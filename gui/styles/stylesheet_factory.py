# gui/styles/stylesheet_factory.py
"""
Generates reusable Qt Style Sheet (QSS) strings from a theme palette.
This centralizes the construction of styles, ensuring consistency.
"""
from typing import Dict, Any
from PySide6.QtGui import QColor

def create_main_tab_widget_style(palette: Dict[str, Any]) -> str:
    """Creates the style for a primary QTabWidget."""
    colors = palette['colors']
    return f"""
        QTabWidget {{
            background-color: {colors['bg_medium']};
            border: 1px solid {colors['border_dark']};
            border-radius: 5px;
        }}
        QTabWidget::pane {{
            background-color: {colors['bg_medium']};
            border: 1px solid {colors['border_dark']};
            border-top: none;
            border-radius: 0 0 5px 5px;
        }}
        QTabBar::tab {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_light']}, stop:1 {colors['bg_medium']});
            color: {colors['text_primary']};
            border: 1px solid {colors['border_dark']};
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            padding: 8px 12px;
            margin-right: 2px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_medium']}, stop:1 {colors['bg_dark']});
            color: {colors['text_bright']};
            border-bottom: none;
        }}
        QTabBar::tab:hover:!selected {{
            background: {colors['state_hover']};
            color: {colors['accent_positive']};
        }}
    """

def create_secondary_tab_widget_style(palette: Dict[str, Any]) -> str:
    """Creates the style for a nested/secondary QTabWidget."""
    colors = palette['colors']
    return f"""
        QTabBar::tab {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_light']}, stop:1 {colors['bg_medium']});
            color: {colors['text_primary']};
            border: 1px solid {colors['border_dark']};
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
            padding: 5px 10px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background: {colors['bg_dark']};
            color: {colors['text_bright']};
            border-bottom: none;
        }}
        QTabBar::tab:hover:!selected {{
            background: {colors['state_hover']};
            color: {colors['accent_positive']};
        }}
    """

def create_list_widget_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QListWidget."""
    colors = palette['colors']
    return f"""
        QListWidget {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 3px;
            alternate-background-color: {colors['bg_medium']};
        }}
        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors['border_dark']};
        }}
        QListWidget::item:selected {{
            background-color: {colors['bg_light']};
            color: {colors['text_primary']};
        }}
        QListWidget::item:hover {{
            background-color: {colors['state_hover']};
            color: {colors['accent_positive']};
        }}
    """

def create_text_edit_style(palette: Dict[str, Any], read_only: bool = False) -> str:
    """Creates a standard style for QTextEdit."""
    colors = palette['colors']
    selection_bg = colors['state_selected'] if not read_only else 'transparent'
    return f"""
        QTextEdit {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 3px;
            padding: 8px;
            selection-background-color: {selection_bg};
        }}
    """

def create_styled_button_style(palette: Dict[str, Any]) -> str:
    """Creates the style for prominent, gradient-based buttons."""
    colors = palette['colors']
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_light']}, stop:1 {colors['bg_medium']});
            color: {colors['text_primary']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['state_hover']}, stop:1 {colors['bg_light']});
            border-color: {colors['accent_positive']};
            color: {colors['accent_positive']};
        }}
        QPushButton:pressed {{
            background: {colors['bg_dark']};
            border-color: {colors['accent_positive']};
        }}
        QPushButton:disabled {{
            background-color: {colors['bg_dark']};
            color: {colors['border_dark']};
            border-color: {colors['bg_medium']};
        }}
    """

def create_context_menu_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QMenu."""
    colors = palette['colors']
    return f"""
        QMenu {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_medium']}, stop:1 {colors['bg_dark']});
            color: {colors['text_bright']};
            border: 2px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 4px;
        }}
        QMenu::item {{
            background-color: transparent;
            padding: 6px 20px 6px 12px;
            border-radius: 2px;
        }}
        QMenu::item:selected {{
            background-color: {colors['bg_light']};
            color: {colors['text_primary']};
        }}
        QMenu::separator {{
            height: 2px;
            background: {colors['border_dark']};
            margin: 4px 6px;
        }}
    """

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

def create_combobox_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QComboBox."""
    colors = palette['colors']
    return f"""
        QComboBox {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 5px 8px;
        }}
        QComboBox:hover {{
            border-color: {colors['border_light']};
        }}
        QComboBox:on {{
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
        }}
        QComboBox::drop-down {{
            border: none;
            border-left: 1px solid {colors['border_dark']};
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {colors['text_primary']};
            margin-right: 5px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            selection-background-color: {colors['state_hover']};
            selection-color: {colors['text_primary']};
            border: 1px solid {colors['border_dark']};
            outline: none;
        }}
    """

def create_line_edit_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QLineEdit."""
    colors = palette['colors']
    return f"""
        QLineEdit {{
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 5px;
        }}
        QLineEdit:focus {{
            border-color: {colors['text_primary']};
        }}
        QLineEdit:disabled {{
            background-color: {colors['bg_medium']};
            color: {colors['text_disabled']};
        }}
    """

def create_scroll_area_style(palette: Dict[str, Any]) -> str:
    """Creates a transparent style for QScrollArea."""
    return """
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QScrollArea > QWidget > QWidget {
            background-color: transparent;
        }
    """

def create_checkbox_style(palette: Dict[str, Any]) -> str:
    """Creates a standard style for QCheckBox."""
    colors = palette['colors']
    return f"""
        QCheckBox {{
            color: {colors['text_primary']};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {colors['border_dark']};
            border-radius: 2px;
            background-color: {colors['bg_dark']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['accent_positive']};
            border-color: {colors['accent_positive']};
            /* Optional: Add an image or keep solid color for checked state */
            image: url(none); 
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors['accent_positive_light']};
        }}
    """