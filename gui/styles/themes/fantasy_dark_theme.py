# gui/styles/themes/fantasy_dark_theme.py
"""
Defines the palette for the 'Fantasy Dark' theme.
This is the single source of truth for all style constants for this theme.
"""
from PySide6.QtGui import QColor

THEME = {
    'name': 'Fantasy Dark',
    'colors': {
        # == Core Palette ==
        'bg_dark': '#1a1410',
        'bg_medium': '#2d2520',
        'bg_light': '#3a302a',
        'bg_dark_transparent': 'rgba(26, 20, 16, 0.85)',
        'bg_medium_transparent': 'rgba(45, 37, 32, 0.5)',

        'border_dark': '#4a3a30',
        'border_light': '#5a4a40',

        'text_primary': '#c9a875',    # Golden/amber
        'text_secondary': '#8b7a65',   # Muted parchment/gray
        'text_bright': '#e8d4b8',     # Brighter parchment for values
        'text_ivory': '#fff5cc',      # For menu buttons
        'text_disabled': '#5a4a40',

        # == States & Accents ==
        'state_hover': '#4a3a30',
        'state_pressed': '#1a1410',
        'state_selected': '#c9a875',
        'state_active_border': '#00aaff', # From CombatEntityWidget
        
        'accent_positive': '#5a9068',
        'accent_positive_light': '#6ac46a',
        'accent_negative': '#D94A38',
        'accent_negative_light': '#ff6b6b',

        # == Resources ==
        'res_mana': '#1178BB',
        'res_mana_dark': '#0b5a8e',
        'res_health': '#D94A38',
        'res_health_dark': '#a03628',
        'res_stamina': '#5a9068',
        'res_stamina_dark': '#3a6a48',
        'res_exp': '#c9a875',
        'res_exp_dark': '#8b7a65',
        'res_ap_active_light': '#4a7c59',
        'res_ap_active_dark': '#2d5a3a',
        'res_ap_border_active': '#5a9068',
        'res_ap_glow_active': 'rgba(90, 144, 104, 30)',


        # == Component Specific ==
        'input_background': 'rgba(255, 255, 255, 0.7)',
        'input_border': '#c4b59d',
        'input_text': '#0d47a1',
        
        'output_text_main': '#3b2f1e',
        'output_text_system': '#a03628',
        'output_text_player': '#0b5a8e',

        # == Combat Log Specific Colors ==
        'log_default_text': '#3D2B1F',
        'log_damage': '#C80000',
        'log_heal': '#009600',
        'log_crit': '#FF0000',
        'log_miss': '#6c5b4b',
        'log_roll': '#C87800',
        'log_turn': '#0064C8',
        'log_round': '#0064FF',
        'log_dev': '#646464',
        'log_event': '#000000',
        'log_system': '#00008B',
        'log_narrative': '#3D2B1F',

        'combat_panel_title': '#5B3A29',
        'combat_status_text': '#FFFFFF',
        'combat_round_text': '#E0E0E0',

        'info_icon_bg': '#1178BB',
        'info_icon_bg_dark': '#0b5a8e',
    },
    'fonts': {
        'family_main': 'Garamond',
        'family_user_input': 'Garamond',
        'family_header': 'Garamond',
        'family_fantasy': "'Times New Roman', serif",

        'size_main_output': 14,
        'size_user_input': 14,
        'size_header': 20,
        'size_status': 12,
        'size_combat_log': 14,
        'size_combat_entity': 12,
        'size_ap_display': 13,
        'size_grimoire_spell': 11,
    },
    'paths': {
        'background_main_output': 'images/gui/background_game_output.png',
        'menu_panel_background': 'images/gui/menu_panel_metal.PNG',
        'button_normal': 'images/gui/button_normal.png',
        'button_hover': 'images/gui/button_hover.png',
        'button_pressed': 'images/gui/button_pressed.png',
        'send_button_icon': 'images/gui/send_button_red_stamp.png',
        'combat_display_main': 'images/gui/combat_display/background_game_output.png',
        'combat_display_panel': 'images/gui/combat_display/background_game_output.png',
    },
    'dimensions': {
        'border_radius': '5px',
        'header_vertical_offset': 5,
    },
    'progress_bars': {
        'bg': '#a08c6e',
        'text': '#FFFFFF',
        'hp_normal': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:1 #aa0000)',
        'hp_low': '#cc0000',
        'hp_critical': '#990000',
        'hp_bleak_normal': '#AA0000A0',
        'hp_bleak_low': '#880000A0',
        'hp_bleak_critical': '#600000A0',
        'stamina': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66CC33, stop:1 #44AA22)',
        'stamina_bleak': '#44AA22A0',
        'mana': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3366CC, stop:1 #2244AA)',
        'mana_bleak': '#2244AAA0',
    }
}