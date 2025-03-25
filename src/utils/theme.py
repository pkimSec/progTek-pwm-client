"""
Theme management utilities for the application.
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QFile, QTextStream

def get_theme_path(theme_name: str) -> str:
    """
    Get the file path for the specified theme.
    
    Args:
        theme_name: Name of the theme (e.g., 'dark', 'light')
        
    Returns:
        Path to the theme file
    """
    # Get the base directory of the application
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Construct path to the theme file
    theme_file = os.path.join(base_dir, 'assets', 'styles', f'{theme_name}.qss')
    
    # Verify file exists
    if not os.path.exists(theme_file):
        print(f"Warning: Theme file not found: {theme_file}")
        return ""
        
    return theme_file

def load_theme(theme_name: str) -> str:
    """
    Load the QSS style content from a theme file.
    
    Args:
        theme_name: Name of the theme (e.g., 'dark', 'light')
        
    Returns:
        QSS style content as string
    """
    theme_file = get_theme_path(theme_name)
    if not theme_file:
        return ""
        
    try:
        with open(theme_file, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading theme file {theme_file}: {e}")
        return ""

def apply_theme(theme_name: str) -> bool:
    """
    Apply a theme to the application.
    
    Args:
        theme_name: Name of the theme (e.g., 'dark', 'light')
        
    Returns:
        True if theme was applied successfully, False otherwise
    """
    print(f"Applying theme: {theme_name}")
    
    # Normalize theme name
    theme_name = theme_name.lower()
    
    # Load theme content
    style_content = load_theme(theme_name)
    if not style_content:
        print(f"Failed to load theme: {theme_name}")
        return False
    
    # Apply to application
    app = QApplication.instance()
    if app:
        app.setStyleSheet(style_content)
        print(f"Applied theme: {theme_name}")
        return True
    else:
        print("No QApplication instance found")
        return False

def toggle_theme(current_theme: str) -> str:
    """
    Toggle between dark and light themes.
    
    Args:
        current_theme: Current theme name
        
    Returns:
        New theme name
    """
    new_theme = "light" if current_theme.lower() == "dark" else "dark"
    apply_theme(new_theme)
    return new_theme

def create_theme_assets() -> None:
    """
    Create necessary icon assets for theming.
    This should be called during initialization to ensure all required assets exist.
    Creates placeholder asset files if they don't exist.
    """
    # Get the base directory of the application
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Define asset directories
    assets_dir = os.path.join(base_dir, 'assets')
    icons_dir = os.path.join(assets_dir, 'icons')
    
    # Create directories if they don't exist
    os.makedirs(icons_dir, exist_ok=True)
    
    # Simple placeholder SVG for checkbox and radio buttons
    # These will be minimal to ensure themes work even without graphic assets
    
    # Check icon - light version (for dark theme)
    check_light_path = os.path.join(icons_dir, 'check-light.png')
    if not os.path.exists(check_light_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
            check_pixmap = QPixmap(16, 16)
            check_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(check_pixmap)
            pen = QPen(QColor(255, 255, 255))  # White
            pen.setWidth(2)
            painter.setPen(pen)
            # Draw checkmark
            painter.drawLine(4, 8, 7, 11)
            painter.drawLine(7, 11, 12, 5)
            painter.end()
            check_pixmap.save(check_light_path)
            print(f"Created placeholder icon: {check_light_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")
    
    # Check icon - dark version (for light theme)
    check_dark_path = os.path.join(icons_dir, 'check-dark.png')
    if not os.path.exists(check_dark_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
            check_pixmap = QPixmap(16, 16)
            check_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(check_pixmap)
            pen = QPen(QColor(30, 30, 46))  # Dark (Mocha)
            pen.setWidth(2)
            painter.setPen(pen)
            # Draw checkmark
            painter.drawLine(4, 8, 7, 11)
            painter.drawLine(7, 11, 12, 5)
            painter.end()
            check_pixmap.save(check_dark_path)
            print(f"Created placeholder icon: {check_dark_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")
    
    # Radio checked icon - light version (for dark theme)
    radio_light_path = os.path.join(icons_dir, 'radio-checked-light.png')
    if not os.path.exists(radio_light_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QBrush, QPen, QColor
            radio_pixmap = QPixmap(16, 16)
            radio_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(radio_pixmap)
            painter.setBrush(QBrush(QColor(255, 255, 255)))  # White
            painter.setPen(Qt.PenStyle.NoPen)
            # Draw circle
            painter.drawEllipse(5, 5, 6, 6)
            painter.end()
            radio_pixmap.save(radio_light_path)
            print(f"Created placeholder icon: {radio_light_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")
    
    # Radio checked icon - dark version (for light theme)
    radio_dark_path = os.path.join(icons_dir, 'radio-checked-dark.png')
    if not os.path.exists(radio_dark_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QBrush, QPen, QColor
            radio_pixmap = QPixmap(16, 16)
            radio_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(radio_pixmap)
            painter.setBrush(QBrush(QColor(30, 30, 46)))  # Dark (Mocha)
            painter.setPen(Qt.PenStyle.NoPen)
            # Draw circle
            painter.drawEllipse(5, 5, 6, 6)
            painter.end()
            radio_pixmap.save(radio_dark_path)
            print(f"Created placeholder icon: {radio_dark_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")
    
    # Search icon - light version (for dark theme)
    search_light_path = os.path.join(icons_dir, 'search-light.png')
    if not os.path.exists(search_light_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
            from PyQt6.QtCore import Qt
            search_pixmap = QPixmap(16, 16)
            search_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(search_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(255, 255, 255))
            pen.setWidth(1)
            painter.setPen(pen)
            # Draw search icon (circle + line)
            painter.drawEllipse(3, 3, 7, 7)
            painter.drawLine(10, 10, 13, 13)
            painter.end()
            search_pixmap.save(search_light_path)
            print(f"Created placeholder icon: {search_light_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")
    
    # Search icon - dark version (for light theme)
    search_dark_path = os.path.join(icons_dir, 'search-dark.png')
    if not os.path.exists(search_dark_path):
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
            from PyQt6.QtCore import Qt
            search_pixmap = QPixmap(16, 16)
            search_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
            painter = QPainter(search_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(76, 79, 105))  # Text color from Latte
            pen.setWidth(1)
            painter.setPen(pen)
            # Draw search icon (circle + line)
            painter.drawEllipse(3, 3, 7, 7)
            painter.drawLine(10, 10, 13, 13)
            painter.end()
            search_pixmap.save(search_dark_path)
            print(f"Created placeholder icon: {search_dark_path}")
        except Exception as e:
            print(f"Failed to create placeholder icon: {e}")