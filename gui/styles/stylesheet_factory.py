# gui/styles/stylesheet_factory.py
"""
Generates reusable Qt Style Sheet (QSS) strings from a theme palette.
This centralizes the construction of styles, ensuring consistency.
"""
from typing import Dict, Any
from PySide6.QtGui import QColor

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
            margin-left: 9px;
            margin-right: 5px;
            font-family: {fonts['family_main']};
            font-size: {fonts['size_menu_button']}pt;
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
    """Creates a style for a round button with a normal and pressed icon state."""
    paths = palette.get('paths', {})
    icon_normal_path = paths.get('send_button_icon', '').replace("\\", "/")
    icon_clicked_path = paths.get('send_button_icon_clicked', '').replace("\\", "/")
    radius = size // 2
    
    return f"""
        QPushButton {{
            image: url('{icon_normal_path}');
            background-color: transparent;
            border: none;
            width: {size}px;
            height: {size}px;
            border-radius: {radius}px;
            padding: 0px;
        }}
        QPushButton:hover {{
            /* Optional: Add a subtle glow or overlay */
        }}
        QPushButton:pressed {{
            image: url('{icon_clicked_path}');
            /* Optional: Add a small padding shift to enhance the "press" feel */
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
        /* Background image frames (no border) */
        QFrame#alliesBGFrame, QFrame#centerBGFrame, QFrame#enemiesBGFrame, QFrame#logBGFrame {{
            border-image: url('{paths['combat_display_panel']}') 0 0 0 0 stretch stretch;
            border: none; /* The border is now on the inner frame */
            border-radius: 15px;
        }}
        /* Inner frames that ONLY draw the border */
        QFrame#panelBorderFrame {{
            background-color: transparent;
            border: 2px solid {colors['border_dark']};
            border-radius: 15px;
        }}
        QTextEdit#combatLogText {{
            background-color: transparent;
            border: none;
            color: {colors['log_default_text']};
            font-family: "{fonts['family_main']}";
            font-size: {fonts['size_combat_log']}pt;
            padding: 15px;
            padding-bottom: 70px; /* Creates space for the command input overlay */
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

def create_combat_display_style(palette: Dict[str, Any]) -> str:
    """Creates the complex stylesheet for the CombatDisplay widget."""
    colors = palette['colors']
    fonts = palette['fonts']
    paths = palette['paths']
    dims = palette['dimensions']

    return f"""
        /* The main outer frame holding the stone background image */
        QFrame#combatBackgroundFrame {{
            border-image: url("{paths['combat_display_main']}") 0 0 0 0 stretch stretch;
            border-radius: 15px;
        }}
        /* The new inner frame that draws the border on top of the background */
        QFrame#combatBorderFrame {{
            background-color: transparent;
            border: 2px solid {colors['border_dark']};
            border-radius: 13px; /* Slightly smaller for inset effect */
            margin: 2px;
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
        /* Background image frames for inner panels (no border) */
        QFrame#alliesBGFrame, QFrame#centerBGFrame, QFrame#enemiesBGFrame, QFrame#logBGFrame {{
            border-image: url('{paths['combat_display_panel']}') 0 0 0 0 stretch stretch;
            border: none;
            border-radius: 15px;
        }}
        /* Inner frames for panels that ONLY draw the border */
        QFrame#panelBorderFrame {{
            background-color: transparent;
            border: 2px solid {colors['border_dark']};
            border-image: none; /* Explicitly disable border-image inheritance */
            border-radius: 13px; /* Slightly smaller than parent (15px) for proper nesting */
            margin: 2px; /* Creates space between background and border */
        }}
        QTextEdit#combatLogText {{
            background-color: transparent;
            border: none;
            color: {colors['log_default_text']};
            font-family: "{fonts['family_main']}";
            font-size: {fonts['size_combat_log']}pt;
            padding: 15px;
            padding-bottom: 70px; /* Creates space for the command input overlay */
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

def create_overlay_command_input_style(palette: Dict[str, Any]) -> str:
    """Creates the style for the transparent, bordered QLineEdit used as an overlay."""
    colors = palette['colors']
    fonts = palette['fonts']
    opacities = palette.get('opacities', {})

    # Get the background color and opacity from the theme
    bg_color_hex = colors.get('input_overlay_bg_color', '#5a4a40')
    bg_opacity = opacities.get('input_overlay_bg_opacity', 0.3)
    
    # Convert hex to RGB to use with rgba()
    q_color = QColor(bg_color_hex)
    r, g, b = q_color.red(), q_color.green(), q_color.blue()

    border_color = colors.get('input_overlay_border', '#4a3a30')

    return f"""
        QLineEdit {{
            background-color: rgba({r}, {g}, {b}, {bg_opacity});
            color: {colors['input_text']};
            border: 2px solid {border_color};
            border-radius: 4px;
            padding: 8px;
            font-family: '{fonts['family_user_input']}';
            font-size: {fonts['size_user_input']}pt;
        }}
        QLineEdit:focus {{
            border-color: {border_color}; /* Keep the border color the same on focus */
        }}
    """