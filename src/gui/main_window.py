from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel,
    QStatusBar, QToolBar, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction

from api.client import APIClient
from utils.config import AppConfig
from utils.session import UserSession
from utils.async_utils import async_callback
from gui.views.vault_view import VaultView
from gui.views.settings_view import SettingsView
from gui.views.admin_view import AdminView
from gui.dialogs.master_password import MasterPasswordDialog

class MainWindow(QMainWindow):
    """Main application window for Password Manager"""
    
    logout_requested = pyqtSignal()
    
    def __init__(self, api_client: APIClient, user_session: UserSession, config: AppConfig, parent=None):
        print("MainWindow initialization starting")
        super().__init__(parent)
        self.api_client = api_client
        self.user_session = user_session
        self.config = config
        
        # Verify we have valid data
        if not api_client or not user_session:
            print("WARNING: MainWindow initialized with invalid api_client or user_session")
        
        # Timer for session inactivity monitoring
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.setInterval(60000)  # Check every minute
        
        # Timer for token refresh
        self.token_refresh_timer = QTimer(self)
        self.token_refresh_timer.timeout.connect(self.refresh_token)
        self.token_refresh_timer.setInterval(45 * 60 * 1000)  # 45 minutes
        
        # Last activity timestamp
        self.last_activity = None
        
        # Initialize UI
        self.setup_ui()
        print("MainWindow initialization complete")
        
        # Start timers
        self.inactivity_timer.start()
        self.token_refresh_timer.start()
    
    def setup_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Password Manager")
        self.resize(self.config.window_width, self.config.window_height)
        
        # Create central widget and layout first, which affects final window size
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Set up toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        
        # Add actions
        self.logout_action = QAction("Logout")
        self.logout_action.triggered.connect(self.handle_logout)
        self.toolbar.addAction(self.logout_action)
        
        self.lock_action = QAction("Lock Vault")
        self.lock_action.triggered.connect(self.lock_vault)
        self.toolbar.addAction(self.lock_action)
        
        # Add spacer to push user info to right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # Add user info to toolbar (email instead of user ID)
        if hasattr(self.user_session, '_user_email') and self.user_session._user_email:
            email = self.user_session._user_email
        else:
            email = f"User {self.user_session.user_id}"
        self.user_label = QLabel(f"Logged in as: {email}")
        self.toolbar.addWidget(self.user_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add vault view tab
        self.vault_view = VaultView(self.api_client, self.user_session)
        self.tab_widget.addTab(self.vault_view, "Vault")
        
        # Add settings view tab
        self.settings_view = SettingsView(self.api_client, self.config)
        self.tab_widget.addTab(self.settings_view, "Settings")
        
        # Add admin tab if user is admin
        if self.user_session.is_admin:
            self.admin_view = AdminView(self.api_client)
            self.tab_widget.addTab(self.admin_view, "Admin")
        
        layout.addWidget(self.tab_widget)
        
        # Set up status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label (just for status messages, not user info)
        self.status_label = QLabel("Ready")
        self.status_bar.addPermanentWidget(self.status_label)
        
        # Center window on screen (must be called after all UI elements are added)
        QTimer.singleShot(0, self.center_window)
    
    def center_window(self):
        """Center window on screen - called after the window has its final size"""
        try:
            screen_geometry = self.screen().availableGeometry()
            frame_geometry = self.frameGeometry()
            
            # Center the window's frame geometry in the available screen space
            center_point = screen_geometry.center()
            frame_geometry.moveCenter(center_point)
            
            print(f"Centering window: screen center={center_point.x()},{center_point.y()}, "
                  f"moving to {frame_geometry.topLeft().x()},{frame_geometry.topLeft().y()}")
                  
            self.move(frame_geometry.topLeft())
        except Exception as e:
            print(f"Error centering window: {str(e)}")

    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
        print(f"MainWindow shown: size={self.width()}x{self.height()}, pos={self.x()},{self.y()}")
        # Center window after it's shown
        QTimer.singleShot(10, self.center_window)
    
    def handle_logout(self):
        """Handle logout action"""
        print("MainWindow: Logout requested")
        reply = QMessageBox.question(
            self, "Logout Confirmation",
            "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print("MainWindow: Logout confirmed")
            # Stop timers first
            self.inactivity_timer.stop()
            self.token_refresh_timer.stop()
            
            # Store window size
            self.config.window_width = self.width()
            self.config.window_height = self.height()
            self.config.save()
            
            # Emit logout signal
            self.logout_requested.emit()
        else:
            print("MainWindow: Logout canceled")
    
    @async_callback
    async def logout_api(self):
        """Log out from API"""
        try:
            await self.api_client.logout()
        except Exception as e:
            print(f"Error during API logout: {str(e)}")
    
    def lock_vault(self):
        """Lock the vault requiring master password to unlock"""
        # Store window size before hiding
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
        
        # Hide window
        self.hide()
        
        # Show master password dialog
        master_dlg = MasterPasswordDialog(self)
        if master_dlg.exec():
            # User entered master password
            master_password = master_dlg.get_password()
            
            # Verify password (it should match the one stored in session)
            if master_password == self.user_session.master_password:
                # Password correct - show window
                self.show()
                self.status_bar.showMessage("Vault unlocked", 3000)
            else:
                # Password incorrect
                QMessageBox.critical(
                    self, "Authentication Failed",
                    "Incorrect master password. Please try again.",
                    QMessageBox.StandardButton.Ok
                )
                # Try again
                self.lock_vault()
        else:
            # User canceled - logout
            self.handle_logout()
    
    def check_inactivity(self):
        """Check for user inactivity"""
        if self.last_activity is None:
            # Initialize last activity
            self.last_activity = self.user_session.last_activity
            return
        
        # Get session timeout (in minutes)
        session_timeout = self.config.session_timeout
        
        # Check if session has been inactive for too long
        inactive_time = (self.user_session.last_activity - self.last_activity).total_seconds() / 60
        if inactive_time >= session_timeout:
            # Session inactive for too long - lock vault
            self.lock_vault()
    
    @async_callback
    async def refresh_token(self):
        """Refresh authentication token"""
        try:
            # The API client will handle token refresh automatically
            # on the next request, but we can trigger a simple request here
            # to ensure the token stays fresh
            await self.api_client.get_vault_salt()
            self.status_bar.showMessage("Session refreshed", 3000)
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            self.status_bar.showMessage("Session refresh failed", 3000)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Store window size
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
        
        # Stop timers
        self.inactivity_timer.stop()
        self.token_refresh_timer.stop()
        
        # Accept close event
        event.accept()
        
        print("MainWindow closed")