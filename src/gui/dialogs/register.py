from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
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
        print(f"Initializing RegisterDialog with API client: {api_client}")
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
    
    def handle_register(self):
        """Entry point for registration - handles button click"""
        print("=== Register button clicked ===")
        # Check if the API client is available
        if not self.api_client:
            self.show_error(Exception("API client not available. Please try again."))
            return
            
        print(f"API client available: {self.api_client}")
        print(f"API base URL: {self.api_client.endpoints.base_url}")
        
        # Call the async version with proper error handling
        try:
            print("Starting registration process...")
            self._handle_register_async()
        except Exception as e:
            print(f"Error initiating registration: {str(e)}")
            traceback.print_exc()
            self.show_error(e)
    
    @async_callback
    async def _handle_register_async(self):
        """Async implementation of registration handling"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        invite_code = self.invite_input.text().strip()
        
        print(f"Registration data - Email: {email}, Invite code: {invite_code}")
        
        try:
            # Disable UI during registration
            self.email_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.confirm_input.setEnabled(False)
            self.invite_input.setEnabled(False)
            self.register_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            
            self.show_loading(True)
            
            print("Ensuring API session exists...")
            await self.api_client.ensure_session()
            
            print("Creating registration request...")
            # Create request object for better debugging
            request_data = {
                "email": email,
                "password": password,
                "invite_code": invite_code
            }
            
            print(f"Sending registration request to: {self.api_client.endpoints.register}")
            print(f"Request data: {request_data}")
            
            # Call API to register
            response = await self.api_client._request(
                'POST', 
                self.api_client.endpoints.register, 
                request_data, 
                include_auth=False,
                retry_auth=False
            )
            
            print(f"Registration response received: {response}")
            
            # Store email for use after dialog closes
            self.email = email
            
            # Show success message
            self.show_success("Registration successful! You can now log in.")
            
            # Emit signal with email
            print(f"Emitting registration_successful signal with email: {email}")
            self.registration_successful.emit(email)
            
            # Close dialog with success after a short delay
            QTimer.singleShot(500, self.accept)
            
        except APIError as e:
            print(f"API Error during registration: {e.status_code} - {e.message}")
            
            if e.status_code == 400:
                if "Invalid invite code" in e.message:
                    self.show_error(Exception("Invalid invite code. Please check and try again."))
                elif "Email already registered" in e.message:
                    self.show_error(Exception("Email already registered. Please use a different email."))
                else:
                    self.show_error(Exception(f"Registration error: {e.message}"))
            else:
                self.show_error(Exception(f"Server error ({e.status_code}): {e.message}"))
                
        except Exception as e:
            print(f"Registration error: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.show_error(e)
        finally:
            print("Registration process completed")
            self.show_loading(False)
            
            # Re-enable UI
            self.email_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.confirm_input.setEnabled(True)
            self.invite_input.setEnabled(True)
            self.register_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)

    def accept(self):
        """Override accept method to ensure proper closure"""
        print("RegisterDialog: accept called")
        # Ensure we've emitted the success signal if we have an email
        if self.email and not self.result():
            print(f"Emitting registration_successful signal before closing: {self.email}")
            self.registration_successful.emit(self.email)
    
        # Call the parent class accept
        super().accept()

    def closeEvent(self, event):
        """Override close event to ensure proper cleanup"""
        print("RegisterDialog: closeEvent called")
        # Ensure we've emitted the success signal if we have an email
        if self.email and not self.result():
            print(f"Emitting registration_successful signal during close: {self.email}")
            self.registration_successful.emit(self.email)
    
        # Call the parent class closeEvent
        super().closeEvent(event)