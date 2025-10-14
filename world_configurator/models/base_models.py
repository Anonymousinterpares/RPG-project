"""
Base data models for the World Configurator Tool.
"""

from dataclasses import dataclass, field, asdict, fields # Added 'fields' import
from typing import Dict, List, Any, Optional, Union, Literal
import json
import uuid
import logging

logger = logging.getLogger("world_configurator.models")

@dataclass
class BaseModel:
    """Base class for all data models."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create a model instance from a dictionary."""
        # Basic implementation, might need overrides in subclasses for complex types
        # Filter data to only include fields defined in the dataclass
        known_fields = {f.name for f in fields(cls)} # Use imported 'fields'
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        try:
            return cls(**filtered_data)
        except TypeError as e:
            logger.error(f"Error creating {cls.__name__} from dict. Data: {filtered_data}, Error: {e}")
            # Attempt to create with minimal required fields if possible, or raise
            # This part depends on how you want to handle partial data.
            # For now, re-raising might be safer.
            raise e

    def to_json(self, indent: int = 2) -> str:
        """Convert the model to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """Create a model instance from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID."""
        return str(uuid.uuid4())


@dataclass
class WorldModelState:
    """
    Tracks the state of a model (modified status, etc.)
    """
    modified: bool = False
    path: Optional[str] = None

    def mark_modified(self) -> None:
        """Mark the model as modified."""
        self.modified = True

    def mark_saved(self, path: str) -> None:
        """Mark the model as saved."""
        self.modified = False
        self.path = path

# --- Culture Related ---
@dataclass
class CultureValue:
    """
    Represents a cultural value.
    """
    name: str
    description: str
    importance: int = 5  # 1-10 scale

@dataclass
class Tradition:
    """
    Represents a cultural tradition.
    """
    name: str
    description: str
    occasion: str
    significance: str

@dataclass
class Culture(BaseModel):
    """
    Represents a culture in the game world.
    """
    id: str
    name: str
    description: str
    values: List[CultureValue] = field(default_factory=list)
    traditions: List[Tradition] = field(default_factory=list)
    language_style: str = ""
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    common_traits: List[str] = field(default_factory=list)

    @classmethod
    def create_new(cls, name: str, description: str) -> 'Culture':
        """Create a new culture with a unique ID."""
        culture_id = cls.generate_id()
        return cls(
            id=culture_id,
            name=name,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Culture':
        """Create a culture instance from a dictionary."""
        data_copy = data.copy()
        if 'values' in data_copy and isinstance(data_copy['values'], list):
            values = []
            for value_data in data_copy['values']:
                if isinstance(value_data, dict):
                    values.append(CultureValue(**value_data))
                elif isinstance(value_data, CultureValue): # Handle already converted objects
                    values.append(value_data)
            data_copy['values'] = values

        if 'traditions' in data_copy and isinstance(data_copy['traditions'], list):
            traditions = []
            for tradition_data in data_copy['traditions']:
                if isinstance(tradition_data, dict):
                    traditions.append(Tradition(**tradition_data))
                elif isinstance(tradition_data, Tradition): # Handle already converted objects
                    traditions.append(tradition_data)
            data_copy['traditions'] = traditions

        # Use superclass from_dict for basic field assignment after handling nested lists
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)


# --- Location Related ---
@dataclass
class LocationConnection:
    """
    Represents a connection between locations.
    """
    target: str  # ID of the target location
    description: str
    travel_time: int  # In minutes
    requirements: List[str] = field(default_factory=list)

@dataclass
class LocationFeature:
    """
    Represents a special feature of a location.
    """
    name: str
    description: str
    interaction_type: str = "none"  # none, examine, use, etc.

@dataclass
class Location(BaseModel):
    """
    Represents a location in the game world.
    """
    id: str
    name: str
    description: str
    type: str  # village, city, dungeon, etc.
    region: str = ""
    culture_id: str = ""
    population: int = 0
    culture_mix: Dict[str, float] = field(default_factory=dict)
    features: List[LocationFeature] = field(default_factory=list)
    connections: List[LocationConnection] = field(default_factory=list)
    npcs: List[str] = field(default_factory=list)  # IDs of important NPCs

    @classmethod
    def create_new(cls, name: str, description: str, location_type: str) -> 'Location':
        """Create a new location with a unique ID."""
        location_id = cls.generate_id()
        return cls(
            id=location_id,
            name=name,
            description=description,
            type=location_type
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Create a location instance from a dictionary."""
        data_copy = data.copy()
        if 'features' in data_copy and isinstance(data_copy['features'], list):
            features = []
            for feature_data in data_copy['features']:
                if isinstance(feature_data, dict):
                    features.append(LocationFeature(**feature_data))
                elif isinstance(feature_data, LocationFeature):
                    features.append(feature_data)
            data_copy['features'] = features

        if 'connections' in data_copy and isinstance(data_copy['connections'], list):
            connections = []
            for connection_data in data_copy['connections']:
                if isinstance(connection_data, dict):
                    connections.append(LocationConnection(**connection_data))
                elif isinstance(connection_data, LocationConnection):
                    connections.append(connection_data)
            data_copy['connections'] = connections

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

