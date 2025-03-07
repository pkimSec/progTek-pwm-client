from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
import re
import traceback

from api.client import APIClient
from api.models import APIError
from utils.config import AppConfig
from utils.async_utils import async_callback
from .base_dialog import BaseDialog
from gui.widgets.strength_meter import PasswordStrengthMeter

class RegisterDialog(BaseDialog):
    """Dialog for registering a new user with invite code"""
    
    registration_successful = pyqtSignal(str)  # Signal emitted with email on success
    
    def __init__(self, api_client: APIClient, config: AppConfig, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.config = config
        self.email = ""  # Store email for access after dialog closes
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager - Register")
        self.setMinimumWidth(450)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Registration form
        form_layout = QFormLayout()
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.textChanged.connect(self.validate_form)
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a strong password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.validate_form)
        form_layout.addRow("Password:", self.password_input)
        
        # Password strength meter
        self.strength_meter = PasswordStrengthMeter()
        self.password_input.textChanged.connect(self.strength_meter.update_strength)
        form_layout.addRow("Password Strength:", self.strength_meter)
        
        # Confirm password
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.textChanged.connect(self.validate_form)
        form_layout.addRow("Confirm Password:", self.confirm_input)
        
        # Invite code
        self.invite_input = QLineEdit()
        self.invite_input.setPlaceholderText("Enter your invite code")
        self.invite_input.textChanged.connect(self.validate_form)
        form_layout.addRow("Invite Code:", self.invite_input)
        
        # Add form to layout
        layout.addLayout(form_layout)
        
        # Help text
        help_label = QLabel("You need an invite code to register. Please contact your administrator.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(help_label)
        
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
        
        # Add progress bar
        self.setup_progress_bar(layout)
        
        # Set default focus
        self.email_input.setFocus()
    
    def validate_form(self):
        """Validate form and enable/disable register button"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        invite_code = self.invite_input.text().strip()
        
        # Basic email format validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        is_email_valid = bool(email_pattern.match(email))
        
        # Password validation
        is_password_valid = len(password) >= 8
        
        # Check if passwords match
        passwords_match = password == confirm
        
        # Invite code check
        has_invite = bool(invite_code)
        
        # Enable button if all valid
        self.register_btn.setEnabled(
            is_email_valid and is_password_valid and passwords_match and has_invite
        )
        
        # Show validation feedback
        if email and not is_email_valid:
            self.email_input.setStyleSheet("border: 1px solid red")
        else:
            self.email_input.setStyleSheet("")
        
        if password and not is_password_valid:
            self.password_input.setStyleSheet("border: 1px solid red")
        else:
            self.password_input.setStyleSheet("")
        
        if confirm and not passwords_match:
            self.confirm_input.setStyleSheet("border: 1px solid red")
        else:
            self.confirm_input.setStyleSheet("")
    
    @async_callback
    async def handle_register(self):
        """Handle registration button click"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        invite_code = self.invite_input.text().strip()
        
        try:
            self.show_loading(True)
            self.register_btn.setEnabled(False)
            
            # Call API to register
            await self.api_client.register(email, password, invite_code)
            
            # Store email for use after dialog closes
            self.email = email
            
            # Show success message
            self.show_success("Registration successful! You can now log in.")
            
            # Emit signal with email
            self.registration_successful.emit(email)
            
            # Close dialog
            self.accept()
            
        except APIError as e:
            if e.status_code == 400:
                if "Invalid invite code" in e.message:
                    self.show_error(Exception("Invalid invite code. Please check and try again."))
                elif "Email already registered" in e.message:
                    self.show_error(Exception("Email already registered. Please use a different email."))
                else:
                    self.show_error(e)
            else:
                self.show_error(e)
        except Exception as e:
            print(f"Registration error: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.show_error(e)
        finally:
            self.show_loading(False)
            self.register_btn.setEnabled(True)