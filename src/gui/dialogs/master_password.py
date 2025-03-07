from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt

from .base_dialog import BaseDialog

class MasterPasswordDialog(BaseDialog):
    """Dialog for entering master password to unlock vault"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Unlock Vault")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Instruction label
        label = QLabel("Enter your master password to unlock the vault:")
        layout.addWidget(label)
        
        # Password field
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Master password")
        self.password.returnPressed.connect(self.accept)
        layout.addWidget(self.password)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Logout")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.unlock_btn = QPushButton("Unlock")
        self.unlock_btn.setDefault(True)
        self.unlock_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.unlock_btn)
        
        layout.addLayout(button_layout)
        
        # Add progress bar at bottom
        self.setup_progress_bar(layout)
        
        # Set initial focus
        self.password.setFocus()
    
    def get_password(self) -> str:
        """Get the entered password"""
        return self.password.text()