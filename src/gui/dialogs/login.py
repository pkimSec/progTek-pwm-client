from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
import traceback
import sys

from api.client import APIClient
from api.models import APIError, LoginResponse
from utils.config import AppConfig
from utils.async_utils import async_callback
from .base_dialog import BaseDialog

class LoginDialog(BaseDialog):
    """Login dialog with server connection test"""
    
    login_successful = pyqtSignal(LoginResponse)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = APIClient(config.api_base_url)
        self.is_connected = False  # Track connection state
        print(f"Initialized LoginDialog with URL: {config.api_base_url}")
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager - Login")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Server status label
        self.status_label = QLabel("Server status: Not connected")
        layout.addWidget(self.status_label)
        
        # Server settings
        server_group = QFormLayout()
        self.server_url = QLineEdit(self.config.api_base_url)
        self.server_url.setPlaceholderText("http://localhost:5000")
        self.server_url.textChanged.connect(self.on_server_url_changed)
        server_group.addRow("Server URL:", self.server_url)
        
        # Test connection button
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.on_test_connection_clicked)
        test_layout.addStretch()
        test_layout.addWidget(self.test_btn)
        
        # Login form
        form_layout = QFormLayout()
        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email")
        self.email.textChanged.connect(self.validate_form)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.textChanged.connect(self.validate_form)
        
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Password:", self.password)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setEnabled(False)
        self.login_btn.clicked.connect(self.handle_login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.setEnabled(False)
        
        button_layout.addWidget(self.register_btn)
        button_layout.addWidget(self.login_btn)
        
        # Add all layouts
        layout.addLayout(server_group)
        layout.addLayout(test_layout)
        layout.addSpacing(15)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        
        # Add progress bar at bottom
        self.setup_progress_bar(layout)
        
        # Set default focus
        self.server_url.setFocus()

    def on_server_url_changed(self):
        """Handle server URL changes"""
        print("Server URL changed")
        self.is_connected = False
        self.login_btn.setEnabled(False)
        self.register_btn.setEnabled(False)
        self.status_label.setText("Server status: Not connected")
        self.status_label.setStyleSheet("color: gray")

    def on_test_connection_clicked(self):
        """Handle test connection button click"""
        print("Test connection button clicked")
        self.test_connection()
    
    def validate_form(self):
        """Enable/disable login button based on form validity"""
        email = self.email.text().strip()
        password = self.password.text().strip()
        has_credentials = bool(email and password)

        self.login_btn.setEnabled(self.is_connected and has_credentials)
    
    @async_callback
    async def test_connection(self):
        """Test connection to server"""
        print("Starting connection test")
        server_url = self.server_url.text().strip()
        if not server_url:
            print("No server URL provided")
            self.show_error(ValueError("Please enter server URL"))
            return
            
        print(f"Testing connection to: {server_url}")
        # Update client with new URL
        self.api_client = APIClient(server_url)
        
        try:
            self.show_loading(True)
            self.status_label.setText("Server status: Testing connection...")
            self.status_label.setStyleSheet("color: orange")
            
            print("Creating API session...")
            await self.api_client.create_session()
            
            print("Testing login endpoint...")
            try:
                await self.api_client.login("test", "test")
            except APIError as e:
                print(f"Received API error: {e.status_code} - {e.message}")
                # If we get a 401, the connection works
                if e.status_code == 401:
                    self.is_connected = True
                    self.status_label.setText("Server status: Connected")
                    self.status_label.setStyleSheet("color: green")
                    self.show_success("Connection successful!")
                    
                    # Enable buttons if form is valid
                    self.register_btn.setEnabled(True)
                    self.validate_form()
                    
                    # Save working URL to config
                    self.config.api_base_url = server_url
                    self.config.save()
                    return
                raise e
                
        except Exception as e:
            print(f"Error during connection test: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.is_connected = False
            self.status_label.setText("Server status: Connection failed")
            self.status_label.setStyleSheet("color: red")
            self.show_error(e)
            self.login_btn.setEnabled(False)
            self.register_btn.setEnabled(False)
        finally:
            print("Connection test completed")
            self.show_loading(False)
    
    @async_callback
    async def handle_login(self, *args):
        """Handle login button click"""
        print("Login attempt started")
        email = self.email.text().strip()
        password = self.password.text()
        
        if not email or not password:
            print("Missing credentials")
            self.show_error(ValueError("Please enter email and password"))
            return
            
        try:
            self.show_loading(True)
            print(f"Attempting login for email: {email}")
            
            # Disable inputs during login
            self.email.setEnabled(False)
            self.password.setEnabled(False)
            self.login_btn.setEnabled(False)
            
            response = await self.api_client.login(email, password)
            print("Login successful")
            
            # Save successful login
            self.config.save()
            
            # Emit success signal with login response
            self.login_successful.emit(response)
            
            # Close dialog
            self.accept()
            
        except APIError as e:
            print(f"Login failed with API error: {e.status_code} - {e.message}")
            if e.status_code == 401:
                self.show_error(Exception("Invalid email or password"))
            elif e.status_code == 429:
                self.show_error(Exception("Too many login attempts. Please try again later."))
            else:
                self.show_error(e)
        except Exception as e:
            print(f"Login failed with error: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.show_error(e)
        finally:
            print("Login attempt completed")
            self.show_loading(False)
            # Re-enable inputs
            self.email.setEnabled(True)
            self.password.setEnabled(True)
            self.validate_form()