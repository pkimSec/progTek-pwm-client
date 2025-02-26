from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout,
    QCheckBox, QGroupBox
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
    """
    Login dialog with server connection test and credential validation.
    The password entered here also serves as the master password for vault encryption/decryption.
    """
    
    # Signal emitted when login is successful - passes login response and master password
    login_successful = pyqtSignal(LoginResponse, str)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = APIClient(config.api_base_url)
        self.is_connected = False  # Track connection state
        print(f"Initialized LoginDialog with URL: {config.api_base_url}")
        self.setup_ui()
        self.load_saved_settings()
        
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager - Login")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Server status label
        self.status_label = QLabel("Server status: Not connected")
        layout.addWidget(self.status_label)
        
        # Server settings group
        server_group = QGroupBox("Server Connection")
        server_layout = QFormLayout()
        
        self.server_url = QLineEdit(self.config.api_base_url)
        self.server_url.setPlaceholderText("http://localhost:5000")
        self.server_url.textChanged.connect(self.on_server_url_changed)
        server_layout.addRow("Server URL:", self.server_url)
        
        # Remember server checkbox
        self.remember_server_cb = QCheckBox("Remember Server")
        server_layout.addRow("", self.remember_server_cb)
        
        # Test connection button
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.on_test_connection_clicked)
        test_layout.addStretch()
        test_layout.addWidget(self.test_btn)
        server_layout.addRow("", test_layout)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Login form group
        login_group = QGroupBox("Login")
        form_layout = QFormLayout()
        
        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email")
        self.email.textChanged.connect(self.validate_form)
        form_layout.addRow("Email:", self.email)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.textChanged.connect(self.validate_form)
        form_layout.addRow("Password:", self.password)
        
        # Remember me checkbox
        self.remember_email_cb = QCheckBox("Remember Email")
        form_layout.addRow("", self.remember_email_cb)
        
        login_group.setLayout(form_layout)
        layout.addWidget(login_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setEnabled(False)
        self.login_btn.clicked.connect(self.handle_login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.setEnabled(False)
        self.register_btn.clicked.connect(self.on_register_clicked)
        
        button_layout.addWidget(self.register_btn)
        button_layout.addWidget(self.login_btn)
        
        layout.addLayout(button_layout)
        
        # Add progress bar at bottom
        self.setup_progress_bar(layout)
        
        # Set default focus
        self.server_url.setFocus()
        
        # Set enter key to trigger login if form is valid
        self.password.returnPressed.connect(self.on_return_pressed)

    def on_return_pressed(self):
        """Handle return key press in password field"""
        if self.login_btn.isEnabled():
            self.handle_login()

    def load_saved_settings(self):
        """Load saved settings from configuration"""
        # Load remember server setting
        self.remember_server_cb.setChecked(self.config.remember_server)
        
        # Load saved server URL
        if self.config.remember_server and self.config.api_base_url:
            self.server_url.setText(self.config.api_base_url)
        
        # Load remember email setting
        self.remember_email_cb.setChecked(self.config.remember_email)
        
        # Load saved email if enabled
        if self.config.remember_email and self.config.last_email:
            self.email.setText(self.config.last_email)
            self.password.setFocus()  # Focus password field if email is pre-filled
    
    def save_settings(self):
        """Save settings to configuration"""
        # Save server settings
        self.config.remember_server = self.remember_server_cb.isChecked()
        if self.config.remember_server:
            self.config.api_base_url = self.server_url.text().strip()
        
        # Save email if remember me is checked
        self.config.remember_email = self.remember_email_cb.isChecked()
        if self.config.remember_email:
            self.config.last_email = self.email.text().strip()
        else:
            self.config.last_email = ""
        
        # Save configuration
        self.config.save()

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

        # Enable login if we already tested connection OR if credentials are provided
        self.login_btn.setEnabled((self.is_connected or self.server_url.text().strip()) and has_credentials)
    
    def on_register_clicked(self):
        """Handle register button click - emit signal for parent to show register dialog"""
        self.save_settings()  # Save current server URL
        self.done(2)  # Use custom return code for register
    
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
                # We intentionally use invalid credentials to test connection
                # A 401 response means the server is reachable and the endpoint exists
                await self.api_client.login("test@example.com", "invalid_password")
            except APIError as e:
                print(f"Received API error: {e.status_code} - {e.message}")
                # If we get a 401, the connection works (authentication failed but endpoint exists)
                if e.status_code == 401:
                    self.is_connected = True
                    self.status_label.setText("Server status: Connected")
                    self.status_label.setStyleSheet("color: green")
                    self.show_success("Connection successful!")
                    
                    # Enable buttons if form is valid
                    self.register_btn.setEnabled(True)
                    self.validate_form()
                    
                    # Save working URL to config if remember server is checked
                    if self.remember_server_cb.isChecked():
                        self.config.api_base_url = server_url
                        self.config.save()
                    return
                else:
                    # Other error codes indicate a problem
                    raise e
                
        except APIError as e:
            print(f"API Error during connection test: {e.status_code} - {e.message}")
            self.is_connected = False
            self.status_label.setText(f"Server status: Error {e.status_code}")
            self.status_label.setStyleSheet("color: red")
            self.show_error(e)
        except Exception as e:
            print(f"Error during connection test: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            self.is_connected = False
            self.status_label.setText("Server status: Connection failed")
            self.status_label.setStyleSheet("color: red")
            self.show_error(Exception(f"Connection failed: {str(e)}"))
        finally:
            print("Connection test completed")
            self.show_loading(False)
            self.login_btn.setEnabled(False)
            self.register_btn.setEnabled(self.is_connected)
    
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
            
            # Perform login API call
            response = await self.api_client.login(email, password)
            print("Testing session cookie after login:")
            for cookie in self.api_client.session.cookie_jar:
                print(f"Cookie: {cookie.key}={cookie.value}")
            print("Login successful")
            
            # Save settings (email if remember me is checked, server URL if remember server is checked)
            self.save_settings()
            
            # Emit success signal with login response and master password
            # The master password is the same as the login password
            master_password = password
            self.login_successful.emit(response, master_password)
            
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