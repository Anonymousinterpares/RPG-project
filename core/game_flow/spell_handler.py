import logging
import random
from typing import Optional, List, Dict, Any

from core.base.commands import CommandResult
from core.magic.spell_catalog import get_spell_catalog
from core.stats.stats_manager import get_stats_manager
from core.effects.effects_engine import apply_effects, TargetContext
from core.stats.stats_base import DerivedStatType
from core.combat.combat_entity import EntityType
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget

logger = logging.getLogger("SPELL_HANDLER")

def execute_cast_spell(engine, spell_id: str, target_id: Optional[str] = None, enforce_known_spells: bool = True) -> CommandResult:
    """
    Execute a spell by id using the minimal effects interpreter.
    Logic moved from GameEngine to separate concern.
    """
    try:
        game_state = engine.state_manager.current_state
        if not game_state:
            return CommandResult.error("No game in progress.")

        # Load spell catalog
        catalog = get_spell_catalog()
        spell = catalog.get_spell_by_id(spell_id)
        if not spell:
            return CommandResult.error(f"Spell not found: {spell_id}")

        # Check if spell has effect atoms
        atoms = spell.effect_atoms
        if not atoms:
            return CommandResult.error(f"Spell '{spell_id}' has no effect atoms to apply.")

        # Enforce known spells gating (release behavior)
        if enforce_known_spells:
            known_spells = game_state.player.list_known_spells()
            if spell_id not in known_spells:
                return CommandResult.error(f"You do not know the spell '{spell.name}'.")

        # Build caster context (player for now)
        caster_sm = get_stats_manager()
        caster_ctx = TargetContext(
            id=getattr(game_state.player, 'id', 'player'), 
            name=getattr(game_state.player, 'name', 'Player'), 
            stats_manager=caster_sm
        )

        # Validate and deduct mana cost
        mana_cost = spell.data.get('mana_cost', 0)
        if mana_cost > 0:
            current_mana = caster_sm.get_current_stat_value(DerivedStatType.MANA)
            if current_mana < mana_cost:
                # SFX: magic failed (insufficient mana)
                try:
                    if hasattr(engine, '_sfx_manager') and engine._sfx_manager:
                        engine._sfx_manager.play_magic_cast(getattr(spell, 'system_id', None), getattr(spell, 'combat_role', None), getattr(spell, 'id', None), failed=True)
                except Exception:
                    pass
                return CommandResult.error(f"Insufficient mana. Need {mana_cost}, have {current_mana:.1f}.")
            
            # Deduct mana cost
            new_mana = max(0, current_mana - mana_cost)
            caster_sm.set_current_stat(DerivedStatType.MANA, new_mana)
            logger.info(f"Deducted {mana_cost} mana for spell '{spell.name}'. Remaining: {new_mana:.1f}")

        # Resolve targets based on spell combat role and selector
        targets: List[TargetContext] = _resolve_spell_targets(spell, target_id, game_state, caster_ctx)
        if not targets:
            return CommandResult.error(f"No valid targets found for spell '{spell.name}'.")

        # SFX: play magic cast
        try:
            if hasattr(engine, '_sfx_manager') and engine._sfx_manager and spell:
                engine._sfx_manager.play_magic_cast(getattr(spell, 'system_id', None), getattr(spell, 'combat_role', None), getattr(spell, 'id', None), failed=False)
        except Exception:
            pass
        
        # Apply effects
        effect_result = apply_effects(atoms=atoms, caster=caster_ctx, targets=targets)
        
        # Emit DisplayEvents if we have a combat orchestrator
        if hasattr(engine, '_combat_orchestrator') and engine._combat_orchestrator:
            
            # Emit spell casting message
            cast_msg = f"{caster_ctx.name} casts {spell.name}!"
            if mana_cost > 0:
                cast_msg += f" (Cost: {mana_cost} mana)"
                
            engine._combat_orchestrator.add_event_to_queue(
                DisplayEvent(
                    type=DisplayEventType.SYSTEM_MESSAGE,
                    content=cast_msg,
                    target_display=DisplayTarget.COMBAT_LOG
                )
            )
            
            # Emit effect results
            for applied_effect in effect_result.applied:
                effect_msg = f"  {applied_effect.get('description', 'Effect applied')}"
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(
                        type=DisplayEventType.SYSTEM_MESSAGE,
                        content=effect_msg,
                        target_display=DisplayTarget.COMBAT_LOG
                    )
                )
        
        if effect_result.success:
            return CommandResult.success(f"Spell '{spell.name}' executed. Applied {len(effect_result.applied)} effect(s).")
        else:
            # Partial failures are surfaced as an error string with details
            details = "; ".join(effect_result.errors) if effect_result.errors else "Unknown error"
            return CommandResult.error(f"Spell '{spell.name}' applied with errors: {details}")
            
    except Exception as e:
        logger.error(f"execute_cast_spell failed: {e}", exc_info=True)
        return CommandResult.error(f"Spell execution failed: {e}")

