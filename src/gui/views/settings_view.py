from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QGroupBox, QLabel, QHBoxLayout, QSpinBox,
    QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from utils.config import AppConfig

class SettingsView(QWidget):
    """View for application settings"""
    
    config_changed = pyqtSignal()
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Server settings
        server_group = QGroupBox("Server Connection")
        server_layout = QFormLayout()
        
        self.server_url = QLineEdit()
        server_layout.addRow("Server URL:", self.server_url)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        self.timeout.setSuffix(" seconds")
        server_layout.addRow("Connection Timeout:", self.timeout)
        
        self.remember_server = QCheckBox("Remember server URL")
        server_layout.addRow("", self.remember_server)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # User Interface settings
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()
        
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        ui_layout.addRow("Theme:", self.theme)
        
        self.remember_email = QCheckBox("Remember last email")
        ui_layout.addRow("", self.remember_email)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Security settings
        security_group = QGroupBox("Security")
        security_layout = QFormLayout()
        
        self.token_refresh = QSpinBox()
        self.token_refresh.setRange(1, 120)
        self.token_refresh.setSuffix(" minutes")
        security_layout.addRow("Token Refresh Interval:", self.token_refresh)
        
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(1, 480)
        self.session_timeout.setSuffix(" minutes")
        security_layout.addRow("Session Timeout:", self.session_timeout)
        
        security_group.setLayout(security_layout)
        layout.addWidget(security_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_settings)
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def load_settings(self):
        """Load settings from config object"""
        # Server settings
        self.server_url.setText(self.config.api_base_url)
        self.timeout.setValue(self.config.api_timeout)
        self.remember_server.setChecked(self.config.remember_server)
        
        # UI settings
        self.theme.setCurrentText(self.config.theme.capitalize())
        self.remember_email.setChecked(self.config.remember_email)
        
        # Security settings
        self.token_refresh.setValue(self.config.token_refresh_interval)
        self.session_timeout.setValue(self.config.session_timeout)
    
    def save_settings(self):
        """Save settings to config object"""
        # Server settings
        self.config.api_base_url = self.server_url.text().strip()
        self.config.api_timeout = self.timeout.value()
        self.config.remember_server = self.remember_server.isChecked()
        
        # UI settings
        self.config.theme = self.theme.currentText().lower()
        self.config.remember_email = self.remember_email.isChecked()
        
        # Security settings
        self.config.token_refresh_interval = self.token_refresh.value()
        self.config.session_timeout = self.session_timeout.value()
        
        # Save to file
        self.config.save()
        
        # Emit signal
        self.config_changed.emit()
        
        # Show success message
        QMessageBox.information(self, "Settings", "Settings saved successfully")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Create new config with defaults
            self.config = AppConfig()
            
            # Load into UI
            self.load_settings()
            
            # Show confirmation
            QMessageBox.information(self, "Settings", "Settings reset to defaults")
            
            # Note: We don't save to disk until user clicks Save