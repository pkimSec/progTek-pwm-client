from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel,
    QStatusBar, QToolBar, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QTimer, QEvent  
from PyQt6.QtGui import QAction 

from datetime import datetime

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

        self.api_client.user_session = user_session
        # Pass the user_session to the vault_view components
        QTimer.singleShot(500, self.initialize_vault_properly)

        # Verify it is valid data
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
        self.last_activity_time = datetime.now()

        # Setup activity tracking
        self.setup_activity_tracking()

        # Initialize UI
        self.setup_ui()
        print("MainWindow initialization complete")

        # Start timers
        self.inactivity_timer.start()
        self.token_refresh_timer.start()

        # Initialize vault state
        self.initialize_vault()

    def initialize_vault(self):
        """Initialize vault with master password and salt"""
        try:
            from crypto.vault import get_vault
            
            # Get master password and salt
            master_password = self.user_session.master_password
            vault_salt = self.user_session.vault_salt
            
            print(f"Initializing vault - Master password: {bool(master_password)}, Salt: {bool(vault_salt)}")
            
            # If we don't have a salt yet, we need to get it from the server
            if not vault_salt:
                print("No vault salt available, attempting to retrieve from server")
                self.get_vault_salt()
                return
            
            # Initialize vault
            vault = get_vault()
            if master_password and vault_salt:
                if vault.unlock(master_password, vault_salt):
                    print("Vault unlocked successfully")
                    self.status_bar.showMessage("Vault unlocked", 3000)
                    
                    # Also set the master password on the API client for future use
                    if hasattr(self.api_client, 'set_master_password'):
                        self.api_client.set_master_password(master_password)
                else:
                    print("Failed to unlock vault")
                    self.status_bar.showMessage("Failed to unlock vault", 3000)
            else:
                if not master_password:
                    print("Missing master password")
                if not vault_salt:
                    print("Missing vault salt")
                self.status_bar.showMessage("Cannot unlock vault: Missing credentials", 3000)
        except Exception as e:
            print(f"Error initializing vault: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Error initializing vault: {str(e)}", 5000)

    def initialize_vault_properly(self):
        """Ensure vault is properly initialized after components are created"""
        print("Running delayed vault initialization...")
        try:
            # Ensure the vault view has the necessary components
            if hasattr(self, 'vault_view'):
                # Pass the user_session to the entry list
                if hasattr(self.vault_view, 'entry_list') and self.vault_view.entry_list:
                    if hasattr(self.vault_view.entry_list, 'api_client'):
                        self.vault_view.entry_list.api_client = self.api_client
                        print("Passed api_client to entry_list")
                    
                    # Force a reload of entries with longer delay to ensure vault is ready
                    QTimer.singleShot(1500, self.reload_entries)
                    
                    # Add a second delayed refresh to handle any race conditions
                    QTimer.singleShot(2500, self.force_refresh_entries)
        except Exception as e:
            print(f"Error in initialize_vault_properly: {str(e)}")
            import traceback
            traceback.print_exc()

    def force_refresh_entries(self):
        """Force refresh of entries display"""
        print("Forcing entry display refresh...")
        try:
            if hasattr(self, 'vault_view') and hasattr(self.vault_view, 'entry_list'):
                if hasattr(self.vault_view.entry_list, 'force_display_refresh'):
                    self.vault_view.entry_list.force_display_refresh()
                    print("Force display refresh completed")
        except Exception as e:
            print(f"Error forcing display refresh: {str(e)}")

    def reload_entries(self):
        """Force reload of entries"""
        print("Forcing reload of entries...")
        try:
            if hasattr(self, 'vault_view') and hasattr(self.vault_view, 'entry_list'):
                self.vault_view.entry_list.load_entries_sync()
                print("Entries reload triggered")
        except Exception as e:
            print(f"Error reloading entries: {str(e)}")
    
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

    def setup_activity_tracking(self):
        """Setup event filters to track user activity"""
        # Install event filter on application
        QApplication.instance().installEventFilter(self)
    
        # Also track child widgets
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        """Event filter to track user activity"""
        # These event types indicate user activity
        activity_events = [
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseMove,
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease
        ]
        
        if event.type() in activity_events:
            self.update_activity()
        
        # Let the event propagate
        return super().eventFilter(watched, event)

    def update_activity(self):
        """Update activity timestamp"""
        self.last_activity_time = datetime.now()
        self.user_session.update_activity()
    
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
        
        # Lock the vault in crypto module
        from crypto.vault import get_vault
        vault = get_vault()
        vault.lock()
        
        # Hide window
        self.hide()
        
        # Show master password dialog
        master_dlg = MasterPasswordDialog(self)
        if master_dlg.exec():
            # User entered master password
            entered_password = master_dlg.get_password()
            
            # Check if entered password matches the one used for login
            # This is the simplest solution - just compare with the stored password
            if entered_password == self.user_session.master_password:
                # Password is correct, unlock the vault
                vault.unlock(entered_password, self.user_session.vault_salt)
                
                # Show window
                self.show()
                self.status_bar.showMessage("Vault unlocked", 3000)
                
                # Update last activity time
                self.update_activity()
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
        # Get session timeout (in minutes)
        session_timeout = self.config.session_timeout
        
        # Calculate inactivity time in minutes
        now = datetime.now()
        inactive_time = (now - self.last_activity_time).total_seconds() / 60
        
        print(f"Checking inactivity: {inactive_time:.2f} minutes of {session_timeout} allowed")
        
        # Check if inactive for too long
        if inactive_time >= session_timeout:
            print(f"Inactivity detected ({inactive_time:.2f} minutes). Locking vault.")
            # Lock vault
            self.lock_vault()
    
    @async_callback
    async def refresh_token(self):
        """Refresh authentication token"""
        try:
            # The API client will handle token refresh automatically
            # on the next request, but triggering a simple request here
            # to ensure the token stays fresh
            await self.api_client.get_vault_salt()
            self.status_bar.showMessage("Session refreshed", 3000)
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            self.status_bar.showMessage("Session refresh failed", 3000)

    @async_callback
    async def get_vault_salt(self):
        """Get vault salt from server"""
        try:
            salt = await self.api_client.get_vault_salt()
            print(f"Retrieved vault salt: {salt[:10] if salt else 'None'}")
            
            if salt:
                # Store salt in session
                self.user_session.set_vault_salt(salt)
                
                # Now retry vault initialization
                self.initialize_vault()
            else:
                print("No salt received from server")
                self.status_bar.showMessage("Failed to get vault salt", 3000)
        except Exception as e:
            print(f"Error getting vault salt: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Error getting vault salt: {str(e)}", 5000)
    
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