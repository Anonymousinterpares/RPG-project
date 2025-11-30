from typing import Any, Dict, List, Optional, TYPE_CHECKING
from .enums import EnvironmentalTag, InteractionMode # Import the new enum and InteractionMode

# Placeholder for actual GameState type - replace with real import
if TYPE_CHECKING:
    from core.base.state.game_state import GameState # Corrected GameState import path
    # Add imports for other managers/states if needed, e.g.:
    # from core.player import PlayerState
    # from core.world import WorldState
    # from core.inventory import InventoryManager
    # from core.combat import CombatManager
    # from core.event import EventLog # Assu Katarzyna was ming an event log system

class ContextBuilder:
    """
    Gathers and structures relevant game state information to provide context
    for LLM agents based on the current interaction mode.
    """

    def build_context(self, game_state: 'GameState', mode: InteractionMode, actor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds a context dictionary based on the game state and interaction mode.

        Args:
            game_state: The current state of the game.
            mode: The current interaction mode.
            actor_id: Optional ID of the entity whose perspective the context is for (e.g., player or NPC).

        Returns:
            A dictionary containing structured context information suitable for LLM consumption.
        """
        if not isinstance(mode, InteractionMode):
            raise TypeError(f"Expected InteractionMode, got {type(mode)}")

        common_context = self._get_common_context(game_state)
        mode_specific_context = {}

        if mode == InteractionMode.COMBAT:
            mode_specific_context = self._get_combat_context(game_state)
        elif mode == InteractionMode.SOCIAL_CONFLICT:
            # Assuming social conflict shares similarities with combat for participants
            mode_specific_context = self._get_social_conflict_context(game_state)
        elif mode == InteractionMode.TRADE:
            mode_specific_context = self._get_trade_context(game_state)
        elif mode == InteractionMode.NARRATIVE:
            mode_specific_context = self._get_narrative_context(game_state)
        else:
            # Fallback or error for unsupported modes
            print(f"Warning: Context building not fully implemented for mode: {mode.value}")
            # Or raise NotImplementedError("Context building not implemented for this mode")

        # --- Add Environmental Tags ---
        environment_tags = []
        world_state = getattr(game_state, 'world', None)
        if world_state:
            location = getattr(world_state, 'current_location', None)
            if location:
                # Assume location has an 'environmental_tags' attribute
                # containing EnvironmentalTag enums or strings
                raw_tags = getattr(location, 'environmental_tags', [])
                environment_tags = [tag.name if isinstance(tag, EnvironmentalTag) else str(tag) for tag in raw_tags]
        # --- End Environmental Tags ---


        # Merge common and mode-specific contexts
        # Mode-specific context can override common context keys if necessary
        full_context = {
            'mode': mode.value,
            **common_context,
            **mode_specific_context,
            'environment': environment_tags # Add the environmental tags
        }

        return full_context

    def _get_common_context(self, game_state: 'GameState') -> Dict[str, Any]:
        """Gathers context common to all interaction modes."""
        # --- Access game state components ---
        player_state = game_state.player
        world_state = game_state.world
        
        # For proper stat access, try to get the stats manager
        from core.stats.stats_manager import get_stats_manager
        stats_manager = get_stats_manager()
        # --- End access ---

        context = {}

        # Player Info
        if player_state:
            player_info = {
                'name': getattr(player_state, 'name', 'Player'),
                'id': getattr(player_state, 'id', getattr(player_state, 'stats_manager_id', 'player_id')),
                'stats': {}
            }
            
            # Try to get stats from stats manager
            try:
                player_info['stats'] = {
                    'hp': stats_manager.get_stat_value("HEALTH"),
                    'max_hp': stats_manager.get_stat_value("MAX_HEALTH"),
                    'resolve': stats_manager.get_stat_value("RESOLVE"),
                    'max_resolve': stats_manager.get_stat_value("MAX_RESOLVE"),
                    'strength': stats_manager.get_stat_value("STRENGTH"),
                    'dexterity': stats_manager.get_stat_value("DEXTERITY"),
                    'constitution': stats_manager.get_stat_value("CONSTITUTION"),
                    'intelligence': stats_manager.get_stat_value("INTELLIGENCE"),
                    'wisdom': stats_manager.get_stat_value("WISDOM"),
                    'charisma': stats_manager.get_stat_value("CHARISMA")
                }
            except Exception as e:
                # Fallback to direct attribute access if stats manager doesn't work
                player_info['stats'] = {
                    'hp': getattr(player_state, 'current_hp', None),
                    'max_hp': getattr(player_state, 'max_hp', None),
                    'resolve': getattr(player_state, 'current_resolve', 0.0),
                    'max_resolve': getattr(player_state, 'max_resolve', None)
                }
            
            # Get player status effects
            status_effects = []
            if hasattr(player_state, 'status_effects'):
                # Similar pattern to how we handled combat entities
                if isinstance(player_state.status_effects, dict):
                    status_effects = [{'name': k, 'duration': v} for k, v in player_state.status_effects.items()]
                elif hasattr(player_state, 'get_active_status_effects'):
                    status_effects = player_state.get_active_status_effects()
                elif isinstance(player_state.status_effects, (list, set)):
                    status_effects = list(player_state.status_effects)
            player_info['status_effects'] = status_effects
            
            context['player'] = player_info

        # Inventory Info (Relevant Items)
        inventory_manager = getattr(player_state, 'inventory_manager', None)
        if inventory_manager:
            equipped = getattr(inventory_manager, 'get_equipped_items', lambda: [])() # Placeholder
            quest_items = getattr(inventory_manager, 'get_quest_items', lambda: [])() # Placeholder
            context['inventory'] = {
                'equipped': [item.name for item in equipped], # Assuming items have a 'name' attribute
                'quest_items': [item.name for item in quest_items],
            }

        # World/Environment Info
        # Determine location object, falling back to player if world is missing
        location_obj = None
        if world_state:
            location_obj = getattr(world_state, 'current_location', None)
        
        if not location_obj and player_state:
            location_obj = getattr(player_state, 'current_location', None)

        if location_obj:
            if isinstance(location_obj, str):
                context['location'] = {
                    'name': location_obj,
                    'description': '',
                    'tags': []
                }
            else:
                context['location'] = {
                    'name': getattr(location_obj, 'name', 'Unknown Area'),
                    'description': getattr(location_obj, 'description', ''),
                    'tags': getattr(location_obj, 'tags', []),
                }
        else:
             context['location'] = {'name': 'Unknown Location'}

        # Use enhanced time description instead of clock time
        context['time_of_day'] = world_state.time_of_day if world_state and hasattr(world_state, 'time_of_day') else 'Unknown'
        
        # --- NEW: NPC Presence Context ---
        # Expose specific NPCs at the location to the LLM, highlighting those with loot.
        current_loc_id = getattr(game_state.player, 'current_location', None)
        if current_loc_id:
            try:
                from core.character.npc_system import get_npc_system
                sys = get_npc_system()
                visible_npcs = sys.get_npcs_by_location(current_loc_id)
                
                npc_context_list = []
                for npc in visible_npcs:
                    # Skip if dead (check stats if available)
                    is_dead = False
                    if npc.has_stats() and npc.stats_manager:
                        try:
                            from core.stats.stats_base import DerivedStatType
                            hp = npc.stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
                            if hp <= 0: is_dead = True
                        except: pass
                    
                    if is_dead: continue

                    # Check for player loot
                    has_loot = False
                    if hasattr(npc, 'inventory') and npc.inventory:
                        has_loot = True
                    
                    desc = f"{npc.name}"
                    if has_loot:
                        desc += " (Holding your items)"
                    elif npc.npc_type.name == "ENEMY":
                        desc += " (Hostile)"
                    
                    npc_context_list.append(desc)
                
                if npc_context_list:
                    context['present_npcs'] = npc_context_list
                    
            except Exception as e:
                # Non-fatal error in context building
                pass

        # Recent Events
        event_log = getattr(world_state, 'event_log', None) # Placeholder
        if event_log:
            # Get the last N significant events (adjust N as needed)
            recent_events = getattr(event_log, 'get_recent_events', lambda limit: [])(limit=5) # Placeholder
            context['recent_events'] = [str(event) for event in recent_events] # Assuming events have __str__

        return context

    def _get_combat_context(self, game_state: 'GameState') -> Dict[str, Any]:
        """Gathers context specific to combat mode."""
        # --- Access game state components directly ---
        combat_manager = game_state.combat_manager
        world_state = game_state.world
        # --- End Access ---

        context = {}

        if combat_manager:
            participants_data = []
            # Try to get combat entities directly from the combat manager
            entities = getattr(combat_manager, 'entities', {})
            
            # Current entity info
            current_entity_id = getattr(combat_manager, 'get_current_entity_id', lambda: None)()
            current_entity = entities.get(current_entity_id) if current_entity_id else None
            
            # Find player entity
            player_entity = None
            player_id = None
            for entity_id, entity in entities.items():
                if hasattr(entity, 'entity_type') and hasattr(entity.entity_type, 'name') and entity.entity_type.name == 'PLAYER':
                    player_entity = entity
                    player_id = entity_id
                    break
            
            # Add entities as participants
            for entity_id, entity in entities.items():
                if not hasattr(entity, 'name'): 
                    continue  # Skip entities with missing data
                
                # Get status effects formatted safely
                status_effects = []
                if hasattr(entity, 'status_effects'):
                    if isinstance(entity.status_effects, dict):
                        # New method using dict of status effects
                        status_effects = [{'name': effect_name, 'duration': duration} 
                                        for effect_name, duration in entity.status_effects.items()]
                    elif isinstance(entity.status_effects, (list, set)):
                        # Old method using list/set of effect names
                        status_effects = [{'name': effect} for effect in entity.status_effects]
                
                # Format entity data
                entity_data = {
                    'id': entity_id,
                    'name': entity.name,
                    'hp': getattr(entity, 'current_hp', 0),
                    'max_hp': getattr(entity, 'max_hp', 0),
                    'mp': getattr(entity, 'current_mp', 0) if hasattr(entity, 'current_mp') else 0,
                    'max_mp': getattr(entity, 'max_mp', 0) if hasattr(entity, 'max_mp') else 0,
                    'status_effects': status_effects,
                    'entity_type': getattr(entity.entity_type, 'name', 'UNKNOWN') if hasattr(entity, 'entity_type') else 'UNKNOWN'
                }
                
                # Include combat stats if available
                if hasattr(entity, 'stats') and isinstance(entity.stats, dict):
                    # Extract key combat stats
                    combat_stats = {
                        'strength': entity.stats.get('strength', 0),
                        'dexterity': entity.stats.get('dexterity', 0),
                        'constitution': entity.stats.get('constitution', 0),
                        'intelligence': entity.stats.get('intelligence', 0), 
                        'wisdom': entity.stats.get('wisdom', 0),
                        'charisma': entity.stats.get('charisma', 0),
                        'attack': entity.stats.get('attack', 0),
                        'defense': entity.stats.get('defense', 0),
                        'initiative': entity.stats.get('initiative', 0),
                    }
                    entity_data['stats'] = combat_stats
                
                participants_data.append(entity_data)
                
            # Store participants
            context['participants'] = participants_data
            
            # Build combat-specific context
            combat_context = {
                'turn_order': combat_manager.turn_order,
                'current_turn': current_entity_id,
                'round': combat_manager.round_number,
                'current_entity': None,
                'player': None
            }
            
            # Add current entity info
            if current_entity:
                combat_context['current_entity'] = {
                    'id': current_entity_id,
                    'name': current_entity.name,
                    'hp': getattr(current_entity, 'current_hp', 0),
                    'max_hp': getattr(current_entity, 'max_hp', 0)
                }
                
            # Add player entity info
            if player_entity:
                combat_context['player'] = {
                    'id': player_id,
                    'name': player_entity.name,
                    'hp': getattr(player_entity, 'current_hp', 0),
                    'max_hp': getattr(player_entity, 'max_hp', 0)
                }
                
            context['combat_context'] = combat_context

        # Environment details relevant to combat
        if world_state:
            location = getattr(world_state, 'current_location', None)
            if location:
                 # Example: Filter tags or get specific combat-relevant properties
                interactables = getattr(location, 'get_interactables', lambda: [])() # Placeholder
                context['environment_interactables'] = [str(i) for i in interactables] # Placeholder

        return context

    def _get_social_conflict_context(self, game_state: 'GameState') -> Dict[str, Any]:
        """Gathers context specific to social conflict mode."""
        context = {}
        participants_data = []
        # Access current_combatants directly from game_state
        # Need to fetch actual participant objects based on IDs
        participant_ids = game_state.current_combatants
        world = game_state.world # Assume world has a way to get characters by ID
        participants = [getattr(world, 'get_character', lambda char_id: None)(pid) for pid in participant_ids]
        participants = [p for p in participants if p is not None] # Filter out not found participants

        # Define key social elements to fetch
        social_stats_keys = ['Charisma', 'Willpower', 'Insight']
        social_skills_keys = ['Persuasion', 'Intimidation', 'Deception', 'Insight'] # Assuming Insight skill exists too

        for p in participants:
            # Access stats manager, assuming it exists on participant objects
            stats_manager = getattr(p, 'stats_manager', None)

            social_stats = {}
            social_skills = {}
            if stats_manager:
                for stat in social_stats_keys:
                    social_stats[stat] = getattr(stats_manager, 'get_stat_value', lambda k, d=None: d)(stat, None)
                for skill in social_skills_keys:
                    social_skills[skill] = getattr(stats_manager, 'get_skill_value', lambda k, d=None: d)(skill, None)

            # Get active *social* effects specifically
            active_effects = getattr(p, 'active_social_effects', [])
            # Ensure effects are serializable (e.g., get their names or dict representation)
            serializable_effects = []
            for effect in active_effects:
                if hasattr(effect, 'to_dict'):
                    serializable_effects.append(effect.to_dict())
                elif hasattr(effect, 'name'):
                     serializable_effects.append(effect.name)
                else:
                     serializable_effects.append(str(effect))


            participants_data.append({
                'id': getattr(p, 'id', 'unknown_id'),
                'name': getattr(p, 'name', 'Unknown Participant'),
                'resolve': getattr(p, 'current_resolve', None),
                'max_resolve': getattr(p, 'max_resolve', None),
                'social_stats': social_stats,
                'social_skills': social_skills,
                'active_social_effects': serializable_effects,
                # 'disposition': getattr(p, 'disposition_towards_player', 'neutral'), # Optional/Future
            })

        context['participants'] = participants_data

        # Recent social events might be implicitly covered by 'recent_events' in common context
        # If more specific social event tracking exists, add it here.

        return context

    def _get_trade_context(self, game_state: 'GameState') -> Dict[str, Any]:
        """Gathers context specific to trade mode."""
        context = {}
        # Assume inventory manager is part of player state or accessible differently
        player = game_state.player
        inventory_manager = getattr(player, 'inventory_manager', None) # Example: Access via player
        world = game_state.world
        partner_id = game_state.current_trade_partner_id

        if not inventory_manager or not world or not player:
            # Log warning or handle missing components
            return context # Cannot build full trade context

        # --- Player Trade Info ---
        player_currency = 0
        player_trade_items = []
        if player and hasattr(player, 'id'): # Check if player object and id exist
            player_currency = getattr(inventory_manager, 'get_currency', lambda owner_id: 0)(player.id)
            player_inv = getattr(inventory_manager, 'get_inventory', lambda owner_id: [])(player.id)
            player_trade_items = [
                {'name': item.name, 'value': getattr(item, 'base_value', 0), 'id': getattr(item, 'id', None)} # Assuming items have name, base_value, id
                for item in player_inv if getattr(item, 'can_be_traded', True) # Filter for tradable items
            ]

        context['player_trade_info'] = {
            'currency': player_currency,
            'inventory': player_trade_items
        }

        # --- Trade Partner Info ---
        if partner_id:
            partner = getattr(world, 'get_character', lambda char_id: None)(partner_id) # Fetch partner object
            if partner:
                partner_currency = getattr(inventory_manager, 'get_currency', lambda owner_id: 0)(partner.id) # Get partner currency
                partner_inv = getattr(inventory_manager, 'get_inventory', lambda owner_id: [])(partner.id) # Get partner inventory
                partner_trade_items = [
                    {'name': item.name, 'value': getattr(item, 'base_value', 0), 'id': getattr(item, 'id', None)}
                    for item in partner_inv if getattr(item, 'can_be_traded', True)
                ]

                context['trade_partner'] = {
                    'id': partner_id,
                    'name': getattr(partner, 'name', 'Unknown Merchant'),
                    'currency': partner_currency, # Include partner currency
                    'inventory': partner_trade_items,
                    # Add disposition or other relevant partner info if available
                    # 'disposition': getattr(partner, 'disposition_towards_player', 'neutral'),
                }
            else:
                # Log warning: Partner ID set but character not found
                context['trade_partner'] = {'id': partner_id, 'error': 'Character not found'}
        else:
             context['trade_partner'] = None # No active trade partner

        return context

    def _get_narrative_context(self, game_state: 'GameState') -> Dict[str, Any]:
        """Gathers context specific to narrative mode."""
        # --- Access game state components directly ---
        # Assuming quest_manager and dialogue_manager are part of world or player state
        world_state = game_state.world
        player_state = game_state.player
        quest_manager = getattr(player_state, 'quest_manager', None) # Example access via player
        dialogue_manager = getattr(world_state, 'dialogue_manager', None) # Example access via world
        # --- End Access ---

        context = {}

        # Active Quests
        if quest_manager:
            active_quests = getattr(quest_manager, 'get_active_quests', lambda: [])() # Placeholder
            context['active_quests'] = [
                {'name': q.name, 'objective': getattr(q, 'current_objective', '')} # Assuming quests have name/objective
                for q in active_quests
            ]

        # Recent Dialogue
        if dialogue_manager:
            recent_lines = getattr(dialogue_manager, 'get_recent_dialogue', lambda limit: [])(limit=5) # Placeholder
            context['recent_dialogue'] = [str(line) for line in recent_lines] # Assuming lines have __str__

        # Known NPCs/Locations nearby (if available)
        if world_state:
            location = getattr(world_state, 'current_location', None)
            if location:
                nearby_npcs = getattr(location, 'get_nearby_npcs', lambda: [])() # Placeholder
                nearby_locations = getattr(location, 'get_nearby_locations', lambda: [])() # Placeholder
                context['nearby_npcs'] = [npc.name for npc in nearby_npcs] # Assuming NPCs have name
                context['nearby_locations'] = [loc.name for loc in nearby_locations] # Assuming locations have name

        return context

# Example Usage (Conceptual - requires actual GameState and managers)
if __name__ == '__main__':
    # This is conceptual and won't run without actual game state implementation
    class MockGameState:
        # Add mock attributes/methods matching placeholders used above
        player = type('obj', (object,), {'name': 'MockPlayer', 'current_hp': 90, 'max_hp': 100, 'current_resolve': 50, 'max_resolve': 50, 'get_active_status_effects': lambda: ['focused']})()
        inventory_manager = type('obj', (object,), {
            'get_equipped_items': lambda: [type('obj', (object,), {'name': 'Iron Sword'})()],
            'get_quest_items': lambda: [type('obj', (object,), {'name': 'Mystic Key'})()],
            'get_currency': lambda: 150
        })()
        world = type('obj', (object,), {
            'current_location': type('obj', (object,), {'name': 'Whispering Woods', 'description': 'Ancient trees loom overhead.', 'tags': ['forest', 'overgrown'], 'get_interactables': lambda: ['old_shrine', 'fallen_log']})(),
            'time_of_day': 'afternoon'
        })()
        event_log = type('obj', (object,), {'get_recent_events': lambda limit: ['Player entered Whispering Woods.', 'A twig snapped nearby.']})()
        combat_manager = type('obj', (object,), {
            'get_participants': lambda: [
                type('obj', (object,), {'id': 'wolf_1', 'name': 'Dire Wolf', 'current_hp': 40, 'max_hp': 40, 'get_active_status_effects': lambda: [], 'position': 'close', 'is_player': False})(),
                type('obj', (object,), {'id': 'wolf_2', 'name': 'Alpha Wolf', 'current_hp': 60, 'max_hp': 60, 'get_active_status_effects': lambda: ['enraged'], 'position': 'medium', 'is_player': False})()
            ]
        })()
        # Add mock managers for other modes as needed

    mock_game_state = MockGameState()
    builder = ContextBuilder()

    print("--- Combat Context ---")
    combat_context = builder.build_context(mock_game_state, InteractionMode.COMBAT)
    import json
    print(json.dumps(combat_context, indent=2))

    print("\n--- Narrative Context (Minimal Mock) ---")
    narrative_context = builder.build_context(mock_game_state, InteractionMode.NARRATIVE)
    print(json.dumps(narrative_context, indent=2))

    # Add calls for other modes (TRADE, SOCIAL_CONFLICT) if mocks are implemented