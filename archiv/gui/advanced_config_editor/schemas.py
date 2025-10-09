# gui/advanced_config_editor/schemas.py
"""
Schema definitions and validation functions for the advanced configuration editor.
"""

# Schema definitions for validation
RACE_SCHEMA = {
    "required": ["name", "description"]
}

PATH_SCHEMA = {
    "required": ["name", "description", "backgrounds_file", "starting_advantages", "common_challenges"]
}

BACKGROUND_SCHEMA = {
    "required": [
        "name", "description", "origin", "skills", "starting_resources",
        "starting_locations", "motivation", "challenge", "narrative_elements"
    ]
}

def validate_entry(entry, schema):
    """
    Validate an entry against a schema.
    
    Args:
        entry (dict): The entry to validate
        schema (dict): The schema to validate against
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required = schema.get("required", [])
    missing = [field for field in required if field not in entry or entry[field] == ""]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, "Valid"