def _resolve_spell_targets(spell, target_id: Optional[str], game_state, caster_ctx) -> List:
    """Resolve spell targets based on combat role and selector."""
    targets = []
    combat_role = spell.combat_role
    
    # If in combat, use combat-specific targeting
    if hasattr(game_state, 'combat_manager') and game_state.combat_manager:
        combat_manager = game_state.combat_manager
        
        if combat_role == 'offensive':
            # Target enemies - user should select, fallback to random if unspecified
            if target_id:
                # Specific target requested by user
                entity = combat_manager.get_entity_by_id(target_id)
                if entity and entity.entity_type == EntityType.ENEMY and entity.is_alive():
                    stats_manager = combat_manager._get_entity_stats_manager(target_id)
                    if stats_manager:
                        targets.append(TargetContext(
                            id=entity.id,
                            name=getattr(entity, 'combat_name', entity.id),
                            stats_manager=stats_manager
                        ))
            else:
                # Fallback: if one enemy, target it; if multiple, pick random alive enemy
                alive_enemies = [e for e in combat_manager.entities.values() 
                               if e.entity_type == EntityType.ENEMY and e.is_alive()]
                if len(alive_enemies) == 1:
                    # Only one enemy - safe to auto-target
                    enemy = alive_enemies[0]
                    stats_manager = combat_manager._get_entity_stats_manager(enemy.id)
                    if stats_manager:
                        targets.append(TargetContext(
                            id=enemy.id,
                            name=getattr(enemy, 'combat_name', enemy.id),
                            stats_manager=stats_manager
                        ))
                elif len(alive_enemies) > 1:
                    enemy = random.choice(alive_enemies)
                    stats_manager = combat_manager._get_entity_stats_manager(enemy.id)
                    if stats_manager:
                        targets.append(TargetContext(
                            id=enemy.id,
                            name=getattr(enemy, 'combat_name', enemy.id),
                            stats_manager=stats_manager
                        ))
                        
        elif combat_role in ['defensive', 'utility']:
            # Target self or ally
            if target_id:
                # Specific target requested (could be self or ally)
                entity = combat_manager.get_entity_by_id(target_id)
                if entity and entity.entity_type == EntityType.PLAYER and entity.is_alive():
                    stats_manager = combat_manager._get_entity_stats_manager(target_id)
                    if stats_manager:
                        targets.append(TargetContext(
                            id=entity.id,
                            name=getattr(entity, 'combat_name', entity.id),
                            stats_manager=stats_manager
                        ))
            else:
                # Default to self-targeting for defensive spells
                targets.append(caster_ctx)
    else:
        # Non-combat context: generally allow self-targeting or specific targets
        if target_id:
            # Try to find the specific target (for future expansion)
            targets.append(caster_ctx)  # For now, fallback to self
        else:
            # Default to self
            targets.append(caster_ctx)
            
    return targets