from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import traceback

from api.client import APIClient
from api.models import APIError
from utils.config import AppConfig
from utils.async_utils import async_callback
from .base_dialog import BaseDialog
from gui.widgets.strength_meter import PasswordStrengthMeter

class RegisterDialog(BaseDialog):
    """Dialog for registering a new user with an invite code"""
    
    register_successful = pyqtSignal()
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = APIClient(config.api_base_url)
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager - Register")
        self.setMinimumWidth(450)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Server information
        server_info = QLabel(f"Connecting to: {self.config.api_base_url}")
        server_info.setStyleSheet("color: gray;")
        layout.addWidget(server_info)
        
        # Registration form
        form_group = QGroupBox("Create New Account")
        form_layout = QFormLayout()
        
        # Email field
        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email")
        self.email.textChanged.connect(self.validate_form)
        form_layout.addRow("Email:", self.email)
        
        # Invite code field
        self.invite_code = QLineEdit()
        self.invite_code.setPlaceholderText("Enter your invite code")
        self.invite_code.textChanged.connect(self.validate_form)
        form_layout.addRow("Invite Code:", self.invite_code)
        
        # Password field
        self.password = QLineEdit()
        self.password.setPlaceholderText("Create a master password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.textChanged.connect(self.validate_form)
        self.password.textChanged.connect(self.update_strength_meter)
        form_layout.addRow("Password:", self.password)
        
        # Password strength meter
        self.strength_meter = PasswordStrengthMeter()
        form_layout.addRow("Strength:", self.strength_meter)
        
        # Password confirmation field
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Confirm your password")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.textChanged.connect(self.validate_form)
        form_layout.addRow("Confirm Password:", self.confirm_password)
        
        # Password requirements
        requirements_label = QLabel(
            "Password requirements:\n"
            "- At least 8 characters\n"
            "- At least one uppercase letter\n"
            "- At least one lowercase letter\n"
            "- At least one number\n"
            "- At least one special character"
        )
        requirements_label.setStyleSheet("color: gray; font-size: 10px;")
        form_layout.addRow("", requirements_label)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Important note about master password
        note_label = QLabel(
            "<b>Important:</b> This password will be your master password for encrypting "
            "and decrypting your vault. Make sure to remember it as it cannot be reset."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #ff6600;")
        layout.addWidget(note_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.setEnabled(False)
        self.register_btn.clicked.connect(self.handle_register)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.register_btn)
        
        layout.addLayout(button_layout)
        
        # Add progress bar at bottom
        self.setup_progress_bar(layout)
        
        # Set default focus
        self.email.setFocus()
    
    def update_strength_meter(self):
        """Update password strength meter"""
        password = self.password.text()
        self.strength_meter.update_strength(password)
    
    def validate_form(self):
        """Enable/disable register button based on form validity"""
        email = self.email.text().strip()
        invite_code = self.invite_code.text().strip()
        password = self.password.text().strip()
        confirm = self.confirm_password.text().strip()
        
        # Basic validation
        valid = (
            bool(email) and 
            bool(invite_code) and 
            bool(password) and 
            password == confirm and
            len(password) >= 8 and
            self.strength_meter.strength_level >= 2  # Require at least medium strength
        )
        
        self.register_btn.setEnabled(valid)
    
    @async_callback
    async def handle_register(self):
        """Handle register button click"""
        print("Registration attempt started")
        
        email = self.email.text().strip()
        invite_code = self.invite_code.text().strip()
        password = self.password.text()
        
        try:
            self.show_loading(True)
            print(f"Attempting registration for email: {email}")
            
            # Disable inputs during registration
            self.email.setEnabled(False)
            self.invite_code.setEnabled(False)
            self.password.setEnabled(False)
            self.confirm_password.setEnabled(False)
            self.register_btn.setEnabled(False)
            
            # Perform registration API call
            await self.api_client.register(email, password, invite_code)
            print("Registration successful")
            
            # Show success message
            self.show_success("Registration successful! You can now log in with your credentials.")
            
            # Emit success signal
            self.register_successful.emit()
            
            # Close dialog
            self.accept()
            
        except APIError as e:
            print(f"Registration failed with API error: {e.status_code} - {e.message}")
            if e.status_code == 400 and "Invalid invite code" in e.message:
                self.show_error(Exception("Invalid invite code. Please check and try again."))
            elif e.status_code == 400 and "already registered" in e.message:
                self.show_error(Exception("Email is already registered. Please use a different email."))
            else:
                self.show_error(e)
        except Exception as e:
            print(f"Registration failed with error: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.show_error(e)
        finally:
            print("Registration attempt completed")
            self.show_loading(False)
            # Re-enable inputs
            self.email.setEnabled(True)
            self.invite_code.setEnabled(True)
            self.password.setEnabled(True)
            self.confirm_password.setEnabled(True)
            self.validate_form()