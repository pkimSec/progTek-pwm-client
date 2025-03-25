from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import traceback
import re
import sys

from api.client import APIClient
from api.models import APIError, LoginResponse
from utils.config import AppConfig
from utils.async_utils import async_callback
from utils.session import UserSession
from .base_dialog import BaseDialog

class LoginDialog(BaseDialog):
    """Login dialog with server connection test"""
    
    login_successful = pyqtSignal(LoginResponse, str)  # Added master_password parameter
    register_clicked = pyqtSignal()
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = APIClient(config.api_base_url)
        self.is_connected = False  # Track connection state
        print(f"Initialized LoginDialog with URL: {config.api_base_url}")
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("progTek-pwm")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Server settings
        server_group = QFormLayout()
        self.server_url = QLineEdit(self.config.api_base_url)
        self.server_url.setPlaceholderText("http://localhost:5000")
        self.server_url.textChanged.connect(self.on_server_url_changed)
        server_group.addRow("Server URL:", self.server_url)
        
        # Test connection layout with status on the right
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.on_test_connection_clicked)
        test_layout.addWidget(self.test_btn)
        test_layout.addStretch()
        
        # Server status label moved to the same line as the test button
        self.status_label = QLabel("Server status: Not connected")
        test_layout.addWidget(self.status_label)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email")
        self.email.textChanged.connect(self.validate_form)

        # If there's a remembered email, set it
        if self.config.remember_email and self.config.last_email:
            self.email.setText(self.config.last_email)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.textChanged.connect(self.validate_form)
        self.password.returnPressed.connect(self.handle_login)  # Enter key submits form
        
        # Login form
        form_layout = QFormLayout()
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Password:", self.password)
        
        # Remember email checkbox
        self.remember_email = QCheckBox("Remember email")
        self.remember_email.setChecked(self.config.remember_email)
        form_layout.addRow("", self.remember_email)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setEnabled(False)
        self.login_btn.clicked.connect(self.handle_login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.setEnabled(False)
        self.register_btn.clicked.connect(self.handle_register)
        
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

        # Auto-test connection on startup
        if self.server_url.text().strip():
            self.test_connection()

    def on_server_url_changed(self):
        """Handle server URL changes"""
        print("Server URL changed")
        self.is_connected = False
        self.login_btn.setEnabled(False)
        self.register_btn.setEnabled(False)
        self.status_label.setText("Server status: Not connected")
        self.status_label.setStyleSheet("color: gray")
        
        # Validate URL format
        url = self.server_url.text().strip()
        if url:
            # Allow localhost with or without protocol
            if url in ["localhost:5000", "127.0.0.1:5000"]:
                self.server_url.setText(f"http://{url}")
                return
                
            # Basic URL validation
            url_pattern = re.compile(
                r'^(http|https)://'  # http:// or https://
                r'([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?'  # domain
                r'(:[0-9]+)?'  # optional port
                r'(/.*)?$'  # optional path
            )
            
            # Also accept http://localhost:port format
            localhost_pattern = re.compile(
                r'^(http|https)://'  # http:// or https://
                r'(localhost|127\.0\.0\.1)'  # localhost or 127.0.0.1
                r'(:[0-9]+)?'  # optional port
                r'(/.*)?$'  # optional path
            )
            
            if not (url_pattern.match(url) or localhost_pattern.match(url)):
                self.status_label.setText("Server status: Invalid URL format")
                self.status_label.setStyleSheet("color: red")
                return

    def on_test_connection_clicked(self):
        """Handle test connection button click"""
        print("Test connection button clicked")
        self.test_connection()
    
    def validate_form(self):
        """Enable/disable login button based on form validity"""
        # Check if UI elements have been initialized
        if not hasattr(self, 'login_btn') or not hasattr(self, 'email'):
            return
            
        email = self.email.text().strip()
        password = self.password.text().strip() if hasattr(self, 'password') else ""
        has_credentials = bool(email and password)

        self.login_btn.setEnabled(self.is_connected and has_credentials)
    
    def handle_register(self):
        """Handle register button click"""
        self.register_clicked.emit()

    def handle_login_success(self, response, master_password):
        """
        Override this to ensure dialog closes on successful login
        """
        print("LoginDialog: Login successful, closing dialog")
        # First emit the signal
        self.login_successful.emit(response, master_password)
        # Then immediately close the dialog
        self.done(QDialog.DialogCode.Accepted)
    
    @async_callback
    async def test_connection(self):
        """Test connection to server using the ping endpoint"""
        print("Starting connection test")
        server_url = self.server_url.text().strip()
        if not server_url:
            print("No server URL provided")
            self.show_error(ValueError("Please enter server URL"))
            return
        
        # Ensure URL has proper format
        if not server_url.startswith("http://") and not server_url.startswith("https://"):
            # Check if it's localhost or IP without http://
            if server_url == "localhost:5000" or server_url == "127.0.0.1:5000":
                server_url = "http://" + server_url
            else:
                self.show_error(ValueError("Invalid URL format. Must start with http:// or https://"))
                return
            
        print(f"Testing connection to: {server_url}")

        # IMPORTANT: Reuse the existing client with the same URL instead of creating a new one
        if self.api_client.endpoints.base_url != server_url:
            # URL changed, use a fresh client
            self.api_client = APIClient(server_url)
        
        try:
            self.show_loading(True)
            self.status_label.setText("Server status: Testing connection...")
            self.status_label.setStyleSheet("color: orange")
            
            print("Creating API session...")
            await self.api_client.ensure_session()
            
            print("Sending ping request...")
            # Use the new ping endpoint instead of trying to login
            ping_url = f"{server_url}/api/ping"
            
            # Create a simple request without authentication
            async with self.api_client.session.get(ping_url) as resp:
                print(f"Ping response status: {resp.status}")
                
                if resp.status == 200:
                    self.is_connected = True
                    self.status_label.setText("Server status: Connected")
                    self.status_label.setStyleSheet("color: green")
                    
                    # Enable buttons if form is valid
                    self.register_btn.setEnabled(True)
                    self.validate_form()
                    
                    # Save working URL to config
                    self.config.api_base_url = server_url
                    self.config.save()
                    return
                    
                try:
                    data = await resp.json()
                    print(f"Ping response data: {data}")
                except:
                    print("Could not parse response as JSON")
                    
                # If we get here, connection failed
                self.is_connected = False
                self.status_label.setText(f"Server status: Connection failed ({resp.status})")
                self.status_label.setStyleSheet("color: red")
                self.show_error(Exception(f"Server connection failed with status {resp.status}"))
                
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

            # Save email if remember checkbox is checked
            self.config.remember_email = self.remember_email.isChecked()
            if self.config.remember_email:
                self.config.last_email = email
            else:
                self.config.last_email = ""

            # Save successful login in config
            self.config.save()

            # Use the new method to handle login success
            self.handle_login_success(response, password)

            
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