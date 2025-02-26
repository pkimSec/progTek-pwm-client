from PyQt6.QtWidgets import QProgressBar, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
import re

class PasswordStrengthMeter(QWidget):
    """Widget for measuring and displaying password strength"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.strength_level = 0  # 0-4 strength scale
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar for visual representation
        self.progress = QProgressBar()
        self.progress.setRange(0, 4)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress, 3)
        
        # Label for text description
        self.label = QLabel("Very Weak")
        layout.addWidget(self.label, 1)
        
        # Apply initial styling
        self.update_styling(0)
    
    def update_strength(self, password: str):
        """
        Update the strength meter based on the password
        Implements a basic strength algorithm
        """
        if not password:
            strength = 0
            description = "Very Weak"
        else:
            # Start with length-based score
            strength = 0
            
            # Check length
            if len(password) >= 8:
                strength += 1
            if len(password) >= 12:
                strength += 1
                
            # Check complexity with regex
            has_lowercase = bool(re.search(r'[a-z]', password))
            has_uppercase = bool(re.search(r'[A-Z]', password))
            has_digit = bool(re.search(r'\d', password))
            has_special = bool(re.search(r'[^A-Za-z0-9]', password))
            
            # Add points for character variety
            if has_lowercase and has_uppercase:
                strength += 1
            if has_digit:
                strength += 0.5
            if has_special:
                strength += 0.5
                
            # Ensure strength is an integer between 0-4
            strength = min(4, int(strength))
            
            # Set description based on strength level
            if strength <= 1:
                description = "Very Weak"
            elif strength == 2:
                description = "Weak"
            elif strength == 3:
                description = "Moderate"
            else:
                description = "Strong"
        
        # Update the progress bar and label
        self.strength_level = strength
        self.progress.setValue(strength)
        self.label.setText(description)
        self.update_styling(strength)
    
    def update_styling(self, strength: int):
        """Update the styling based on strength level"""
        # Define colors for different strength levels
        colors = [
            "#FF3B30",  # Red - Very Weak
            "#FF9500",  # Orange - Weak
            "#FFCC00",  # Yellow - Moderate
            "#34C759"   # Green - Strong
        ]
        
        # Apply color to progress bar
        if strength == 0:
            color = colors[0]
        else:
            color = colors[min(strength - 1, 3)]
            
        # Create stylesheet
        style = f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 2px;
                background-color: #f5f5f5;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """
        
        self.progress.setStyleSheet(style)
        
        # Apply text color to label
        self.label.setStyleSheet(f"color: {color};")