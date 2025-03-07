from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFormLayout, QComboBox, QSpinBox,
    QLineEdit, QGroupBox, QCheckBox, QTabWidget
)
from PyQt6.QtCore import Qt

from api.client import APIClient
from utils.config import AppConfig
from utils.async_utils import async_callback

class SettingsView(QWidget):
    """View for application settings"""
    
    def __init__(self, api_client: APIClient, config: AppConfig, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.config = config
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tabs for different settings categories
        tabs = QTabWidget()
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Theme setting
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        if self.config.theme == "dark":
            self.theme_combo.setCurrentIndex(1)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        general_layout.addWidget(theme_group)
        
        # Security settings
        security_group = QGroupBox("Security")
        security_layout = QFormLayout(security_group)
        
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(1, 120)
        self.session_timeout.setValue(self.config.session_timeout)
        self.session_timeout.setSuffix(" minutes")
        self.session_timeout.valueChanged.connect(self.on_timeout_changed)
        security_layout.addRow("Session Timeout:", self.session_timeout)
        
        self.auto_lock = QCheckBox("Lock vault on system idle")
        self.auto_lock.setChecked(True)
        security_layout.addRow("", self.auto_lock)
        
        self.clipboard_clear = QCheckBox("Clear clipboard after")
        self.clipboard_clear.setChecked(True)
        
        clipboard_layout = QHBoxLayout()
        clipboard_layout.addWidget(self.clipboard_clear)
        
        self.clipboard_timeout = QSpinBox()
        self.clipboard_timeout.setRange(10, 300)
        self.clipboard_timeout.setValue(30)
        self.clipboard_timeout.setSuffix(" seconds")
        clipboard_layout.addWidget(self.clipboard_timeout)
        clipboard_layout.addStretch()
        
        security_layout.addRow("", clipboard_layout)
        
        general_layout.addWidget(security_group)
        
        # Server settings
        server_group = QGroupBox("Server Connection")
        server_layout = QFormLayout(server_group)
        
        self.server_url = QLineEdit(self.config.api_base_url)
        self.server_url.setReadOnly(True)  # Readonly in settings, change in login dialog
        server_layout.addRow("Server URL:", self.server_url)
        
        self.api_timeout = QSpinBox()
        self.api_timeout.setRange(5, 120)
        self.api_timeout.setValue(self.config.api_timeout)
        self.api_timeout.setSuffix(" seconds")
        self.api_timeout.valueChanged.connect(self.on_api_timeout_changed)
        server_layout.addRow("API Timeout:", self.api_timeout)
        
        test_server_btn = QPushButton("Test Connection")
        test_server_btn.clicked.connect(self.test_server_connection)
        server_layout.addRow("", test_server_btn)
        
        general_layout.addWidget(server_group)
        
        # Add stretch to push everything to the top
        general_layout.addStretch()
        
        # Add tab
        tabs.addTab(general_tab, "General")
        
        # About tab
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        
        about_label = QLabel(
            "<h2>Password Manager</h2>"
            "<p>Version 0.1.0</p>"
            "<p>Open source password manager with end-to-end encryption.</p>"
            "<p>License: GNU General Public License v3.0</p>"
            "<p><a href='https://github.com/pkimSec/progTek-pwm-Client'>GitHub Repository</a></p>"
        )
        about_label.setOpenExternalLinks(True)
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about_label)
        about_layout.addStretch()
        
        tabs.addTab(about_tab, "About")
        
        layout.addWidget(tabs)
        
        # Save button at bottom
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)
    
    def on_theme_changed(self, theme_name):
        """Handle theme change"""
        self.config.theme = theme_name.lower()
    
    def on_timeout_changed(self, value):
        """Handle session timeout change"""
        self.config.session_timeout = value
    
    def on_api_timeout_changed(self, value):
        """Handle API timeout change"""
        self.config.api_timeout = value
    
    def save_settings(self):
        """Save settings to configuration"""
        self.config.save()
        self.save_btn.setText("Settings Saved!")
        self.save_btn.setDisabled(True)
        
        # Reset button after delay
        QTimer.singleShot(2000, lambda: (
            self.save_btn.setText("Save Settings"),
            self.save_btn.setEnabled(True)
        ))
    
    @async_callback
    async def test_server_connection(self):
        """Test connection to server"""
        try:
            # Test connection by getting salt (requires authentication)
            await self.api_client.get_vault_salt()
            
            # Show success message
            QMessageBox.information(
                self, "Connection Test",
                "Server connection successful!",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self, "Connection Test",
                f"Connection failed: {str(e)}",
                QMessageBox.StandardButton.Ok
            )

# Fix QMessageBox and QTimer imports
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer