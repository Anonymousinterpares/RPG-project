#!/usr/bin/env python3
"""
Handles transitions between different interaction modes.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Tuple

from core.interaction.enums import InteractionMode
from core.combat.combat_manager import CombatManager
from core.combat.enums import CombatState
from core.character.npc_system import NPCSystem
from core.base.state import get_state_manager, GameState # Import GameState for type hinting
from core.combat.dev_commands import create_enemy_combat_entity, create_player_combat_entity
from core.stats.stats_base import DerivedStatType, StatType # Import StatType for checks
from core.combat.combat_entity import EntityType, CombatEntity # Import EntityType and CombatEntity
from core.stats.skill_check import SkillCheckResult # Import SkillCheckResult

# Import necessary functions/classes from interaction_core
from core.game_flow.game_flow_utils import get_participant_by_id # Assuming this helper stays in interaction_core
from core.game_flow.npc_interaction import trigger_combat_narration # Assuming this is called after combat init

if TYPE_CHECKING:
    from core.base.engine import GameEngine # Import GameEngine for type hinting


logger = logging.getLogger("INTERACTION_PROC")


# --- Helper: Mode Transition Cooldown ---

def _check_and_apply_cooldown(game_state: 'GameState', origin_mode: InteractionMode, target_mode: InteractionMode) -> Optional[str]:
    """Checks if a transition is on cooldown. Returns error message if blocked."""
    cooldown_key = f"{origin_mode.name}_TO_{target_mode.name}"
    current_time = time.time()
    if cooldown_key in game_state.mode_transition_cooldowns:
        cooldown_expires = game_state.mode_transition_cooldowns[cooldown_key]
        if current_time < cooldown_expires:
            remaining_time = int(cooldown_expires - current_time)
            narrative_result = f"You cannot attempt to transition from {origin_mode.name} to {target_mode.name} yet. Cooldown remaining: {remaining_time} seconds."
            logger.info(f"Mode transition {cooldown_key} blocked by cooldown. Remaining: {remaining_time}s")
            return narrative_result
        else:
            # Cooldown expired, remove it
            del game_state.mode_transition_cooldowns[cooldown_key]
            logger.debug(f"Cooldown {cooldown_key} expired and removed.")
    return None

def _set_cooldown_on_failure(game_state: 'GameState', origin_mode: InteractionMode, target_mode: InteractionMode, narrative_result: str) -> str:
    """Applies cooldown if transition failed and updates narrative."""
    if game_state.current_mode != target_mode:
        cooldown_key = f"{origin_mode.name}_TO_{target_mode.name}"
        cooldown_duration = 60 # seconds (Example: 1 minute cooldown)
        current_time = time.time()
        game_state.mode_transition_cooldowns[cooldown_key] = current_time + cooldown_duration
        logger.info(f"Applied cooldown for {cooldown_key}. Expires at {game_state.mode_transition_cooldowns[cooldown_key]}")
        # Add a note to the narrative if it doesn't already indicate failure/cooldown
        if "fail" not in narrative_result.lower() and "cannot" not in narrative_result.lower() and "remain" not in narrative_result.lower() and "still in" not in narrative_result.lower():
            narrative_result += f"\n(A cooldown is now active for this transition.)"
    return narrative_result

# --- Helper: Combat Initiation ---

def _create_combat_enemies(game_state: 'GameState', request: Dict[str, Any]) -> Tuple[List[CombatEntity], Optional[str]]:
    """Creates CombatEntity objects for enemies based on the request.

    Enhancements:
    - Accepts optional per-enemy specification via request['enemies'] (list), where each
      item may include 'name', 'count', 'level', 'spawn_hints' (with 'actor_type',
      'threat_tier', 'species_tags', 'is_boss', 'overlay', 'classification'), or a direct
      'classification' dict. Each enemy spec is handled independently so that mixed groups
      (e.g., 1 Wolf beast_easy + 1 Ogre beast_normal) are generated distinctly.
    - Supports spawn_hints.name and spawn_hints.classification even when a single enemy
      is requested via the legacy top-level fields.
    """
    enemy_entities = []
    target_entity_id_or_name = request.get("target_entity_id")  # Keep original request value
    enemy_template = request.get("enemy_template")
    enemy_level = request.get("enemy_level", 1)  # Keep level/count in case template is used later
    enemy_count = request.get("enemy_count", 1)

    # Optional compact spawn hints (from NarratorAgent)
    spawn_hints = request.get("spawn_hints") or {}
    # Normalize keys (single-enemy path)
    if isinstance(spawn_hints, dict):
        actor_type_hint = str(spawn_hints.get("actor_type", "")).lower() or None
        threat_tier_hint = str(spawn_hints.get("threat_tier", "")).lower() or None
        is_boss_hint = bool(spawn_hints.get("is_boss", False))
        overlay_hint = spawn_hints.get("overlay")
        species_tags = spawn_hints.get("species_tags") if isinstance(spawn_hints.get("species_tags"), list) else []
        provided_display_name = str(spawn_hints.get("name")) if spawn_hints.get("name") else None
        provided_classification = spawn_hints.get("classification") if isinstance(spawn_hints.get("classification"), dict) else None
    else:
        actor_type_hint = None
        threat_tier_hint = None
        is_boss_hint = False
        overlay_hint = None
        species_tags = []
        provided_display_name = None
        provided_classification = None

    # Get NPC System (Ensuring it exists or creating fallback)
    npc_system = None
    state_manager = get_state_manager()
    try:
        npc_system = state_manager.get_npc_system()
        if not npc_system:
            logger.warning("NPCSystem not found in StateManager. Creating a new instance.")
            from core.character.npc_system import NPCSystem
            npc_system = NPCSystem()
            state_manager.set_npc_system(npc_system)
    except (AttributeError, Exception) as e:
        logger.error(f"Error accessing NPCSystem via state manager: {e}")
        from core.character.npc_system import NPCSystem
        npc_system = NPCSystem()

    # Helper: compute canonical family id from enums with validation/fallback
    def _canonical_family_id(actor_type: str, threat_tier: str) -> str:
        try:
            from core.base.config import get_config
            cfg_local = get_config()
            fams = cfg_local.get("npc_families.families") or {}
            if not isinstance(fams, dict):
                fams = {}
        except Exception:
            fams = {}
        at = (actor_type or "").lower()
        tt = (threat_tier or "").lower()
        if at not in {"beast", "humanoid", "undead", "construct", "elemental", "spirit"}:
            at = "beast"
        if tt not in {"harmless", "easy", "normal", "dangerous", "ferocious", "mythic"}:
            tt = "normal"
        candidate = f"{at}_{tt}_base"
        if candidate in fams:
            return candidate
        # Nearest-tier fallback for humanoid_harmless (missing today)
        if at == "humanoid" and tt == "harmless":
            fallback = "humanoid_easy_base"
            return fallback if fallback in fams else (next(iter(fams.keys())) if fams else "beast_normal_base")
        # If actor type family missing, degrade to beast at same tier
        beast_candidate = f"beast_{tt}_base"
        if beast_candidate in fams:
            return beast_candidate
        # Final resort
        return next(iter(fams.keys())) if fams else "beast_normal_base"

    # Helper: compute template id from a spec (variant/family/actor_type+tier) and overlay
    def _compute_template_id(spec: Dict[str, Any], display_name: Optional[str] = None, narrative_hint: Optional[str] = None) -> str:
        """Return final enemy_type id string for NPCSystem.
        Rules:
        - Ignore any LLM-provided family_id string. Only accept a known variant_id.
        - Prefer enums (actor_type, threat_tier) to build family_id.
        - If enums are missing, ask the EntityClassifierAgent with name/context.
        - Overlay is applied via ::overlay.
        """
        # Normalize overlay/boss
        overlay = spec.get("overlay") or (spec.get("spawn_hints", {}) or {}).get("overlay")
        is_boss = bool(spec.get("is_boss") or (spec.get("spawn_hints", {}) or {}).get("is_boss", False))
        overlay_id = overlay or ("default_boss" if is_boss else None)

        # 1) Variant id (validate)
        variant_id = None
        classification = spec.get("classification") if isinstance(spec.get("classification"), dict) else None
        if not classification:
            sh = spec.get("spawn_hints") if isinstance(spec.get("spawn_hints"), dict) else {}
            classification = sh.get("classification") if isinstance(sh.get("classification"), dict) else None
        if classification:
            cand_variant = classification.get("variant_id") or classification.get("variant")
            if isinstance(cand_variant, str):
                try:
                    from core.base.config import get_config
                    variants = (get_config().get("npc_variants.variants") or {})
                    if isinstance(variants, dict) and cand_variant in variants:
                        variant_id = cand_variant
                except Exception:
                    variant_id = None

        # If we have a valid variant id, use it now (overlay applied later)
        if variant_id:
            base_id = variant_id
        else:
            # 2) Try enums from hints/classification
            atype = (spec.get("actor_type") or (spec.get("spawn_hints", {}) or {}).get("actor_type") or (classification or {}).get("actor_type") or "").lower()
            tier = (spec.get("threat_tier") or (spec.get("spawn_hints", {}) or {}).get("threat_tier") or (classification or {}).get("threat_tier") or "").lower()
            if not (atype and tier):
                # 3) Ask classifier LLM (name + short context)
                try:
                    from core.agents.entity_classifier import get_entity_classifier_agent
                    from core.agents.base_agent import AgentContext
                    agent = get_entity_classifier_agent()
                    # Build compact prompt input
                    nm = display_name or spec.get("name") or (spec.get("spawn_hints", {}) or {}).get("name") or "Unknown"
                    species_tags = spec.get("species_tags") or (spec.get("spawn_hints", {}) or {}).get("species_tags") or []
                    intent = narrative_hint or ("; ").join([str(nm), f"tags={species_tags}"])
                    ctx = AgentContext(
                        game_state={"mode": "CLASSIFY"},
                        player_state={},
                        world_state={},
                        player_input=intent,
                        conversation_history=[],
                        relevant_memories=[],
                        additional_context={}
                    )
                    out = agent.process(ctx) or {}
                    atype = str(out.get("actor_type", "beast"))
                    tier = str(out.get("threat_tier", "normal"))
                    # Optional: if classifier suggested a valid variant_id, prefer it
                    v = out.get("variant_id")
                    if isinstance(v, str):
                        try:
                            from core.base.config import get_config
                            variants = (get_config().get("npc_variants.variants") or {})
                            if isinstance(variants, dict) and v in variants:
                                variant_id = v
                        except Exception:
                            pass
                except Exception as e:
                    atype = atype or "beast"
                    tier = tier or "normal"
            if variant_id:
                base_id = variant_id
            else:
                base_id = _canonical_family_id(atype, tier)

        # Apply overlay syntax if needed
        return f"{base_id}::{overlay_id}" if overlay_id and base_id else (base_id or "beast_normal_base")

    # Helper: compute a human-readable name for a spec
    def _compute_display_name(spec: Dict[str, Any]) -> Optional[str]:
        # Direct name field wins
        nm = spec.get("name")
        if not nm:
            # Nested under spawn_hints
            sh = spec.get("spawn_hints") if isinstance(spec.get("spawn_hints"), dict) else {}
            nm = sh.get("name")
        if nm:
            return str(nm)
        # Species tag fallback
        sp = None
        sh = spec.get("spawn_hints") if isinstance(spec.get("spawn_hints"), dict) else {}
        stags = spec.get("species_tags") or sh.get("species_tags")
        if isinstance(stags, list) and stags:
            sp = str(stags[0])
        if sp:
            return sp.title()
        # As last resort derive from id
        tid = _compute_template_id(spec)
        base_label = tid.replace("_base", "").replace("_", " ") if tid else "enemy"
        return base_label.title()


    # --- Resolve Target NPC ---
    target_npc = None

    # Multi-enemy specification (preferred when provided): request['enemies']
    enemies_spec = request.get("enemies") if isinstance(request.get("enemies"), list) else []

    # If a list of enemies is provided, skip single-target/template resolution and build per-spec
    created_npcs: List[Any] = []
    if enemies_spec:
        logger.info(f"Creating enemies from 'enemies' array (count={len(enemies_spec)}).")
        try:
            player_location = getattr(game_state.player, 'current_location', 'unknown_location')
            if not player_location:
                player_location = 'unknown_location'
        except Exception:
            player_location = 'unknown_location'

        # Track local name counts for numbering duplicates across specs
        local_name_counts: Dict[str, int] = {}

        for idx, spec in enumerate(enemies_spec):
            try:
                # Normalized view combining top-level spec and nested spawn_hints for convenience
                merged: Dict[str, Any] = {}
                if isinstance(spec, dict):
                    merged.update(spec)
                    if isinstance(spec.get('spawn_hints'), dict):
                        # Copy select keys up for easier access if not present
                        for k in ["actor_type", "threat_tier", "species_tags", "is_boss", "overlay", "name", "classification"]:
                            if k not in merged and k in spec['spawn_hints']:
                                merged[k] = spec['spawn_hints'][k]
                # Compute template id and display name
                display_name = _compute_display_name(merged)
                narrative_hint = (request.get("additional_context", {}) or {}).get("original_intent") or request.get("reason")
                template_id = _compute_template_id(merged, display_name=display_name, narrative_hint=narrative_hint)
                count = int(merged.get("count", 1) or 1)
                level = int(merged.get("level", request.get("enemy_level", 1)) or 1)

                logger.debug(f"Enemy spec[{idx}] -> template='{template_id}', name='{display_name}', count={count}, level={level}")

                for j in range(max(1, count)):
                    # Unique-ish names prior to CombatEntity naming to avoid Manager renames
                    base_name = display_name or "Enemy"
                    n = local_name_counts.get(base_name, 0) + 1
                    local_name_counts[base_name] = n
                    final_name = base_name if (count == 1 and n == 1) else f"{base_name} {n}"

                    enemy_npc = npc_system.create_enemy_for_combat(
                        name=final_name,
                        enemy_type=template_id,
                        level=level,
                        location=player_location
                    )
                    if enemy_npc and hasattr(enemy_npc, 'id'):
                        created_npcs.append(enemy_npc)
                        logger.debug(f"Created enemy NPC '{final_name}' (ID: {enemy_npc.id}, template: {template_id})")
                    else:
                        logger.error(f"Failed to create enemy NPC from spec[{idx}] named '{final_name}'.")
            except Exception as ex:
                logger.error(f"Error processing enemy spec[{idx}]: {ex}", exc_info=True)

        if not created_npcs:
            return [], "System Error: Failed to create enemies from 'enemies' specification."

        # If we built specific enemies, skip the rest of the single-enemy path
        npcs_to_process = created_npcs
    if not enemies_spec:
        if target_entity_id_or_name:
            # Try finding by ID/Name using the utility function first
            participant = get_participant_by_id(game_state, target_entity_id_or_name)
            if participant and getattr(participant, 'entity_type', None) != EntityType.PLAYER:
                target_npc = participant
                logger.info(f"Found target NPC '{getattr(target_npc, 'name', 'Unknown')}' via get_participant_by_id.")
            else:
                # If not found by utility, try NPCSystem directly
                logger.warning(f"Participant '{target_entity_id_or_name}' not found via standard lookup. Trying NPCSystem directly.")
                if npc_system:
                     # Try by ID first if it looks like one
                    if len(target_entity_id_or_name) > 10 and '-' in target_entity_id_or_name: # Basic UUID check
                        if hasattr(npc_system, 'get_npc_by_id'):
                            target_npc = npc_system.get_npc_by_id(target_entity_id_or_name)
                    # If not found by ID or doesn't look like ID, try by name
                    if not target_npc and hasattr(npc_system, 'get_npc_by_name'):
                        target_npc = npc_system.get_npc_by_name(target_entity_id_or_name)

                if target_npc:
                    logger.info(f"Found target NPC '{getattr(target_npc, 'name', 'Unknown')}' via NPCSystem lookup.")
                else:
                    # --- MODIFICATION: Attempt Dynamic Creation HERE ---
                    logger.warning(f"Provided target '{target_entity_id_or_name}' not found via NPCSystem either.")
                    # Only attempt creation if no template was provided and we have a name
                    if not enemy_template and target_entity_id_or_name and npc_system:
                        logger.info(f"Attempting dynamic creation of '{target_entity_id_or_name}' within _create_combat_enemies.")
                        try:
                            # Determine type/level dynamically using the existing function
                            dynamic_enemy_type, dynamic_level = _determine_dynamic_enemy_details(request, target_entity_id_or_name)
                            player_location = getattr(game_state.player, 'current_location', 'unknown_location')
                            target_npc = npc_system.create_enemy_for_combat(
                                name=target_entity_id_or_name,  # Use the requested name
                                enemy_type=dynamic_enemy_type,
                                level=dynamic_level,
                                location=player_location
                            )
                            if target_npc:
                                logger.info(f"Successfully created dynamic NPC: {target_npc.name} (ID: {target_npc.id})")
                                # The newly created NPC is now assigned to target_npc
                            else:
                                 logger.error(f"Dynamic creation failed for '{target_entity_id_or_name}'.")
                                 target_entity_id_or_name = None  # Mark as invalid if creation failed
                        except Exception as fallback_creation_error:
                             logger.error(f"Error during dynamic NPC creation: {fallback_creation_error}", exc_info=True)
                             target_entity_id_or_name = None  # Mark as invalid
                    else:
                         # If we had a template or no name, clear the invalid target name
                         target_entity_id_or_name = None
                     # --- END MODIFICATION ---


        # --- Check if we have a target or template AFTER potential dynamic creation ---
        if not target_npc and not enemy_template:
            logger.error("Combat initiation request missing valid target_entity_id/name or enemy_template.")
            return [], "System Error: Combat initiation request is incomplete (missing target or template)."

        # --- Create list of NPCs to process ---
        npcs_to_process = []
        if target_npc:  # If we found or created the target NPC
            npcs_to_process.append(target_npc)
            logger.info(f"Targeting NPC '{getattr(target_npc, 'name', 'Unknown')}' for combat.")
        elif enemy_template and npc_system:  # If we didn't have a target, but have a template
            # Validate provided template; if invalid, resolve universally via classifier/hints
            try:
                from core.base.config import get_config
                cfg = get_config()
                families = cfg.get("npc_families.families") or {}
                variants = cfg.get("npc_variants.variants") or {}
            except Exception:
                families, variants = {}, {}
            base_id = enemy_template.split("::", 1)[0]
            if not (isinstance(variants, dict) and base_id in variants) and not (isinstance(families, dict) and base_id in families):
                narrative_hint = (request.get("additional_context", {}) or {}).get("original_intent") or request.get("reason")
                spec_for_compute = {
                    "actor_type": actor_type_hint,
                    "threat_tier": threat_tier_hint,
                    "spawn_hints": {"classification": provided_classification or {}},
                    "name": provided_display_name,
                    "species_tags": species_tags,
                }
                resolved_id = _compute_template_id(spec_for_compute, display_name=provided_display_name, narrative_hint=narrative_hint)
                logger.info(f"Template '{enemy_template}' invalid; resolved universally to '{resolved_id}'.")
                enemy_template = resolved_id

            logger.info(f"Creating {enemy_count} enemies from template '{enemy_template}' (Level {enemy_level})")
            for i in range(enemy_count):
                # Choose a readable name: prefer provided name/species, else derive from template id
                base_name = provided_display_name or (species_tags[0].title() if species_tags else enemy_template.replace("_base", "").replace("_", " ").title())
                enemy_name = f"{base_name} {i+1}" if enemy_count > 1 else base_name
                try:
                    player_location = getattr(game_state.player, 'current_location', 'unknown_location')
                    if not player_location:
                        logger.warning("Player location not found, using 'unknown_location' for enemy creation.")
                        player_location = 'unknown_location'

                    enemy_npc = npc_system.create_enemy_for_combat(
                        name=enemy_name, enemy_type=enemy_template, level=enemy_level, location=player_location
                    )
                    if enemy_npc and hasattr(enemy_npc, 'id'):
                        npcs_to_process.append(enemy_npc)
                        logger.debug(f"Successfully created enemy NPC '{enemy_name}' (ID: {enemy_npc.id})")
                    else:
                        logger.error(f"Failed to create or get ID for enemy NPC: {enemy_name}")
                except Exception as creation_error:
                    logger.error(f"Error creating enemy NPC '{enemy_name}': {creation_error}", exc_info=True)
    else:
        # Already populated from 'enemies' list above
        npcs_to_process = created_npcs


    if not npcs_to_process:
        logger.error("No enemy NPCs were identified or created for combat initiation.")
        return [], "System Error: Could not initiate combat (failed to identify/create enemies)."

    # --- Generate Unique Combat Names and Create Combat Entities ---
    enemy_entities = []
    name_counts: Dict[str, int] = {}
    player_combat_name = getattr(game_state.player, 'name', 'Player')

    for npc in npcs_to_process:
        base_name = npc.name
        combat_name = base_name
        if base_name == player_combat_name:
             combat_name = f"{base_name} (NPC)"

        current_count = name_counts.get(base_name, 0) + 1
        name_counts[base_name] = current_count
        if current_count > 1:
            combat_name = f"{base_name} {current_count}"

        final_name = combat_name
        temp_count = 1
        existing_combat_names = {e.combat_name for e in enemy_entities}
        while final_name == player_combat_name or final_name in existing_combat_names:
             temp_count += 1
             final_name = f"{combat_name}_{temp_count}"

        try:
            enemy_entity = create_enemy_combat_entity(npc, final_name)
            enemy_entities.append(enemy_entity)
        except TypeError as te:
            logger.error(f"TypeError creating combat entity for {npc.name} ({final_name}): {te}", exc_info=True)
            return [], f"System Error: Failed to create combat entity ({te})"
        except Exception as e:
            logger.error(f"Failed to create combat entity for {npc.name} ({final_name}): {e}", exc_info=True)
            return [], f"System Error: Failed to prepare enemy for combat ({e})"

    return enemy_entities, None # Return list and no error message if successful

def _determine_dynamic_enemy_details(request: Dict[str, Any], target_entity_id: str) -> Tuple[str, int]:
    """Determines enemy type and level from context for dynamic creation."""
    enemy_type = "hostile"
    level = 1
    reason = request.get("reason", "")
    additional_context = request.get("additional_context", {})

    # Determine enemy type from context/reason/name
    type_keywords = {
        "bandit": ["bandit", "thief", "rogue", "thug", "brigand"],
        "guard": ["guard", "soldier", "watchman", "sentinel", "cop", "police"],
        "wolf": ["wolf", "hound", "dog", "canine", "beast"],
        "goblin": ["goblin", "hobgoblin", "creature", "monster"],
        "skeleton": ["skeleton", "undead", "bones", "animated", "dead"],
        "giant": ["giant", "ogre", "troll", "colossus"],
        "dragon": ["dragon", "drake", "wyvern", "serpent"],
        "wizard": ["wizard", "mage", "witch", "warlock", "sorcerer", "magician"],
    }
    check_strings = [target_entity_id.lower(), reason.lower()]
    # Add more context strings if available, e.g., from additional_context["narrative_context"]

    for type_name, keywords in type_keywords.items():
        for string in check_strings:
            for keyword in keywords:
                if keyword in string:
                    enemy_type = type_name
                    logger.debug(f"Determined enemy type '{enemy_type}' from context")
                    break
            if enemy_type != "hostile": break
        if enemy_type != "hostile": break

    # Determine level from context
    level_indicators = {
        "boss": 5, "elder": 4, "powerful": 4, "strong": 3, "experienced": 3,
        "veteran": 3, "dangerous": 3, "mighty": 3, "lesser": 1, "weak": 1,
        "young": 1, "apprentice": 1, "novice": 1
    }
    for indicator, value in level_indicators.items():
        if indicator in target_entity_id.lower() or indicator in reason.lower():
            level = value
            logger.debug(f"Determined level {level} from context keyword '{indicator}'")
            break

    return enemy_type, level

# --- Helper: Flee Attempt ---

def _determine_flee_parameters(game_state: 'GameState', player_entity: CombatEntity) -> Tuple[int, int, List[str]]:
    """Determines the DC and situational modifier for a flee attempt."""
    flee_dc = 12 # Base difficulty
    situational_modifier = 0
    modifier_reasons = []
    player_status_effects = getattr(player_entity, 'status_effects', set())

    # Calculate DC based on enemies
    enemy_count = 0
    highest_enemy_initiative = 0
    if game_state.combat_manager and game_state.combat_manager.entities:
        for entity in game_state.combat_manager.entities.values():
            if entity.entity_type == EntityType.ENEMY:
                enemy_count += 1
                enemy_initiative = entity.get_stat(DerivedStatType.INITIATIVE) # Use get_stat
                highest_enemy_initiative = max(highest_enemy_initiative, enemy_initiative)

        flee_dc = max(flee_dc, 10 + int(highest_enemy_initiative)) # Ensure int
        if enemy_count > 1:
            dc_increase = min(enemy_count - 1, 5)
            flee_dc += dc_increase
            logger.debug(f"Adjusting flee DC by +{dc_increase} for {enemy_count} enemies to {flee_dc}")

    # Calculate situational modifier based on player status
    if "HASTED" in player_status_effects:
        situational_modifier += 2
        modifier_reasons.append("Hasted (+2)")
    if "SLOWED" in player_status_effects:
        situational_modifier -= 2
        modifier_reasons.append("Slowed (-2)")
    if "ENCUMBERED" in player_status_effects:
        situational_modifier -= 1
        modifier_reasons.append("Encumbered (-1)")
    # TODO: Add equipment/terrain modifiers

    logger.debug(f"Calculated Flee DC: {flee_dc}, Situational Modifier: {situational_modifier} ({', '.join(modifier_reasons)})")
    return flee_dc, situational_modifier, modifier_reasons

def _perform_flee_check(engine: 'GameEngine', player_entity: CombatEntity, flee_dc: int, situational_modifier: int, modifier_reasons: List[str]) -> Tuple[SkillCheckResult, str]:
    """Performs the Dexterity check for fleeing."""
    try:
        from core.stats.stats_manager import get_stats_manager
        stats_manager = get_stats_manager()
        entity_stats_manager = getattr(player_entity, 'stats_manager', None)

        if entity_stats_manager and hasattr(entity_stats_manager, 'perform_skill_check'):
            check_result = entity_stats_manager.perform_skill_check(
                stat_type=StatType.DEXTERITY, difficulty=flee_dc, situational_modifier=situational_modifier
            )
        elif stats_manager and hasattr(stats_manager, 'perform_skill_check'):
            logger.warning(f"Using global stats manager for flee check for entity {player_entity.id}")
            check_result = stats_manager.perform_skill_check(
                stat_type=StatType.DEXTERITY, difficulty=flee_dc, situational_modifier=situational_modifier
            )
        else:
            raise ValueError("Stats manager not available for flee check.")

        # Format the check result narrative
        modifier_str = f"{check_result.modifier} (stat)"
        if check_result.situational_modifier != 0:
            modifier_str += f" {check_result.situational_modifier:+}"
            if modifier_reasons: modifier_str += f" ({', '.join(modifier_reasons)})"
            else: modifier_str += " (situational)"

        check_output = (
            f"Flee attempt ({StatType.DEXTERITY.name} check DC {flee_dc}): "
            f"Roll {check_result.roll} + {modifier_str} "
            f"= {check_result.total} -> {check_result.outcome_desc}"
            f"{' (Crit!)' if check_result.critical else ''}"
        )
        engine._output("system", check_output)
        return check_result, check_output

    except Exception as e:
        logger.error(f"Error performing flee check for actor {player_entity.id}: {e}", exc_info=True)
        raise e # Re-raise the exception to be caught by the caller

def _handle_flee_outcome(engine: 'GameEngine', game_state: 'GameState', success: bool, outcome_narrative: str) -> str:
    """Handles the outcome of the flee check, updating game state and returning narrative."""
    if success:
        if game_state.combat_manager and hasattr(game_state.combat_manager, 'end_combat'):
            game_state.combat_manager.end_combat("Player fled") # Pass reason
        game_state.combat_manager = None
        game_state.current_combatants = []
        game_state.set_interaction_mode(InteractionMode.NARRATIVE)
        # Music: revert to exploration/ambient after leaving combat
        try:
            md = getattr(engine, 'get_music_director', lambda: None)()
            if md:
                md.hard_set("exploration", intensity=0.5, reason="leave_combat_flee")
        except Exception:
            pass
        narrative_result = f"You successfully escape the battle! {outcome_narrative} You find yourself back in the narrative."
        logger.info("Successfully fled combat. Transitioned to NARRATIVE mode.")
    else:
        narrative_result = f"You try to escape, but your enemies cut off your retreat! {outcome_narrative} You are still in combat."
        logger.info("Flee attempt failed. Remaining in COMBAT mode.")
    return narrative_result

# --- Main Transition Handlers ---

def _handle_transition_request(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Processes a mode transition request."""
    target_mode_str = request.get("target_mode")
    origin_mode_str = request.get("origin_mode")
    
    logger.debug(f"Handling Mode Transition Request: From {origin_mode_str} To {target_mode_str} by Actor {effective_actor_id}. Request Details: {json.dumps(request, indent=2)}")

    if not target_mode_str or not origin_mode_str:
        logger.error(f"ModeTransitionRequest missing target_mode or origin_mode: {request}")
        return "System Error: Mode transition request is incomplete."

    try:
        target_mode = InteractionMode[target_mode_str.upper()]
        origin_mode = InteractionMode[origin_mode_str.upper()]
    except KeyError:
        logger.error(f"Invalid mode name in ModeTransitionRequest: {request}")
        return f"System Error: Invalid mode name specified: {target_mode_str} or {origin_mode_str}."

    cooldown_message = _check_and_apply_cooldown(game_state, origin_mode, target_mode)
    if cooldown_message:
        # If in combat, queue message via orchestrator
        if game_state.current_mode == InteractionMode.COMBAT and hasattr(engine, '_combat_orchestrator') and game_state.combat_manager:
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            event = DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE, content=cooldown_message,
                target_display=DisplayTarget.COMBAT_LOG, role="system"
            )
            engine._combat_orchestrator.add_event_to_queue(event)
            game_state.combat_manager.waiting_for_display_completion = True
        else: # Output directly if not in orchestrated combat context for this message
            engine._output("system", cooldown_message)
        return cooldown_message 

    narrative_result = ""
    transition_successful = False 
    original_mode_before_attempt = game_state.current_mode # Store for potential revert

    if origin_mode == InteractionMode.NARRATIVE and target_mode == InteractionMode.COMBAT:
        logger.debug("Setting game_state.is_transitioning_to_combat = True before calling _initiate_combat_transition.")
        game_state.is_transitioning_to_combat = True
        narrative_result = _initiate_combat_transition(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.COMBAT
        if narrative_result and not transition_successful: 
             game_state.is_transitioning_to_combat = False 
    elif origin_mode == InteractionMode.COMBAT and target_mode == InteractionMode.NARRATIVE:
        reason_lower = request.get("reason", "").lower()
        # Player surrender/flee from COMBAT mode is now primarily handled by CombatManager converting the
        # "request_mode_transition" into a FleeAction or processing surrender directly.
        # This _handle_transition_request function, when called by CombatManager,
        # is confirming if the mechanical outcome of that FleeAction/Surrender leads to a mode change.
        if game_state.combat_manager:
            actor_entity = game_state.combat_manager.get_entity_by_id(effective_actor_id)
            if actor_entity and not actor_entity.is_active_in_combat: # Flee was successful for this actor
                transition_successful = True
                narrative_result = f"{actor_entity.combat_name} has fled the battle."
                # Check if all players fled or all enemies defeated to actually change mode
                game_state.combat_manager._check_combat_state()
                if game_state.combat_manager.state != CombatState.IN_PROGRESS:
                    game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                    # CM will go to ENDING_COMBAT step.
                else: # Other players still in combat
                    narrative_result += " The battle continues for the others."
                    transition_successful = False # Mode doesn't change overall yet
            elif "surrender" in reason_lower:
                narrative_result = _attempt_surrender_transition(engine, game_state, request, effective_actor_id)
                transition_successful = game_state.current_mode == InteractionMode.NARRATIVE # surrender changes mode directly if successful
            else: # Generic "flee" reason, but actor still active (means mechanical flee failed or not processed yet)
                narrative_result = "Your attempt to leave combat was unsuccessful."
                transition_successful = False
        else:
            # Guard: if engine is already waiting for the orchestrated closing narrative, do not intervene.
            try:
                if hasattr(engine, '_waiting_for_closing_narrative_display') and engine._waiting_for_closing_narrative_display:
                    logger.info("Mode transition request received after combat finalize begun; ignoring extra transition and message.")
                    narrative_result = ""  # No extra message; finalization flow will handle narrative
                    transition_successful = True
                else:
                    logger.warning("Origin mode is COMBAT but CombatManager is missing. Treating as already concluded; switching to NARRATIVE.")
                    game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                    narrative_result = "You are no longer in combat."
                    transition_successful = True
            except Exception:
                logger.warning("Guard failed; applying safe fallback to NARRATIVE.")
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                narrative_result = "You are no longer in combat."
                transition_successful = True

    elif origin_mode == InteractionMode.NARRATIVE and target_mode == InteractionMode.TRADE:
        narrative_result = _initiate_trade_transition(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.TRADE
    elif origin_mode == InteractionMode.TRADE and target_mode == InteractionMode.NARRATIVE:
        narrative_result = _end_trade_transition(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.NARRATIVE
    elif origin_mode == InteractionMode.NARRATIVE and target_mode == InteractionMode.SOCIAL_CONFLICT:
        narrative_result = _initiate_social_conflict_transition(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.SOCIAL_CONFLICT
    elif origin_mode == InteractionMode.SOCIAL_CONFLICT and target_mode == InteractionMode.NARRATIVE:
        narrative_result = _end_social_conflict_transition(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.NARRATIVE
    elif origin_mode == InteractionMode.TRADE and target_mode == InteractionMode.SOCIAL_CONFLICT:
        narrative_result = _handle_trade_to_social_conflict(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.SOCIAL_CONFLICT
    elif origin_mode == InteractionMode.SOCIAL_CONFLICT and target_mode == InteractionMode.TRADE:
        narrative_result = _handle_social_conflict_to_trade(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.TRADE
    elif origin_mode == InteractionMode.TRADE and target_mode == InteractionMode.COMBAT:
        if not game_state.is_transitioning_to_combat: game_state.is_transitioning_to_combat = True
        narrative_result = _handle_trade_to_combat(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.COMBAT
        if not transition_successful: game_state.is_transitioning_to_combat = False
    elif origin_mode == InteractionMode.SOCIAL_CONFLICT and target_mode == InteractionMode.COMBAT:
        if not game_state.is_transitioning_to_combat: game_state.is_transitioning_to_combat = True
        narrative_result = _handle_social_conflict_to_combat(engine, game_state, request, effective_actor_id)
        transition_successful = game_state.current_mode == InteractionMode.COMBAT
        if not transition_successful: game_state.is_transitioning_to_combat = False
    else:
        logger.warning(f"Unhandled mode transition requested: {origin_mode.name} -> {target_mode.name}")
        narrative_result = f"System Warning: Requested transition from {origin_mode.name} to {target_mode.name} is not yet implemented."
        transition_successful = False

    if not transition_successful and game_state.current_mode == original_mode_before_attempt: # Only apply cooldown if mode didn't change at all
        narrative_result = _set_cooldown_on_failure(game_state, origin_mode, target_mode, narrative_result)
    
    if target_mode == InteractionMode.COMBAT and not transition_successful: 
        game_state.is_transitioning_to_combat = False # Ensure flag is reset on any COMBAT transition failure

    if narrative_result:
        role_for_output = "system" if "Error" in narrative_result or "Warning" in narrative_result else "gm"
        
        # If the current mode is COMBAT (e.g., failed flee/surrender text) and orchestrator exists
        if game_state.current_mode == InteractionMode.COMBAT and hasattr(engine, '_combat_orchestrator') and game_state.combat_manager:
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            event = DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE, content=narrative_result,
                target_display=DisplayTarget.COMBAT_LOG, role=role_for_output
            )
            engine._combat_orchestrator.add_event_to_queue(event)
            game_state.combat_manager.waiting_for_display_completion = True
        elif game_state.current_mode != InteractionMode.COMBAT or not (transition_successful and target_mode == InteractionMode.COMBAT):
            # Output for non-combat transitions or if combat transition failed early and returned to NARRATIVE
            engine._output(role_for_output, narrative_result)

    return narrative_result 

def _attempt_surrender_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the attempt to surrender from Combat to Narrative mode."""
    logger.info(f"Handling surrender attempt by {effective_actor_id}")
    active_enemies_remain = False
    enemy_details = [] 

    if game_state.combat_manager:
        for entity_id, entity in game_state.combat_manager.entities.items():
            if entity.entity_type == EntityType.ENEMY and \
               entity.is_alive() and \
               getattr(entity, 'is_active_in_combat', True):
                active_enemies_remain = True
                enemy_details.append(f"{entity.combat_name} (Active)")
            elif entity.entity_type == EntityType.ENEMY:
                 enemy_details.append(f"{entity.combat_name} (Inactive/Defeated)")
        logger.debug(f"Checking for active enemies for surrender: {enemy_details}")
    else:
        logger.warning("Cannot check for active enemies: CombatManager is None.")
        active_enemies_remain = True # Assume enemies if CM is missing

    if active_enemies_remain:
        logger.info("Surrender failed: Active enemies remain.")
        # Message will be queued by CombatManager's orchestrator path for failed transition
        narrative_result = "You attempt to surrender, but your enemies are not willing to accept your plea while they still stand!"
        # Do NOT change game_state.current_mode here. Caller (CombatManager) handles turn end.
        return narrative_result # Return feedback to be queued by CM
    else:
        logger.info("Surrender accepted (no active enemies). Ending combat.")
        final_combat_state_name = "PLAYER_SURRENDERED" # Or derive more specifically
        if game_state.combat_manager:
            # Let CombatManager handle its state change to FLED or a specific SURRENDER state if added
            game_state.combat_manager.state = CombatState.FLED # Using FLED as a proxy for player ending combat by choice
            reason = f"Player {effective_actor_id} surrendered."
            if hasattr(game_state.combat_manager, 'end_combat'): # This method might set a more specific state
                 game_state.combat_manager.end_combat(reason)
            final_combat_state_name = game_state.combat_manager.state.name


        # Game state changes (mode, clearing CM) are handled by CombatManager when its step becomes ENDING_COMBAT / COMBAT_ENDED
        # or by the calling function in CombatManager._step_processing_player_action if transition is successful.
        # This function's role is to determine IF surrender is mechanically possible and give feedback.
        # The actual mode change is now handled by the caller in CombatManager based on this outcome.
        game_state.set_interaction_mode(InteractionMode.NARRATIVE) # If successful, mode changes
        if game_state.combat_manager: game_state.combat_manager = None # Clear CM if mode changed
        game_state.current_combatants = []

        # Music: revert to pre-combat mood after surrender
        try:
            md = getattr(engine, 'get_music_director', lambda: None)()
            if md:
                prev_mood = getattr(engine, '_pre_combat_mood', None)
                prev_i = getattr(engine, '_pre_combat_intensity', None)
                if prev_mood:
                    md.hard_set(prev_mood, intensity=prev_i if isinstance(prev_i, (int,float)) else None, reason="leave_combat_surrender")
        except Exception:
            pass

        narrative_result = f"Your surrender is accepted as there are no active opponents. The combat ends ({final_combat_state_name})."
        # SFX: surrender
        try:
            if hasattr(engine, '_sfx_manager') and engine._sfx_manager:
                engine._sfx_manager.play_one_shot('event','surrender')
        except Exception:
            pass
        # engine._output("system", narrative_result) # Orchestrator will handle this via CM queue
        return narrative_result

def _initiate_combat_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Prepares for the transition to Combat mode, setting up CombatManager."""
    logger.info(f"[MODE TRANSITION] Initiating NARRATIVE -> COMBAT. Request: {json.dumps(request, indent=2)}")

    # The initiating narrative (e.g., "You lunge at the guard...") is now expected to be in
    # game_state.combat_narrative_buffer, put there by MainWindow because
    # game_state.is_transitioning_to_combat was set to True by _handle_transition_request
    # before this function was called. This function no longer outputs it.

    # Extract original_intent for CombatManager.prepare_for_combat
    additional_context = request.get("additional_context", {})
    original_intent = additional_context.get("original_intent", "Unknown combat-initiating action")
    # narrative_context_for_log = additional_context.get("narrative_context", "") # For logging if needed

    # logger.debug(f"Original player intent for combat: '{original_intent}'")
    # logger.debug(f"Narrative context that led to combat: '{narrative_context_for_log[:100]}...'")


    if game_state.current_mode == InteractionMode.COMBAT:
        # If there is no active/in-progress CombatManager, force reset to NARRATIVE and continue
        try:
            from core.combat.enums import CombatState
            cm = getattr(game_state, 'combat_manager', None)
            if not cm or getattr(cm, 'state', None) != CombatState.IN_PROGRESS:
                logger.warning("Current mode is COMBAT but no active in-progress CombatManager. Forcing reset to NARRATIVE and continuing with new combat.")
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
            else:
                logger.warning("Attempted to initiate combat while already in COMBAT mode.")
                # game_state.is_transitioning_to_combat = False # Should be handled by caller if transition fails overall
                return "System Warning: Already in combat." # Return message to caller
        except Exception:
            # On any error determining CM state, be conservative and block duplicate combat
            logger.warning("Error checking CombatManager state while already in COMBAT mode. Blocking duplicate initiation.")
            return "System Warning: Already in combat."

    if game_state.combat_manager:
        logger.warning("Clearing existing CombatManager before initiating new combat.")
        game_state.combat_manager = None
        if hasattr(engine, '_combat_orchestrator'): 
            engine._combat_orchestrator.set_combat_manager(None)
            engine._combat_orchestrator.clear_queue_and_reset_flags()

    game_state.current_combatants = []
    # game_state.combat_narrative_buffer is populated by MainWindow

    try:
        enemy_entities, error_msg = _create_combat_enemies(game_state, request)
        if error_msg:
            # game_state.is_transitioning_to_combat = False # Handled by caller on error
            return error_msg 

        player_combat_name = game_state.player.name
        enemy_combat_names = {e.combat_name for e in enemy_entities}
        if player_combat_name in enemy_combat_names:
            player_combat_name += " (Player)"

        try:
            player_entity = create_player_combat_entity(game_state, player_combat_name)
        except Exception as e:
            logger.error(f"Failed to create player combat entity: {e}", exc_info=True)
            # game_state.is_transitioning_to_combat = False # Handled by caller
            return "System Error: Failed to prepare player for combat."

        combat_manager = CombatManager()
        game_state.combat_manager = combat_manager 
        if hasattr(engine, '_combat_orchestrator'): 
            engine._combat_orchestrator.set_combat_manager(combat_manager)

        surprise = request.get("surprise", False)
        
        combat_manager.prepare_for_combat(
            player_entity=player_entity,
            enemy_entities=enemy_entities,
            surprise=surprise,
            initiating_intent=original_intent 
        )
        logger.info("CombatManager initialized and prepared with entities.")

        # Set the mode. MainWindow._update_ui will detect this change.
        # If is_transitioning_to_combat is still true, _update_ui will handle flushing the buffer.
        game_state.set_interaction_mode(InteractionMode.COMBAT) 
        logger.info("Transitioned game_state to COMBAT mode.")
        
        # Music: enter combat mood immediately (authoritative hard-set)
        try:
            md = getattr(engine, 'get_music_director', lambda: None)()
            if md:
                # Remember pre-combat mood/intensity to restore later
                try:
                    engine._pre_combat_mood = getattr(md, '_mood', None)
                    engine._pre_combat_intensity = float(getattr(md, '_intensity', 0.6))
                except Exception:
                    engine._pre_combat_mood = getattr(engine, '_pre_combat_mood', None)
                    engine._pre_combat_intensity = getattr(engine, '_pre_combat_intensity', 0.6)
                md.hard_set("combat", intensity=0.7, reason="enter_combat")
            # Combat start SFX
            try:
                if hasattr(engine, '_sfx_manager') and engine._sfx_manager:
                    engine._sfx_manager.play_one_shot('event','combat_start')
            except Exception:
                pass
        except Exception:
            pass
        
        # The first call to combat_manager.process_combat_step(engine) is now triggered
        # by MainWindow._update_ui after it processes the mode switch and potentially
        # queues the BUFFER_FLUSH event with the orchestrator. The orchestrator then starts CM.

        return "" # Success, no direct narrative output.

    except Exception as e:
        logger.error(f"Error initiating combat transition: {e}", exc_info=True)
        # game_state.is_transitioning_to_combat = False # Handled by caller
        if game_state.combat_manager: game_state.combat_manager = None
        if hasattr(engine, '_combat_orchestrator'): engine._combat_orchestrator.set_combat_manager(None)
        game_state.current_combatants = []
        # If mode somehow got set to COMBAT, revert it
        if game_state.current_mode == InteractionMode.COMBAT: 
            game_state.set_interaction_mode(InteractionMode.NARRATIVE) # This will also clear is_transitioning_to_combat
        return f"System Error: Failed to initiate combat transition: {str(e)}"

def _attempt_flee_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the attempt to flee from Combat to Narrative mode."""
    logger.info(f"Attempting to flee combat for actor {effective_actor_id}.")
    narrative_result = "Flee attempt processing..." # Default
    
    if not game_state.combat_manager:
        logger.error("Cannot attempt flee: CombatManager is None.")
        game_state.set_interaction_mode(InteractionMode.NARRATIVE)
        return "System Error: Combat already concluded or in error state. Flee not applicable."

    player_entity = game_state.combat_manager.get_entity_by_id(effective_actor_id)

    if not player_entity:
        logger.error(f"Could not get player entity for flee check: {effective_actor_id}")
        return "System Error: Cannot perform flee check (player entity unavailable)."

    
    if game_state.combat_manager.state == CombatState.FLED and not player_entity.is_active_in_combat:
        game_state.set_interaction_mode(InteractionMode.NARRATIVE)
        game_state.combat_manager = None 
        game_state.current_combatants = []
        narrative_result = "You successfully escaped the battle!"
        logger.info(f"Flee successful for {effective_actor_id}. Transitioned to NARRATIVE.")
        # SFX + music restore
        try:
            if hasattr(engine, '_sfx_manager') and engine._sfx_manager:
                engine._sfx_manager.play_one_shot('event','flee')
        except Exception:
            pass
        try:
            md = getattr(engine, 'get_music_director', lambda: None)()
            if md:
                prev_mood = getattr(engine, '_pre_combat_mood', None)
                prev_i = getattr(engine, '_pre_combat_intensity', None)
                if prev_mood:
                    md.hard_set(prev_mood, intensity=prev_i if isinstance(prev_i, (int,float)) else None, reason="leave_combat_flee")
        except Exception:
            pass
    else:
        narrative_result = "Your attempt to flee was unsuccessful. The battle continues!" # Placeholder
        logger.info(f"Flee attempt for {effective_actor_id} seems to have failed or is being handled by CM. Staying in COMBAT.")
        
    return narrative_result 


def _initiate_trade_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Narrative to Trade mode."""
    target_entity_id = request.get("target_entity_id")
    if not target_entity_id:
        logger.error("Initiate trade request missing target_entity_id.")
        return "System Error: Who do you want to trade with?"

    trade_partner = get_participant_by_id(game_state, target_entity_id)
    if not trade_partner:
        logger.warning(f"Target entity '{target_entity_id}' not found for trading.")
        return f"You don't see '{target_entity_id}' here to trade with."

    game_state.current_trade_partner_id = target_entity_id
    game_state.set_interaction_mode(InteractionMode.TRADE)

    partner_name = getattr(trade_partner, 'name', target_entity_id)
    narrative_result = f"You approach {partner_name} to trade."
    logger.info(f"Transitioned to TRADE mode with partner {target_entity_id}.")
    return narrative_result

def _end_trade_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Trade to Narrative mode."""
    if game_state.current_mode != InteractionMode.TRADE:
        logger.warning("Attempted to end trade when not in TRADE mode.")
        return ""

    partner_id = game_state.current_trade_partner_id
    partner_name = "your trading partner"
    if partner_id:
        trade_partner = get_participant_by_id(game_state, partner_id)
        if trade_partner:
            partner_name = getattr(trade_partner, 'name', partner_id)

    game_state.current_trade_partner_id = None
    game_state.set_interaction_mode(InteractionMode.NARRATIVE)

    narrative_result = f"You finish trading with {partner_name}."
    logger.info("Ended trade. Transitioned back to NARRATIVE mode.")
    return narrative_result

def _initiate_social_conflict_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Narrative to Social Conflict mode."""
    target_entity_id = request.get("target_entity_id")
    if not target_entity_id:
        logger.error("Initiate social conflict request missing target_entity_id.")
        return "System Error: Who do you want to engage in a social conflict with?"

    conflict_partner = get_participant_by_id(game_state, target_entity_id)
    if not conflict_partner:
        logger.warning(f"Target entity '{target_entity_id}' not found for social conflict.")
        return f"You don't see '{target_entity_id}' here to confront."

    player_id = getattr(game_state.player, 'id', getattr(game_state.player, 'stats_manager_id', None))
    if not player_id:
        logger.error("Cannot initiate social conflict: Player ID not found.")
        return "System Error: Cannot determine player identity for social conflict."

    if player_id == target_entity_id:
        return "You cannot start a social conflict with yourself."

    game_state.current_combatants = [player_id, target_entity_id]
    game_state.set_interaction_mode(InteractionMode.SOCIAL_CONFLICT)

    # Initialize resolve (example)
    player_entity = get_participant_by_id(game_state, player_id)
    if player_entity and hasattr(player_entity, 'stats_manager') and hasattr(player_entity.stats_manager, 'set_current_stat'):
        initial_player_resolve = getattr(player_entity.stats_manager, 'get_stat', lambda s: 10)('resolve')
        player_entity.stats_manager.set_current_stat('resolve', initial_player_resolve)
        logger.debug(f"Initialized player {player_id} resolve to {initial_player_resolve}")

    if conflict_partner and hasattr(conflict_partner, 'stats_manager') and hasattr(conflict_partner.stats_manager, 'set_current_stat'):
        initial_partner_resolve = getattr(conflict_partner.stats_manager, 'get_stat', lambda s: 10)('resolve')
        conflict_partner.stats_manager.set_current_stat('resolve', initial_partner_resolve)
        logger.debug(f"Initialized partner {target_entity_id} resolve to {initial_partner_resolve}")

    partner_name = getattr(conflict_partner, 'name', target_entity_id)
    narrative_result = f"You initiate a social conflict with {partner_name}."
    logger.info(f"Transitioned to SOCIAL_CONFLICT mode with participants: {game_state.current_combatants}.")
    return narrative_result

def _end_social_conflict_transition(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Social Conflict to Narrative mode."""
    if game_state.current_mode != InteractionMode.SOCIAL_CONFLICT:
        logger.warning("Attempted to end social conflict when not in SOCIAL_CONFLICT mode.")
        return ""

    participants = game_state.current_combatants[:]
    participant_names = [getattr(get_participant_by_id(game_state, p_id), 'name', p_id) for p_id in participants]

    game_state.current_combatants = []
    game_state.set_interaction_mode(InteractionMode.NARRATIVE)

    narrative_result = f"The social conflict between {', '.join(participant_names)} ends."
    logger.info("Ended social conflict. Transitioned back to NARRATIVE mode.")
    return narrative_result

def _perform_charisma_check(engine: 'GameEngine', actor: Any, target_name: str, dc: int, context_msg: str) -> Tuple[bool, str]:
    """Performs a Charisma check and returns success status and narrative."""
    if not hasattr(actor, 'stats_manager') or not hasattr(actor.stats_manager, 'perform_skill_check'):
        raise AttributeError(f"Actor {getattr(actor, 'name', 'Unknown')} has no stats_manager or perform_skill_check method.")

    check_result = actor.stats_manager.perform_skill_check(stat_type=StatType.CHARISMA, difficulty=dc)
    check_narrative = (
        f"{getattr(actor, 'name', 'Unknown')} attempts to {context_msg} with {target_name} ({StatType.CHARISMA.name} check DC {dc}): "
        f"Roll {check_result.roll} + {check_result.modifier} (stat) = {check_result.total} -> {check_result.outcome_desc}"
    )
    engine._output("system", check_narrative)
    return check_result.is_success, check_result.outcome_desc

def _handle_trade_to_social_conflict(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Trade to Social Conflict mode."""
    logger.info(f"Attempting transition TRADE -> SOCIAL_CONFLICT for actor {effective_actor_id}")

    target_entity_id = request.get("target_entity_id") or game_state.current_trade_partner_id
    if not target_entity_id:
        logger.error("Transition TRADE -> SOCIAL_CONFLICT failed: No target.")
        return "System Error: Cannot transition to social conflict without a target."
    request["target_entity_id"] = target_entity_id

    actor = get_participant_by_id(game_state, effective_actor_id)
    target = get_participant_by_id(game_state, target_entity_id)
    if not actor or not target:
        logger.error(f"Transition TRADE -> SOCIAL_CONFLICT failed: Participants not found.")
        return "System Error: Could not find participants for social conflict."

    actor_name = getattr(actor, 'name', effective_actor_id)
    target_name = getattr(target, 'name', target_entity_id)

    try:
        success, outcome_desc = _perform_charisma_check(engine, actor, target_name, 13, "escalate trade")
        if success:
            logger.info("Charisma check succeeded. Transitioning TRADE -> SOCIAL_CONFLICT.")
            end_trade_narrative = _end_trade_transition(engine, game_state, request, effective_actor_id)
            init_social_narrative = _initiate_social_conflict_transition(engine, game_state, request, effective_actor_id)
            transition_reason = request.get("reason", "The situation escalates.")
            return f"{end_trade_narrative} {transition_reason} {init_social_narrative}"
        else:
            logger.info("Charisma check failed. Remaining in TRADE mode.")
            return f"Your attempt to escalate the situation with {target_name} fails ({outcome_desc}). You remain in trade."
    except Exception as e:
        logger.error(f"Error during TRADE -> SOCIAL_CONFLICT transition check: {e}", exc_info=True)
        return f"System Error: Failed to perform transition check: {str(e)}"

def _handle_social_conflict_to_trade(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Social Conflict to Trade mode."""
    logger.info(f"Attempting transition SOCIAL_CONFLICT -> TRADE for actor {effective_actor_id}")

    target_entity_id = request.get("target_entity_id")
    if not target_entity_id:
        participants = game_state.current_combatants
        if len(participants) == 2:
            target_entity_id = next((p_id for p_id in participants if p_id != effective_actor_id), None)
            if target_entity_id: request["target_entity_id"] = target_entity_id
            else: return "System Error: Cannot determine target for trade transition."
        else: return "System Error: Cannot transition to trade without a clear target."

    actor = get_participant_by_id(game_state, effective_actor_id)
    target = get_participant_by_id(game_state, target_entity_id)
    if not actor or not target:
        logger.error(f"Transition SOCIAL_CONFLICT -> TRADE failed: Participants not found.")
        return "System Error: Could not find participants for trade transition."

    actor_name = getattr(actor, 'name', effective_actor_id)
    target_name = getattr(target, 'name', target_entity_id)

    try:
        success, outcome_desc = _perform_charisma_check(engine, actor, target_name, 15, "de-escalate conflict into trade")
        if success:
            logger.info("Charisma check succeeded. Transitioning SOCIAL_CONFLICT -> TRADE.")
            end_social_narrative = _end_social_conflict_transition(engine, game_state, request, effective_actor_id)
            init_trade_narrative = _initiate_trade_transition(engine, game_state, request, effective_actor_id)
            transition_reason = request.get("reason", "You manage to calm the situation.")
            return f"{end_social_narrative} {transition_reason} {init_trade_narrative}"
        else:
            logger.info("Charisma check failed. Remaining in SOCIAL_CONFLICT mode.")
            return f"Your attempt to de-escalate the conflict with {target_name} fails ({outcome_desc}). The social conflict continues."
    except Exception as e:
        logger.error(f"Error during SOCIAL_CONFLICT -> TRADE transition check: {e}", exc_info=True)
        return f"System Error: Failed to perform transition check: {str(e)}"

def _handle_trade_to_combat(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Trade to Combat mode."""
    logger.info(f"Attempting transition TRADE -> COMBAT for actor {effective_actor_id}")

    target_entity_id = request.get("target_entity_id") or game_state.current_trade_partner_id
    if not target_entity_id:
        logger.error("Transition TRADE -> COMBAT failed: No target.")
        return "System Error: Cannot transition to combat without a target."
    request["target_entity_id"] = target_entity_id

    target = get_participant_by_id(game_state, target_entity_id)
    if not target:
        logger.error(f"Transition TRADE -> COMBAT failed: Target ({target_entity_id}) not found.")
        return "System Error: Could not find target for combat transition."
    if not hasattr(target, 'stats_manager') and not hasattr(target, 'get_stat'):
        logger.warning(f"Target {target_entity_id} does not appear combat-capable.")
        return f"System Error: {getattr(target, 'name', target_entity_id)} cannot engage in combat."

    end_trade_narrative = _end_trade_transition(engine, game_state, request, effective_actor_id)
    combat_request = {
        "target_mode": "COMBAT", "origin_mode": "TRADE",
        "reason": request.get("reason", "Trade escalated to combat."),
        "target_entity_id": target_entity_id, "surprise": request.get("surprise", False)
    }
    init_combat_narrative = _initiate_combat_transition(engine, game_state, combat_request, effective_actor_id)
    return f"{end_trade_narrative} The situation rapidly escalates! {init_combat_narrative}"

def _handle_social_conflict_to_combat(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Handles the transition from Social Conflict to Combat mode."""
    logger.info(f"Attempting transition SOCIAL_CONFLICT -> COMBAT for actor {effective_actor_id}")

    target_entity_id = request.get("target_entity_id")
    if not target_entity_id:
        participants = game_state.current_combatants
        if len(participants) == 2:
            target_entity_id = next((p_id for p_id in participants if p_id != effective_actor_id), None)
            if target_entity_id: request["target_entity_id"] = target_entity_id
            else: return "System Error: Cannot determine target for combat transition."
        else: return "System Error: Cannot transition to combat without a clear target."

    target = get_participant_by_id(game_state, target_entity_id)
    if not target:
        logger.error(f"Transition SOCIAL_CONFLICT -> COMBAT failed: Target ({target_entity_id}) not found.")
        return "System Error: Could not find target for combat transition."
    if not hasattr(target, 'stats_manager') and not hasattr(target, 'get_stat'):
        logger.warning(f"Target {target_entity_id} does not appear combat-capable.")
        return f"System Error: {getattr(target, 'name', target_entity_id)} cannot engage in combat."

    end_social_narrative = _end_social_conflict_transition(engine, game_state, request, effective_actor_id)
    combat_request = {
        "target_mode": "COMBAT", "origin_mode": "SOCIAL_CONFLICT",
        "reason": request.get("reason", "Social conflict escalated to combat."),
        "target_entity_id": target_entity_id, "surprise": request.get("surprise", False)
    }
    init_combat_narrative = _initiate_combat_transition(engine, game_state, combat_request, effective_actor_id)
    return f"{end_social_narrative} Words fail, and the situation turns violent! {init_combat_narrative}"
