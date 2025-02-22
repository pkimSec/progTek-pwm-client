import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from api.client import APIClient
from api.models import APIError, LoginResponse
from utils.config import AppConfig
from utils.async_utils import async_callback
from .base_dialog import BaseDialog

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LoginDialog(BaseDialog):
    """Login dialog with server connection test"""
    
    login_successful = pyqtSignal(LoginResponse)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = APIClient(config.api_base_url)
        logger.debug("LoginDialog initialized with URL: %s", config.api_base_url)
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager - Login")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Server settings
        server_group = QFormLayout()
        self.server_url = QLineEdit(self.config.api_base_url)
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
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Password:", self.password)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setEnabled(False)  # Disabled until connection test
        self.login_btn.clicked.connect(self.on_login_clicked)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.setEnabled(False)  # Disabled until connection test
        # self.register_btn.clicked.connect(self.show_register)  # TODO: Implement
        
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

    def on_test_connection_clicked(self):
        """Handle test connection button click"""
        logger.debug("Test connection button clicked")
        self.test_connection()

    def on_login_clicked(self):
        """Handle login button click"""
        logger.debug("Login button clicked")
        self.handle_login()
    
    @async_callback()
    async def test_connection(self):
        """Test connection to server"""
        logger.debug("Testing connection...")
        server_url = self.server_url.text().strip()
        if not server_url:
            self.show_error(ValueError("Please enter server URL"))
            return
        
        logger.debug("Testing connection to URL: %s", server_url)
        self.test_btn.setEnabled(False)
        self.show_loading(True)
        
        try:
            # Update client with new URL
            self.api_client = APIClient(server_url)
            await self.api_client.create_session()
            
            # Try to get salt endpoint as connection test
            try:
                await self.api_client.login("test", "test")
            except APIError as e:
                # If we get a 401, the connection works
                if e.status_code == 401:
                    logger.debug("Connection test successful")
                    self.show_success("Connection successful!")
                    self.login_btn.setEnabled(True)
                    self.register_btn.setEnabled(True)
                    
                    # Save working URL to config
                    self.config.api_base_url = server_url
                    self.config.save()
                    return
                logger.error("Connection test failed with status: %d", e.status_code)
                raise e
                
        except Exception as e:
            logger.exception("Connection test failed")
            self.show_error(e)
            self.login_btn.setEnabled(False)
            self.register_btn.setEnabled(False)
        finally:
            self.test_btn.setEnabled(True)
            self.show_loading(False)
    
    @async_callback()
    async def handle_login(self):
        """Handle login button click"""
        logger.debug("Handling login...")
        email = self.email.text().strip()
        password = self.password.text()
        
        if not email or not password:
            self.show_error(ValueError("Please enter email and password"))
            return
        
        self.login_btn.setEnabled(False)
        self.show_loading(True)
        
        try:
            logger.debug("Attempting login for email: %s", email)
            response = await self.api_client.login(email, password)
            logger.debug("Login successful")
            self.login_successful.emit(response)
            self.accept()
            
        except Exception as e:
            logger.exception("Login failed")
            self.show_error(e)
        finally:
            self.login_btn.setEnabled(True)
            self.show_loading(False)