# gui/styles/stylesheet_factory.py
"""
Generates reusable Qt Style Sheet (QSS) strings from a theme palette.
This centralizes the construction of styles, ensuring consistency.
"""
from typing import Dict, Any
from PySide6.QtGui import QColor

# def create_main_window_style(palette: Dict[str, Any], object_name: str, opacity: float) -> str:
#     """Creates the scoped stylesheet for the main window's command inputs."""
#     colors = palette['colors']
#     fonts = palette['fonts']
    
#     r, g, b = QColor(colors['bg_dark_transparent']).red(), QColor(colors['bg_dark_transparent']).green(), QColor(colors['bg_dark_transparent']).blue()

#     return f"""
#         QWidget#{object_name} {{
#             background-color: rgba({r}, {g}, {b}, {opacity});
#             border-radius: 10px;
#             padding: 5px;
#             border: 2px solid {colors['border_dark']};
#         }}
#         QWidget#{object_name} QLineEdit {{
#             background-color: {colors['input_background']};
#             color: {colors['input_text']};
#             border: 1px solid {colors['input_border']};
#             border-radius: 4px;
#             padding: 8px;
#             font-family: '{fonts['family_user_input']}';
#             font-size: {fonts['size_user_input']}pt;
#             margin-left: 5px;
#             margin-right: 5px;
#         }}
#     """

def create_image_button_style(palette: Dict[str, Any]) -> str:
    """Creates the style for buttons that use background images."""
    paths = palette['paths']
    colors = palette['colors']
    fonts = palette['fonts']
    return f"""
        QPushButton {{
            background-image: url('{paths['button_normal']}');
            background-position: center;
            background-repeat: no-repeat;
            background-color: transparent;
            color: {colors['text_ivory']};
            border: none;
            padding: 8px;
            text-align: center;
            min-width: 100px;
            max-width: 110px;
            min-height: 35px;
            border-radius: 5px;
            margin-left: 5px;
            margin-right: 10px;
            font-family: {fonts['family_fantasy']};
        }}
        QPushButton:hover {{
            background-image: url('{paths['button_hover']}');
        }}
        QPushButton:pressed {{
            background-image: url('{paths['button_pressed']}');
            color: {colors['accent_negative']};
            font-weight: bold;
        }}
    """

def create_round_image_button_style(palette: Dict[str, Any], size: int) -> str:
    """Creates a style for a transparent, round button meant to hold an icon."""
    radius = size // 2
    
    return f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            width: {size}px;
            height: {size}px;
            border-radius: {radius}px;
            padding: 0px; /* Important for icon positioning */
        }}
        QPushButton:hover {{
            /* Optional: Add a subtle glow effect here if desired */
        }}
        QPushButton:pressed {{
            /* Move the icon slightly down and to the right to simulate a press */
            padding-top: 2px;
            padding-left: 1px;
        }}
    """

def create_groupbox_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QGroupBox."""
    colors = palette['colors']
    return f"""
        QGroupBox {{
            background-color: {colors['bg_light']};
            border: 1px solid {colors['border_dark']};
            border-radius: 5px;
            margin-top: 15px;
            font-weight: bold;
            color: {colors['text_primary']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px 0 10px;
        }}
    """

def create_dialog_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QDialog and its common child widgets."""
    colors = palette['colors']
    return f"""
        QDialog {{
            background-color: {colors['bg_medium']};
            color: {colors['text_bright']};
        }}
        QLabel {{
            color: {colors['text_primary']};
        }}
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 5px;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {colors['text_primary']};
        }}
        QPushButton {{
            background-color: {colors['bg_light']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {colors['state_hover']};
            border-color: {colors['border_light']};
        }}
        QPushButton:pressed {{
            background-color: {colors['bg_dark']};
        }}
        QPushButton:disabled {{
            background-color: {colors['bg_dark']};
            color: {colors['text_disabled']};
        }}
    """

def create_combat_display_style(palette: Dict[str, Any]) -> str:
    """Creates the complex stylesheet for the CombatDisplay widget."""
    colors = palette['colors']
    fonts = palette['fonts']
    paths = palette['paths']
    dims = palette['dimensions']

    return f"""
        QFrame#combatContentFrame {{
            border-image: url("{paths['combat_display_main']}") 0 0 0 0 stretch stretch;
            padding: 10px;
        }}
        QLabel#panelHeaderLabel {{
            background-color: transparent;
            color: {colors['combat_panel_title']};
            font-family: "{fonts['family_header']}";
            font-size: {fonts['size_header']}pt;
            font-weight: bold;
            padding-top: {dims['header_vertical_offset']}px;
            margin-bottom: 5px;
        }}
        QFrame#alliesBGFrame, QFrame#centerBGFrame, QFrame#enemiesBGFrame, QFrame#logBGFrame {{
            border-image: url('{paths['combat_display_panel']}') 0 0 0 0 stretch stretch;
            border: 2px groove {colors['border_dark']};
            border-radius: 15px;
        }}
        QTextEdit#combatLogText {{
            background-color: transparent;
            border: none;
            color: {colors['log_default_text']};
            font-family: "{fonts['family_main']}";
            font-size: {fonts['size_combat_log']}pt;
            padding: 15px;
        }}
        QLabel#statusLabel, QLabel#roundLabel {{
            background-color: transparent;
            font-family: "{fonts['family_main']}";
            font-weight: bold;
        }}
        QLabel#statusLabel {{
            color: {colors['combat_status_text']};
            font-size: {fonts['size_status'] + 2}pt;
        }}
        QLabel#roundLabel {{
            color: {colors['combat_round_text']};
            font-size: {fonts['size_status']}pt;
        }}
    """