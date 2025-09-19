#!/usr/bin/env python3
"""
NPC Creator module focused on creating and generating NPCs for various interactions.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_generator import NPCGenerator
from core.character.npc_manager import NPCManager
from core.base.config import get_config

logger = logging.getLogger(__name__)


class NPCCreator:
    """
    Class for handling NPC creation operations.
    Contains methods for creating different types of NPCs and enhancing existing ones.
    """
    
    def __init__(self, npc_manager: NPCManager):
        """
        Initialize the NPC creator.
        
        Args:
            npc_manager: The NPCManager instance to use
        """
        self.npc_manager = npc_manager
        self.npc_generator = npc_manager.npc_generator
    
    def create_npc(self, 
                  interaction_type: NPCInteractionType,
                  name: Optional[str] = None,
                  npc_type: Optional[NPCType] = None,
                  npc_subtype: Optional[str] = None,
                  relationship: NPCRelationship = NPCRelationship.NEUTRAL,
                  location: Optional[str] = None,
                  description: Optional[str] = None,
                  occupation: Optional[str] = None,
                  is_persistent: bool = False) -> NPC:
        """
        Create a new NPC and add it to the manager.
        
        Args:
            interaction_type: The type of interaction this NPC is for
            name: Optional name for the NPC (generated if None)
            npc_type: Type of NPC (determined from interaction if None)
            relationship: Initial relationship with the player
            location: Where the NPC is located
            description: Optional description of the NPC
            occupation: Optional occupation
            is_persistent: Whether this NPC should be saved persistently
            
        Returns:
            The newly created NPC
        """
        # Check if NPC with this name already exists
        if name and self.npc_manager.get_npc_by_name(name):
            logger.warning(f"NPC with name '{name}' already exists, checking compatibility")
            existing_npc = self.npc_manager.get_npc_by_name(name)
            
            # If it exists but has minimal stats and we need more, enhance it
            if existing_npc and not existing_npc.has_stats():
                self.enhance_npc_for_interaction(existing_npc, interaction_type)
                return existing_npc
            
            # Otherwise, append a number to make the name unique
            i = 2
            while self.npc_manager.get_npc_by_name(f"{name} {i}"):
                i += 1
            name = f"{name} {i}"
        
        # Generate the NPC
        npc = self.npc_generator.generate_npc_for_interaction(
            interaction_type=interaction_type,
            name=name,
            npc_type=npc_type,
            npc_subtype=npc_subtype,
            relationship=relationship,
            location=location,
            description=description,
            occupation=occupation,
            is_persistent=is_persistent
        )
        
        # Add to manager
        self.npc_manager.add_npc(npc)
        
        return npc
    
    def create_enemy(self, 
                    name: Optional[str] = None,
                    enemy_type: str = "generic",
                    level: int = 1,
                    location: Optional[str] = None) -> NPC:
        """
        Create a new enemy NPC for combat and add it to the manager.
        
        Args:
            name: Optional name for the enemy
            enemy_type: Type of enemy (e.g., "bandit", "wolf", "guard")
            level: Level of the enemy, affects stats
            location: Where the enemy is located
            
        Returns:
            The newly created enemy NPC
        """
        # Families-mode path
        try:
            cfg = get_config()
            mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        except Exception:
            mode = "legacy"

        if mode == "families":
            from core.character.npc_family_generator import NPCFamilyGenerator
            fam_gen = NPCFamilyGenerator()
            # Parse overlay syntax: id::overlay_id or id+boss
            raw = enemy_type
            overlay_id = None
            target_id = raw
            if isinstance(raw, str) and "::" in raw:
                parts = raw.split("::", 1)
                target_id, overlay_id = parts[0], parts[1] or None
            elif isinstance(raw, str) and raw.endswith("+boss"):
                target_id = raw[:-5]
                overlay_id = overlay_id or "default_boss"

            # Pull difficulty/encounter_size from config if available
            try:
                difficulty = (cfg.get("game.difficulty", "normal") or "normal")
                encounter_size = (cfg.get("game.encounter_size", "solo") or "solo")
            except Exception:
                difficulty = "normal"
                encounter_size = "solo"

            # Use variant if exists, else family
            used_variant = False
            if callable(getattr(fam_gen, "get_variant", None)) and fam_gen.get_variant(target_id):
                npc = fam_gen.generate_npc_from_variant(
                    variant_id=target_id,
                    name=name,
                    location=location,
                    level=level,
                    overlay_id=overlay_id,
                    difficulty=difficulty,
                    encounter_size=encounter_size,
                )
                used_variant = True
            else:
                npc = fam_gen.generate_npc_from_family(
                    family_id=target_id,
                    name=name,
                    location=location,
                    level=level,
                    overlay_id=overlay_id,
                    difficulty=difficulty,
                    encounter_size=encounter_size,
                )
            # Add to manager and return
            self.npc_manager.add_npc(npc)
            return npc

        # Legacy path fallback
        npc = self.npc_generator.generate_enemy_npc(
            name=name,
            enemy_type=enemy_type,
            level=level,
            location=location
        )
        # Add to manager
        self.npc_manager.add_npc(npc)
        return npc
    
    def create_merchant(self,
                       name: Optional[str] = None,
                       shop_type: str = "general",
                       location: Optional[str] = None,
                       description: Optional[str] = None) -> NPC:
        """
        Create a merchant NPC specialized for commerce interactions.
        
        Args:
            name: Optional name for the merchant
            shop_type: Type of shop (e.g., "general", "weapons", "potions")
            location: Where the merchant is located
            description: Optional description of the merchant
            
        Returns:
            The newly created merchant NPC
        """
        # Generate a merchant-focused description if none provided
        if not description and name:
            description = f"{name} is a {shop_type} merchant offering goods for sale."
        elif not description:
            description = f"A {shop_type} merchant offering goods for sale."
        
        # Families-mode path for non-combat NPCs
        try:
            cfg = get_config()
            mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        except Exception:
            mode = "legacy"

        if mode == "families":
            from core.character.npc_family_generator import NPCFamilyGenerator
            fam_gen = NPCFamilyGenerator()
            # Determine culture hint from location (optional)
            culture_hint = None
            try:
                seed = f"merchant|{location or ''}|{shop_type}|{name or ''}"
                if location:
                    # Prefer culture_mix if present
                    mix = cfg.get(f"locations.{location}.culture_mix")
                    if isinstance(mix, dict) and mix:
                        culture_hint = self._choose_from_weighted_map(mix, seed)
                    else:
                        culture_hint = cfg.get(f"locations.{location}.culture")
                if not culture_hint:
                    # Global default mix if available
                    mix_def = cfg.get("location_defaults.culture_mix")
                    if isinstance(mix_def, dict) and mix_def:
                        culture_hint = self._choose_from_weighted_map(mix_def, seed)
            except Exception:
                pass
            family_id = fam_gen.choose_humanoid_family(culture_hint=culture_hint, location=location, seed=seed) or "humanoid_normal_base"

            # Difficulty/encounter from config
            difficulty = (cfg.get("game.difficulty", "normal") or "normal")
            encounter_size = (cfg.get("game.encounter_size", "solo") or "solo")

            npc = fam_gen.generate_npc_from_family(
                family_id=family_id,
                name=name,
                location=location,
                level=1,
                overlay_id=None,
                difficulty=difficulty,
                encounter_size=encounter_size,
            )
            # Adjust for commerce context
            npc.npc_type = NPCType.MERCHANT
            npc.relationship = NPCRelationship.NEUTRAL
            if not npc.description:
                npc.description = description or (f"A {shop_type} merchant.")
            # Ensure communicative tag and record commerce metadata
            if npc.known_information is None:
                npc.known_information = {}
            tags = list(npc.known_information.get("tags", []) or [])
            if "communicative:true" not in tags:
                tags.append("communicative:true")
            npc.known_information["tags"] = tags
            npc.known_information["service"] = {"type": "merchant", "shop_type": shop_type}

            # Semi-deterministic naming if not provided
            if not name:
                npc.name = self._generate_semideterministic_name(culture_hint=culture_hint, role_hint="merchant", seed=seed)

            # Mark for LLM flavor (description/backstory) to be enriched later by orchestrated flow
            npc.known_information["needs_llm_flavor"] = True
            npc.known_information["flavor_context"] = {
                "kind": "commerce",
                "shop_type": shop_type,
                "culture": culture_hint,
                "location": location,
                "family_id": family_id,
            }
            # Attempt LLM flavor enrichment (graceful on failure)
            try:
                from core.character.npc_flavor import attempt_enrich_npc_flavor
                attempt_enrich_npc_flavor(npc)
            except Exception:
                pass
            # Persist merchants
            npc.is_persistent = True
            self.npc_manager.add_npc(npc)
            return npc

        # Legacy path fallback
        return self.create_npc(
            interaction_type=NPCInteractionType.COMMERCE,
            name=name,
            npc_type=NPCType.MERCHANT,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            occupation=f"{shop_type}.capitalize() Merchant",
            is_persistent=True  # Merchants are typically persistent
        )
    
    def create_quest_giver(self,
                          name: Optional[str] = None,
                          quest_type: str = "general",
                          location: Optional[str] = None,
                          description: Optional[str] = None) -> NPC:
        """
        Create a quest giver NPC specialized for quest interactions.
        
        Args:
            name: Optional name for the quest giver
            quest_type: Type of quest (e.g., "fetch", "kill", "escort")
            location: Where the quest giver is located
            description: Optional description of the quest giver
            
        Returns:
            The newly created quest giver NPC
        """
        # Generate a quest-focused description if none provided
        if not description and name:
            description = f"{name} is looking for someone to help with a {quest_type} task."
        elif not description:
            description = f"Someone looking for help with a {quest_type} task."
        
        # Families-mode path
        try:
            cfg = get_config()
            mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        except Exception:
            mode = "legacy"

        if mode == "families":
            from core.character.npc_family_generator import NPCFamilyGenerator
            fam_gen = NPCFamilyGenerator()
            culture_hint = None
            try:
                seed = f"quest_giver|{location or ''}|{quest_type}|{name or ''}"
                if location:
                    mix = cfg.get(f"locations.{location}.culture_mix")
                    if isinstance(mix, dict) and mix:
                        culture_hint = self._choose_from_weighted_map(mix, seed)
                    else:
                        culture_hint = cfg.get(f"locations.{location}.culture")
                if not culture_hint:
                    mix_def = cfg.get("location_defaults.culture_mix")
                    if isinstance(mix_def, dict) and mix_def:
                        culture_hint = self._choose_from_weighted_map(mix_def, seed)
            except Exception:
                pass
            family_id = fam_gen.choose_humanoid_family(culture_hint=culture_hint, location=location, seed=seed) or "humanoid_normal_base"

            difficulty = (cfg.get("game.difficulty", "normal") or "normal")
            encounter_size = (cfg.get("game.encounter_size", "solo") or "solo")

            npc = fam_gen.generate_npc_from_family(
                family_id=family_id,
                name=name,
                location=location,
                level=1,
                overlay_id=None,
                difficulty=difficulty,
                encounter_size=encounter_size,
            )
            npc.npc_type = NPCType.QUEST_GIVER
            npc.relationship = NPCRelationship.NEUTRAL
            if not npc.description:
                npc.description = description or ("A potential quest giver.")
            if npc.known_information is None:
                npc.known_information = {}
            tags = list(npc.known_information.get("tags", []) or [])
            if "communicative:true" not in tags:
                tags.append("communicative:true")
            if "quest_giver:true" not in tags:
                tags.append("quest_giver:true")
            npc.known_information["tags"] = tags
            npc.known_information["quest"] = {"role": "giver", "type": quest_type}
            if not name:
                npc.name = self._generate_semideterministic_name(culture_hint=culture_hint, role_hint="quest_giver", seed=seed)
            npc.known_information["needs_llm_flavor"] = True
            npc.known_information["flavor_context"] = {
                "kind": "quest",
                "quest_type": quest_type,
                "culture": culture_hint,
                "location": location,
                "family_id": family_id,
            }
            try:
                from core.character.npc_flavor import attempt_enrich_npc_flavor
                attempt_enrich_npc_flavor(npc)
            except Exception:
                pass
            npc.is_persistent = True
            self.npc_manager.add_npc(npc)
            return npc

        # Legacy fallback
        return self.create_npc(
            interaction_type=NPCInteractionType.QUEST,
            name=name,
            npc_type=NPCType.QUEST_GIVER,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            is_persistent=True  # Quest givers are typically persistent
        )
    
    def create_service_npc(self,
                          name: Optional[str] = None,
                          service_type: str = "innkeeper",
                          location: Optional[str] = None,
                          description: Optional[str] = None) -> NPC:
        """
        Create a service NPC specialized for service interactions.
        
        Args:
            name: Optional name for the service provider
            service_type: Type of service (e.g., "innkeeper", "blacksmith", "healer")
            location: Where the service provider is located
            description: Optional description of the service provider
            
        Returns:
            The newly created service NPC
        """
        # Generate a service-focused description if none provided
        if not description and name:
            description = f"{name} is a {service_type} offering services."
        elif not description:
            description = f"A {service_type} offering services."
        
        # Families-mode path
        try:
            cfg = get_config()
            mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        except Exception:
            mode = "legacy"

        if mode == "families":
            from core.character.npc_family_generator import NPCFamilyGenerator
            fam_gen = NPCFamilyGenerator()
            culture_hint = None
            try:
                seed = f"service|{location or ''}|{service_type}|{name or ''}"
                if location:
                    mix = cfg.get(f"locations.{location}.culture_mix")
                    if isinstance(mix, dict) and mix:
                        culture_hint = self._choose_from_weighted_map(mix, seed)
                    else:
                        culture_hint = cfg.get(f"locations.{location}.culture")
                if not culture_hint:
                    mix_def = cfg.get("location_defaults.culture_mix")
                    if isinstance(mix_def, dict) and mix_def:
                        culture_hint = self._choose_from_weighted_map(mix_def, seed)
            except Exception:
                pass
            family_id = fam_gen.choose_humanoid_family(culture_hint=culture_hint, location=location, seed=seed) or "humanoid_normal_base"

            difficulty = (cfg.get("game.difficulty", "normal") or "normal")
            encounter_size = (cfg.get("game.encounter_size", "solo") or "solo")

            npc = fam_gen.generate_npc_from_family(
                family_id=family_id,
                name=name,
                location=location,
                level=1,
                overlay_id=None,
                difficulty=difficulty,
                encounter_size=encounter_size,
            )
            npc.npc_type = NPCType.SERVICE
            npc.relationship = NPCRelationship.NEUTRAL
            if not npc.description:
                npc.description = description or (f"A {service_type} offering services.")
            if npc.known_information is None:
                npc.known_information = {}
            tags = list(npc.known_information.get("tags", []) or [])
            if "communicative:true" not in tags:
                tags.append("communicative:true")
            npc.known_information["tags"] = tags
            npc.known_information["service"] = {"type": "service", "service_type": service_type}
            # Apply social role variants (guard/official/scholar) as tags
            social_roles = {
                "guard": ["role:guard", "duty:watch"],
                "official": ["role:official"],
                "scholar": ["role:scholar"],
            }
            if service_type in social_roles:
                tags.extend(social_roles[service_type])
                npc.known_information["tags"] = tags
            if not name:
                npc.name = self._generate_semideterministic_name(culture_hint=culture_hint, role_hint=service_type, seed=seed)
            npc.known_information["needs_llm_flavor"] = True
            npc.known_information["flavor_context"] = {
                "kind": "service",
                "service_type": service_type,
                "culture": culture_hint,
                "location": location,
                "family_id": family_id,
            }
            try:
                from core.character.npc_flavor import attempt_enrich_npc_flavor
                attempt_enrich_npc_flavor(npc)
            except Exception:
                pass
            npc.is_persistent = True
            self.npc_manager.add_npc(npc)
            return npc

        # Legacy fallback
        return self.create_npc(
            interaction_type=NPCInteractionType.SERVICE,
            name=name,
            npc_type=NPCType.SERVICE,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            occupation=service_type.capitalize(),
            is_persistent=True  # Service NPCs are typically persistent
        )
    
    def enhance_npc_for_interaction(self, npc: NPC, interaction_type: NPCInteractionType) -> None:
        """
        Enhance an existing NPC with additional details for a new type of interaction.
        This implements the just-in-time generation approach for NPC stats.
        
        Args:
            npc: The NPC to enhance
            interaction_type: The interaction type to prepare for
        """
        # No need to enhance if the NPC already has stats
        if npc.has_stats() and interaction_type == NPCInteractionType.MINIMAL:
            return
        
        # Generate stats if needed
        if not npc.has_stats():
            logger.info(f"Generating stats for NPC {npc.name} for {interaction_type.name} interaction")
            self.npc_generator.enhance_npc_for_new_interaction(npc, interaction_type)
            return
        
        # For existing NPCs with stats, enhance them for the new interaction
        self.npc_generator.enhance_npc_for_new_interaction(npc, interaction_type)
        
        # Record this enhancement in NPC's logs
        if not npc.known_information:
            npc.known_information = {}
        
        if "interaction_history" not in npc.known_information:
            npc.known_information["interaction_history"] = []
        
        npc.known_information["interaction_history"].append({
            "type": interaction_type.name,
            "timestamp": str(datetime.now())
        })
        
        logger.info(f"Enhanced NPC {npc.name} for {interaction_type.name} interaction")
    
    def get_or_create_npc(self,
                         name: str,
                         interaction_type: NPCInteractionType,
                         location: Optional[str] = None,
                         description: Optional[str] = None,
                         npc_type: Optional[NPCType] = None,
                         npc_subtype: Optional[str] = None) -> Tuple[NPC, bool]:
        """
        Get an existing NPC by name or create a new one if not found.
        This is the primary method for implementing just-in-time NPC generation.
        
        Args:
            name: Name of the NPC to get or create
            interaction_type: The interaction type needed
            location: Optional location for new NPCs
            description: Optional description for new NPCs
            npc_type: Optional NPC type for new NPCs
            npc_subtype: Optional subtype (e.g., 'boss_dragon', 'merchant')
            
        Returns:
            Tuple of (NPC, was_created) where was_created is True if a new NPC was created
        """
        # Check if the NPC already exists
        existing_npc = self.npc_manager.get_npc_by_name(name)
        
        if existing_npc:
            # Enhance the NPC if necessary for the current interaction
            self.enhance_npc_for_interaction(existing_npc, interaction_type)
            return existing_npc, False
        
        # Create a new NPC
        new_npc = self.create_npc(
            interaction_type=interaction_type,
            name=name,
            npc_type=npc_type,
            npc_subtype=npc_subtype,
            location=location,
            description=description
        )
        
        return new_npc, True

    # ---- Helpers ----
    def _choose_from_weighted_map(self, weights: dict, seed: str) -> Optional[str]:
        """Deterministically choose a key from a {key: weight} mapping."""
        import hashlib, random as _random
        if not isinstance(weights, dict) or not weights:
            return None
        items = [(k, float(v)) for k, v in weights.items() if isinstance(v, (int, float)) and float(v) > 0]
        if not items:
            return None
        rng = _random.Random()
        h = hashlib.md5(seed.encode("utf-8")).digest()
        rng.seed(int.from_bytes(h, byteorder="big", signed=False))
        total = sum(w for _, w in items)
        pick = rng.random() * total
        acc = 0.0
        for k, w in items:
            acc += w
            if pick <= acc:
                return k
        return items[-1][0]

    def _generate_semideterministic_name(self, culture_hint: Optional[str], role_hint: Optional[str], seed: str) -> str:
        """Generate a semi-deterministic name using legacy pools as guidance.
        Combines culture/role hints to pick a pool, then selects name parts using a seeded RNG.
        """
        import hashlib, random as _random
        from typing import List
        rng = _random.Random()
        h = hashlib.md5(seed.encode("utf-8")).digest()
        rng.seed(int.from_bytes(h, byteorder="big", signed=False))

        # Try culture-aware names.json first
        try:
            cfg = get_config()
            names = cfg.get("npc_names.cultures") or {}
            culture = culture_hint or "generic"
            spec = names.get(culture) or names.get("generic")
            if spec:
                # Build first and last name from syllables and patterns
                import re
                def build_from_spec(spec_local):
                    pats = spec_local.get("patterns") or ["FN LN"]
                    pat = pats[min(len(pats)-1, rng.randrange(len(pats)))]
                    def gen_first():
                        s = spec_local.get("first_syllables", ["al","an","ar","el","ia"])    
                        n = max(1, min(3, int(rng.random()*3)+1))
                        return "".join(rng.choice(s) for _ in range(n)).capitalize()
                    def gen_last():
                        pref = spec_local.get("last_prefixes", [""])
                        suff = spec_local.get("last_suffixes", ["son","wood","wright","smith"]) 
                        core = spec_local.get("last_cores", ["stone","light","river","storm"]) 
                        form = rng.randrange(3)
                        if form == 0:
                            return (rng.choice(core)+rng.choice(suff)).capitalize()
                        elif form == 1:
                            return (rng.choice(pref)+rng.choice(core)).capitalize()
                        else:
                            return (rng.choice(core)).capitalize()
                    fn = gen_first()
                    ln = gen_last()
                    return pat.replace("FN", fn).replace("LN", ln)
                name = build_from_spec(spec)
                # Ensure simple validation
                allowed = spec.get("allowed_chars", "^[A-Za-z' -]+$")
                if re.match(allowed, name):
                    return name
        except Exception:
            pass
        # Fallback to legacy name pools
        pools = {}
        try:
            cfg = get_config()
            pools = cfg.get("npc_legacy_templates.name_pools") or {}
        except Exception:
            pools = {}
        candidates: List[str] = []
        if role_hint == "merchant" and "merchant" in pools:
            candidates.append("merchant")
        if culture_hint == "concordant" and "generic" in pools:
            candidates.append("generic")
        if "fantasy" in pools:
            candidates.append("fantasy")
        if not candidates and pools:
            candidates = list(pools.keys())
        pool_key = rng.choice(candidates) if candidates else None
        pool = pools.get(pool_key, {}) if pool_key else {}
        gender_key = rng.choice(["male", "female"]) if pool else None
        first_list = list(pool.get(gender_key, []) or []) if gender_key else []
        last_list = list(pool.get("surname", []) or []) if pool else []
        def pick(lst: List[str], fallback: str) -> str:
            return lst[rng.randrange(len(lst))] if lst else fallback
        first = pick(first_list, "Alex")
        last = pick(last_list, "Smith")
        suffixes = ["an", "el", "is", "on", "ar", "ia"]
        if rng.random() < 0.3:
            first = first + rng.choice(suffixes)
        return f"{first} {last}"