# --- History Related ---
@dataclass
class HistoricalEvent:
    """
    Represents a significant historical event.
    """
    year: int
    title: str
    description: str
    significance: str = ""
    affected_locations: List[str] = field(default_factory=list)
    affected_cultures: List[str] = field(default_factory=list)

@dataclass
class Era:
    """
    Represents a historical era.
    """
    name: str
    start_year: int
    end_year: int
    description: str
    events: List[HistoricalEvent] = field(default_factory=list)

@dataclass
class WorldHistory(BaseModel):
    """
    Represents the history of the game world.
    """
    name: str
    description: str
    current_year: int
    eras: List[Era] = field(default_factory=list)

    @classmethod
    def create_new(cls, name: str, description: str, current_year: int) -> 'WorldHistory':
        """Create a new world history."""
        return cls(
            name=name,
            description=description,
            current_year=current_year
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldHistory':
        """Create a world history instance from a dictionary."""
        data_copy = data.copy()
        if 'eras' in data_copy and isinstance(data_copy['eras'], list):
            eras = []
            for era_data in data_copy['eras']:
                if isinstance(era_data, dict):
                    events = []
                    if 'events' in era_data and isinstance(era_data['events'], list):
                        for event_data in era_data['events']:
                            if isinstance(event_data, dict):
                                events.append(HistoricalEvent(**event_data))
                            elif isinstance(event_data, HistoricalEvent):
                                events.append(event_data)
                    era_data['events'] = events # Update the dict before creating Era
                    eras.append(Era(**era_data))
                elif isinstance(era_data, Era):
                    eras.append(era_data)
            data_copy['eras'] = eras

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

# --- Quest Related ---
@dataclass
class QuestObjective:
    """
    Represents an objective in a quest.
    """
    id: str
    description: str
    type: str  # fetch, kill, escort, etc.
    target_id: str = ""
    location_id: str = ""
    completion_criteria: str = ""
    rewards: Dict[str, Any] = field(default_factory=dict)
    mandatory: bool = True

@dataclass
class Quest(BaseModel):
    """
    Represents a quest in the game.
    """
    id: str
    title: str
    description: str
    giver_id: str = ""
    level: int = 1
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)

    @classmethod
    def create_new(cls, title: str, description: str) -> 'Quest':
        """Create a new quest with a unique ID."""
        quest_id = cls.generate_id()
        return cls(
            id=quest_id,
            title=title,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Quest':
        """Create a quest instance from a dictionary."""
        data_copy = data.copy()
        if 'objectives' in data_copy and isinstance(data_copy['objectives'], list):
            objectives = []
            for obj_data in data_copy['objectives']:
                if isinstance(obj_data, dict):
                    if 'id' not in obj_data: obj_data['id'] = cls.generate_id() # Ensure ID
                    if 'mandatory' not in obj_data:
                        obj_data['mandatory'] = True
                    objectives.append(QuestObjective(**obj_data))
                elif isinstance(obj_data, QuestObjective):
                    if not hasattr(obj_data, 'mandatory'):
                        try:
                            setattr(obj_data, 'mandatory', True)
                        except Exception:
                            pass
                    objectives.append(obj_data)
            data_copy['objectives'] = objectives

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

# --- Rules Related ---
@dataclass
class FundamentalRule:
    """
    Represents a fundamental rule of the game world.
    """
    name: str
    description: str
    category: str  # magic, physics, society, etc.
    effects: List[str] = field(default_factory=list)

@dataclass
class WorldRules(BaseModel):
    """
    Represents the fundamental rules of the game world.
    """
    name: str
    description: str
    rules: List[FundamentalRule] = field(default_factory=list)

    @classmethod
    def create_new(cls, name: str, description: str) -> 'WorldRules':
        """Create a new world rules definition."""
        return cls(
            name=name,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldRules':
        """Create a WorldRules instance from a dictionary."""
        data_copy = data.copy()
        if 'rules' in data_copy and isinstance(data_copy['rules'], list):
            rules = []
            for rule_data in data_copy['rules']:
                if isinstance(rule_data, dict):
                    rules.append(FundamentalRule(**rule_data))
                elif isinstance(rule_data, FundamentalRule):
                    rules.append(rule_data)
            data_copy['rules'] = rules

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)


# --- Magic System Related ---
@dataclass
class SpellEffect:
    """
    Represents a single effect of a spell.
    """
    target_type: Literal["caster", "target"] = "target"
    effect_type: Literal["damage", "healing", "stat_modification", "status_effect"] = "damage"
    value: float = 0.0
    stat_affected: str = ""
    status_effect: str = ""
    duration: int = 0
    dice_notation: str = ""
    description: str = ""

@dataclass
class Spell(BaseModel):
    """
    Represents a spell in the magic system.
    """
    id: str
    name: str
    description: str
    mana_cost: int = 0
    casting_time: str = "1 action"
    range: str = "10m"
    target: str = "single"
    effects: List[SpellEffect] = field(default_factory=list)
    # New: effect_atoms for modern engine path (JSON schema: config/gameplay/effect_atoms.schema.json)
    effect_atoms: List[Dict[str, Any]] = field(default_factory=list)
    level: int = 1
    components: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    combat_role: Literal["offensive", "defensive", "utility"] = "offensive"

    @classmethod
    def create_new(cls, name: str, description: str) -> 'Spell':
        """Create a new spell with a unique ID."""
        spell_id = cls.generate_id()
        return cls(
            id=spell_id,
            name=name,
            description=description,
            combat_role="offensive"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Spell':
        """Create a spell instance from a dictionary."""
        data_copy = data.copy()
        if 'effects' in data_copy and isinstance(data_copy['effects'], list):
            effects = []
            for effect_data in data_copy['effects']:
                if isinstance(effect_data, dict):
                    effects.append(SpellEffect(**effect_data))
                elif isinstance(effect_data, SpellEffect):
                    effects.append(effect_data)
            data_copy['effects'] = effects
        # Effect atoms: accept pass-through list of dicts
        if 'effect_atoms' in data_copy and isinstance(data_copy['effect_atoms'], list):
            try:
                atoms = []
                for a in data_copy['effect_atoms']:
                    if isinstance(a, dict):
                        atoms.append(a)
                data_copy['effect_atoms'] = atoms
            except Exception:
                data_copy['effect_atoms'] = []
        # Normalize combat_role if present; default to 'offensive'
        if 'combat_role' in data_copy:
            try:
                role = str(data_copy['combat_role']).strip().lower()
                if role in ("offensive", "defensive", "utility"):
                    data_copy['combat_role'] = role
                else:
                    data_copy['combat_role'] = "offensive"
            except Exception:
                data_copy['combat_role'] = "offensive"
        else:
            data_copy['combat_role'] = "offensive"

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

@dataclass
class RacialAffinity:
    """
    Represents a race's affinity to a magical system.
    """
    affinity_level: str = "Medium"
    learning_difficulty: str = "Moderate"
    natural_talent: bool = False
    bonus_effects: Optional[str] = None

@dataclass
class ClassAffinity:
    """
    Represents a class's affinity to a magical system.
    """
    affinity_level: str = "Medium"
    learning_difficulty: str = "Moderate"
    required_stats: Dict[str, int] = field(default_factory=dict)

@dataclass
class MagicalSystem(BaseModel):
    """
    Represents a magical system in the game world.
    """
    id: str
    name: str
    description: str
    origin: str = ""
    limitations: str = ""
    practitioners: str = ""
    cultural_significance: str = ""
    racial_affinities: Dict[str, RacialAffinity] = field(default_factory=dict)
    class_affinities: Dict[str, ClassAffinity] = field(default_factory=dict)
    spells: Dict[str, Spell] = field(default_factory=dict)

    @classmethod
    def create_new(cls, name: str, description: str) -> 'MagicalSystem':
        """Create a new magical system with a unique ID."""
        system_id = cls.generate_id()
        return cls(
            id=system_id,
            name=name,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MagicalSystem':
        """Create a magical system instance from a dictionary."""
        data_copy = data.copy()
        if 'spells' in data_copy and isinstance(data_copy['spells'], dict):
            spells = {}
            for spell_id, spell_data in data_copy['spells'].items():
                if isinstance(spell_data, dict):
                    if 'id' not in spell_data: spell_data['id'] = spell_id
                    spells[spell_id] = Spell.from_dict(spell_data)
                elif isinstance(spell_data, Spell):
                    spells[spell_id] = spell_data
            data_copy['spells'] = spells

        if 'racial_affinities' in data_copy and isinstance(data_copy['racial_affinities'], dict):
            racial_affinities = {}
            for race_name, affinity_data in data_copy['racial_affinities'].items():
                if isinstance(affinity_data, dict):
                    racial_affinities[race_name] = RacialAffinity(**affinity_data)
                elif isinstance(affinity_data, RacialAffinity):
                    racial_affinities[race_name] = affinity_data
            data_copy['racial_affinities'] = racial_affinities

        if 'class_affinities' in data_copy and isinstance(data_copy['class_affinities'], dict):
            class_affinities = {}
            for class_name, affinity_data in data_copy['class_affinities'].items():
                if isinstance(affinity_data, dict):
                    class_affinities[class_name] = ClassAffinity(**affinity_data)
                elif isinstance(affinity_data, ClassAffinity):
                    class_affinities[class_name] = affinity_data
            data_copy['class_affinities'] = class_affinities

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)


# --- Race and Class Related (MOVED HERE) ---
@dataclass
class RaceTrait:
    """Represents a specific trait of a race."""
    name: str
    description: str

@dataclass
class Race(BaseModel):
    """Represents a playable race in the game world."""
    id: str
    name: str
    description: str
    stat_modifiers: Dict[str, int] = field(default_factory=dict)
    traits: List[RaceTrait] = field(default_factory=list)
    recommended_classes: List[str] = field(default_factory=list)

    @classmethod
    def create_new(cls, name: str, description: str) -> 'Race':
        """Create a new race with a unique ID."""
        race_id = cls.generate_id()
        return cls(
            id=race_id,
            name=name,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Race':
        """Create a race instance from a dictionary."""
        data_copy = data.copy()
        if 'traits' in data_copy and isinstance(data_copy['traits'], list):
            traits = []
            for trait_data in data_copy['traits']:
                if isinstance(trait_data, dict):
                    traits.append(RaceTrait(**trait_data))
                elif isinstance(trait_data, RaceTrait):
                     traits.append(trait_data)
            data_copy['traits'] = traits

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

@dataclass
class ClassArchetype:
    """Represents a specific archetype or specialization within a class."""
    name: str
    description: str
    stat_distribution: Dict[str, int] = field(default_factory=dict)

@dataclass
class CharacterClass(BaseModel):
    """Represents a character class in the game."""
    id: str
    name: str
    description: str
    stat_modifiers: Dict[str, int] = field(default_factory=dict)
    minimum_stats: Dict[str, int] = field(default_factory=dict)
    recommended_stats: Dict[str, List[str]] = field(default_factory=dict) # e.g., {"primary": ["STR"], "secondary": ["CON"]}
    archetypes: Dict[str, ClassArchetype] = field(default_factory=dict)
    weapon_proficiencies: List[str] = field(default_factory=list)
    armor_proficiencies: List[str] = field(default_factory=list)

    @classmethod
    def create_new(cls, name: str, description: str) -> 'CharacterClass':
        """Create a new class with a unique ID."""
        class_id = cls.generate_id()
        return cls(
            id=class_id,
            name=name,
            description=description
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterClass':
        """Create a class instance from a dictionary."""
        data_copy = data.copy()
        if 'archetypes' in data_copy and isinstance(data_copy['archetypes'], dict):
            archetypes = {}
            for arch_name, arch_data in data_copy['archetypes'].items():
                if isinstance(arch_data, dict):
                     # Ensure name is included if missing in nested dict
                    if 'name' not in arch_data:
                        arch_data['name'] = arch_name
                    archetypes[arch_name] = ClassArchetype(**arch_data)
                # If it's already an object, keep it
                elif isinstance(arch_data, ClassArchetype):
                    archetypes[arch_name] = arch_data
            data_copy['archetypes'] = archetypes

        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered_data)

@dataclass
class OriginTrait:
    """Represents a minor trait granted by an Origin."""
    name: str = ""
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OriginTrait':
        return cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description
        }

@dataclass
class Origin:
    """Represents a starting origin/scenario for a character."""
    id: str = field(default_factory=lambda: f"origin_{uuid.uuid4().hex[:8]}")
    name: str = "New Origin"
    description: str = ""
    starting_location_id: str = ""
    starting_culture_id: Optional[str] = None # Optional culture override
    starting_items: List[str] = field(default_factory=list)
    initial_quests: List[str] = field(default_factory=list)
    suitable_races: List[str] = field(default_factory=list)
    suitable_classes: List[str] = field(default_factory=list)
    introduction_text: str = ""
    skill_proficiencies: List[str] = field(default_factory=list) # NEW
    origin_traits: List[OriginTrait] = field(default_factory=list) # NEW
    
    # Time-related settings for enhanced time management
    starting_time_period: Optional[str] = None  # e.g., "dawn", "noon", "evening", etc.
    starting_season: Optional[str] = None       # e.g., "Spring", "Summer", "Fall", "Winter"
    time_progression_rate: Optional[float] = None  # Custom time scale if different from default

    @classmethod
    def create_new(cls, name: str, description: str, location_id: str) -> 'Origin':
        """Helper to create a new Origin with a default ID."""
        return cls(
            name=name,
            description=description,
            starting_location_id=location_id
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Origin':
        # Handle optional fields gracefully
        traits_data = data.get("origin_traits", [])
        traits = [OriginTrait.from_dict(t) for t in traits_data if isinstance(t, dict)]

        return cls(
            id=data.get("id", f"origin_{uuid.uuid4().hex[:8]}"),
            name=data.get("name", "Unknown Origin"),
            description=data.get("description", ""),
            starting_location_id=data.get("starting_location_id", data.get("starting_location", "")), # Check old key too
            starting_culture_id=data.get("starting_culture_id"), # Okay if None
            starting_items=data.get("starting_items", []),
            initial_quests=data.get("initial_quests", []),
            suitable_races=data.get("suitable_races", []),
            suitable_classes=data.get("suitable_classes", []),
            introduction_text=data.get("introduction_text", ""),
            skill_proficiencies=data.get("skill_proficiencies", []), # NEW
            origin_traits=traits # NEW
        )

    def to_dict(self) -> Dict[str, Any]:
        # Filter out None values for cleaner JSON, especially for optional culture
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "starting_location_id": self.starting_location_id,
            "starting_items": self.starting_items,
            "initial_quests": self.initial_quests,
            "suitable_races": self.suitable_races,
            "suitable_classes": self.suitable_classes,
            "introduction_text": self.introduction_text,
            "skill_proficiencies": self.skill_proficiencies, # NEW
            "origin_traits": [t.to_dict() for t in self.origin_traits] # NEW
        }
        if self.starting_culture_id is not None:
            data["starting_culture_id"] = self.starting_culture_id
        return data

# --- World Config Container
@dataclass
class WorldConfig:
    """
    Container for all world configuration data.
    Uses the unified Origin concept.
    """
    cultures: Dict[str, Culture] = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    history: Optional[WorldHistory] = None
    rules: Optional[WorldRules] = None
    origins: Dict[str, Origin] = field(default_factory=dict)
    quests: Dict[str, Quest] = field(default_factory=dict)
    magic_systems: Dict[str, MagicalSystem] = field(default_factory=dict)
    races: Dict[str, Race] = field(default_factory=dict)
    classes: Dict[str, CharacterClass] = field(default_factory=dict)
    state: WorldModelState = field(default_factory=WorldModelState)

    def add_race(self, race: Race) -> None:
        """Add a race to the configuration."""
        self.races[race.id] = race
        self.state.mark_modified()

    def add_class(self, char_class: CharacterClass) -> None:
        """Add a character class to the configuration."""
        self.classes[char_class.id] = char_class
        self.state.mark_modified()

    # RENAMED add_scenario to add_origin
    def add_origin(self, origin: Origin) -> None:
        """Add a starting origin to the configuration."""
        self.origins[origin.id] = origin
        self.state.mark_modified()

    def add_culture(self, culture: Culture) -> None:
        """Add a culture to the configuration."""
        self.cultures[culture.id] = culture
        self.state.mark_modified()

    def add_location(self, location: Location) -> None:
        """Add a location to the configuration."""
        self.locations[location.id] = location
        self.state.mark_modified()

    def add_magic_system(self, magic_system: MagicalSystem) -> None:
        """Add a magical system to the configuration."""
        self.magic_systems[magic_system.id] = magic_system
        self.state.mark_modified()

    def set_history(self, history: WorldHistory) -> None:
        """Set the world history."""
        self.history = history
        self.state.mark_modified()

    def set_rules(self, rules: WorldRules) -> None:
        """Set the fundamental rules."""
        self.rules = rules
        self.state.mark_modified()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        result = {
            "cultures": {k: v.to_dict() for k, v in self.cultures.items()},
            "locations": {k: v.to_dict() for k, v in self.locations.items()},
            "origins": {k: v.to_dict() for k, v in self.origins.items()}, # RENAMED from scenarios
            "quests": {k: v.to_dict() for k, v in self.quests.items()},
            "magic_systems": {k: v.to_dict() for k, v in self.magic_systems.items()},
            "races": {k: v.to_dict() for k, v in self.races.items()},
            "classes": {k: v.to_dict() for k, v in self.classes.items()},
        }
        if self.history: result["history"] = self.history.to_dict()
        if self.rules: result["rules"] = self.rules.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldConfig':
        """Create a configuration from a dictionary."""
        config = cls()
        if "cultures" in data:
            for item_id, item_data in data["cultures"].items():
                if "id" not in item_data: item_data["id"] = item_id
                config.cultures[item_id] = Culture.from_dict(item_data)
        if "locations" in data:
            for item_id, item_data in data["locations"].items():
                if "id" not in item_data: item_data["id"] = item_id
                config.locations[item_id] = Location.from_dict(item_data)
        if "origins" in data:
            for item_id, item_data in data["origins"].items():
                if "id" not in item_data: item_data["id"] = item_id
                config.origins[item_id] = Origin.from_dict(item_data)
        if "quests" in data:
            for item_id, item_data in data["quests"].items():
                if "id" not in item_data: item_data["id"] = item_id
                config.quests[item_id] = Quest.from_dict(item_data)
        if "magic_systems" in data:
            for item_id, item_data in data["magic_systems"].items():
                if "id" not in item_data: item_data["id"] = item_id
                config.magic_systems[item_id] = MagicalSystem.from_dict(item_data)
        if "history" in data:
            config.history = WorldHistory.from_dict(data["history"])
        if "rules" in data:
            config.rules = WorldRules.from_dict(data["rules"])
        if "races" in data:
            for race_id, race_data in data["races"].items():
                if "id" not in race_data: race_data["id"] = race_id
                config.races[race_id] = Race.from_dict(race_data)
        if "classes" in data:
            for class_id, class_data in data["classes"].items():
                if "id" not in class_data: class_data["id"] = class_id
                config.classes[class_id] = CharacterClass.from_dict(class_data)

        return config
