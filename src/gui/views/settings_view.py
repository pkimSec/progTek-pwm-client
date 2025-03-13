from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFormLayout, QComboBox, QSpinBox,
    QLineEdit, QGroupBox, QCheckBox, QTabWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer

from api.client import APIClient
from utils.config import AppConfig
from utils.async_utils import async_callback
from gui.dialogs.password_change import PasswordChangeDialog

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
        self.auto_lock.stateChanged.connect(self.on_auto_lock_changed)
        security_layout.addRow("", self.auto_lock)
        
        self.clipboard_clear = QCheckBox("Clear clipboard after")
        self.clipboard_clear.setChecked(True)
        self.clipboard_clear.stateChanged.connect(self.on_clipboard_clear_changed)
        
        clipboard_layout = QHBoxLayout()
        clipboard_layout.addWidget(self.clipboard_clear)
        
        self.clipboard_timeout = QSpinBox()
        self.clipboard_timeout.setRange(10, 300)
        self.clipboard_timeout.setValue(30)
        self.clipboard_timeout.setSuffix(" seconds")
        self.clipboard_timeout.valueChanged.connect(self.on_clipboard_timeout_changed)
        clipboard_layout.addWidget(self.clipboard_timeout)
        clipboard_layout.addStretch()
        
        security_layout.addRow("", clipboard_layout)
        
        # Password Change Button
        password_btn = QPushButton("Change Master Password")
        password_btn.clicked.connect(self.show_password_change_dialog)
        security_layout.addRow("", password_btn)
        
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
            "<h2>progTek-pwm-Client</h2>"
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
        
        # Update main window timeout if available
        main_window = self.window()
        if hasattr(main_window, 'inactivity_timer'):
            print(f"Updating main window inactivity timer to {value} minutes")
            # Convert minutes to milliseconds
            main_window.inactivity_timer.setInterval(value * 60 * 1000)
    
    def on_api_timeout_changed(self, value):
        """Handle API timeout change"""
        self.config.api_timeout = value
        
        # Update API client timeout if possible
        if self.api_client and hasattr(self.api_client, 'session') and self.api_client.session:
            try:
                self.api_client.session.timeout = value
                print(f"Updated API client timeout to {value} seconds")
            except Exception as e:
                print(f"Could not update API client timeout: {e}")
    
    def on_auto_lock_changed(self, state):
        """Handle auto lock change"""
        is_checked = (state == Qt.CheckState.Checked)
        
        # Update main window auto lock if available
        main_window = self.window()
        if hasattr(main_window, 'inactivity_timer'):
            if is_checked:
                main_window.inactivity_timer.start()
                print("Auto lock enabled")
            else:
                main_window.inactivity_timer.stop()
                print("Auto lock disabled")
    
    def on_clipboard_clear_changed(self, state):
        """Handle clipboard clear change"""
        is_checked = (state == Qt.CheckState.Checked)
        self.clipboard_timeout.setEnabled(is_checked)
        
        # Store in config
        self.config.clipboard_clear_enabled = is_checked
    
    def on_clipboard_timeout_changed(self, value):
        """Handle clipboard timeout change"""
        # Store in config
        self.config.clipboard_clear_timeout = value
    
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
            result = await self.api_client.get_vault_salt()
            
            # Show success message
            QMessageBox.information(
                self, "Connection Test",
                "Server connection successful!",
                QMessageBox.StandardButton.Ok
            )
            
            return result
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self, "Connection Test",
                f"Connection failed: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return None
    
    def show_password_change_dialog(self):
        """Show password change dialog"""
        dialog = PasswordChangeDialog(self.api_client, self)
        dialog.password_changed.connect(self.on_password_changed)
        dialog.exec()
    
    def on_password_changed(self):
        """Handle password change success"""
        # Notify the user through a message box
        QMessageBox.information(
            self,
            "Password Changed",
            "Your master password has been successfully changed. "
            "Make sure you remember your new password, as it cannot be recovered.",
            QMessageBox.StandardButton.Ok
        )
        
        # Update master password in main window
        main_window = self.window()
        if hasattr(main_window, 'user_session') and hasattr(main_window.user_session, 'clear_sensitive_data'):
            # Clear the old password from memory
            main_window.user_session.clear_sensitive_data()
            
            # Need to re-login or lock vault to set new password
            reply = QMessageBox.question(
                self,
                "Vault Access",
                "To apply the new password, you need to log out and log back in. "
                "Would you like to do this now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes and hasattr(main_window, 'handle_logout'):
                # Use QTimer to delay the logout to ensure this function completes first
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, main_window.handle_logout)