from PyQt6.QtWidgets import QProgressBar, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSlot

try:
    import zxcvbn
    HAS_ZXCVBN = True
except ImportError:
    HAS_ZXCVBN = False
    print("zxcvbn not available, using basic password strength estimation")

class PasswordStrengthMeter(QWidget):
    """Widget to display password strength"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar for strength visualization
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress, 3)
        
        # Label for strength text
        self.label = QLabel("Weak")
        self.label.setMinimumWidth(80)
        layout.addWidget(self.label, 1)
        
        # Set initial state
        self.update_strength("")
    
    @pyqtSlot(str)
    def update_strength(self, password: str):
        """Update meter based on password strength"""
        if not password:
            strength = 0
            text = "None"
            color = "gray"
        elif HAS_ZXCVBN:
            # Use zxcvbn for better password strength estimation
            result = zxcvbn.zxcvbn(password)
            score = result['score']  # 0-4 score
            
            # Convert to percentage and text
            strength = (score / 4) * 100
            
            if score == 0:
                text = "Very Weak"
                color = "red"
            elif score == 1:
                text = "Weak"
                color = "orangered"
            elif score == 2:
                text = "Moderate"
                color = "orange"
            elif score == 3:
                text = "Strong"
                color = "yellowgreen"
            else:  # score == 4
                text = "Very Strong"
                color = "green"
                
        else:
            # Basic strength calculation without zxcvbn
            if len(password) < 8:
                strength = 25
                text = "Weak"
                color = "red"
            elif len(password) < 12:
                # Check for complexity
                has_upper = any(c.isupper() for c in password)
                has_lower = any(c.islower() for c in password)
                has_digit = any(c.isdigit() for c in password)
                has_special = any(not c.isalnum() for c in password)
                
                complexity = sum([has_upper, has_lower, has_digit, has_special])
                
                if complexity < 2:
                    strength = 25
                    text = "Weak"
                    color = "red"
                elif complexity < 3:
                    strength = 50
                    text = "Moderate"
                    color = "orange"
                else:
                    strength = 75
                    text = "Strong"
                    color = "yellowgreen"
            else:
                # Check for complexity in longer passwords
                has_upper = any(c.isupper() for c in password)
                has_lower = any(c.islower() for c in password)
                has_digit = any(c.isdigit() for c in password)
                has_special = any(not c.isalnum() for c in password)
                
                complexity = sum([has_upper, has_lower, has_digit, has_special])
                
                if complexity < 3:
                    strength = 75
                    text = "Strong"
                    color = "yellowgreen"
                else:
                    strength = 100
                    text = "Very Strong"
                    color = "green"
        
        # Update UI
        self.progress.setValue(int(strength))
        self.label.setText(text)
        
        # Set color based on strength
        stylesheet = f"QProgressBar::chunk {{ background-color: {color}; }}"
        self.progress.setStyleSheet(stylesheet)