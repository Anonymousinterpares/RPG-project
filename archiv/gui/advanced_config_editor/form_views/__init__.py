# gui/advanced_config_editor/form_views/__init__.py
"""
Form views for the advanced configuration editor.
"""
from .races_form import create_races_form_tab
from .paths_form import create_paths_form_tab
from .world_settings_form import create_world_settings_form_tab
from .scenarios_form import create_scenarios_form_tab
from .items_form import create_items_form_tab

__all__ = [
    'create_races_form_tab',
    'create_paths_form_tab',
    'create_world_settings_form_tab',
    'create_scenarios_form_tab',
    'create_items_form_tab'
]