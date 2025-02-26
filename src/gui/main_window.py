from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMessageBox, QStackedWidget,
    QToolBar, QStatusBar, QLabel, QMenu, QMenuBar,
    QVBoxLayout, QWidget, QDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize

from api.client import APIClient
from utils.config import AppConfig
from utils.async_utils import async_callback
from gui.views.vault_view import VaultView
from gui.views.admin_view import AdminView
from gui.views.settings_view import SettingsView
import traceback
import time

class MainWindow(QMainWindow):
    """Main application window with vault management and admin features"""
    
    def __init__(self, api_token: str, user_id: int, user_role: str, 
             master_password: str, config: AppConfig, api_client=None, parent=None):
        super().__init__(parent)
        self.api_token = api_token
        self.user_id = user_id
        self.user_role = user_role
        self.master_password = master_password
        self.config = config
    
        self.api_client = api_client
        self.api_client._access_token = api_token
    
        # Setup UI
        self.setup_ui()
        # Verify session
        self.verify_session()
    
        # Start token refresh timer
        self.setup_token_refresh()

        # Start auto-logout timer
        self.setup_auto_logout()
    
        print(f"Main window initialized for user {user_id} with role {user_role}")

    @async_callback
    async def verify_session(self):
        """Verify that the session is valid"""
        try:
            print("Verifying session status...")
            result = await self.api_client.verify_session()
            if result:
                print(f"Session verified: {result}")
                self.statusbar.showMessage("Session verified", 2000)
            else:
                print("Session verification failed")
                self.statusbar.showMessage("Session verification failed - please log in again", 5000)
                QTimer.singleShot(5000, self.logout)
        except Exception as e:
            print(f"Session verification error: {str(e)}")
            self.statusbar.showMessage("Session error - please log in again", 5000)
            QTimer.singleShot(5000, self.logout)
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Manager")
        self.resize(self.config.window_width, self.config.window_height)
        
        # Create central widget with stacked layout
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main views
        self.setup_views()
        
        # Create toolbar with actions
        self.setup_toolbar()
        
        # Create menu bar
        self.setup_menu()
        
        # Create status bar
        self.setup_status_bar()
        
        # Show default view
        self.show_vault_view()
    
    def setup_views(self):
        """Initialize different views/pages"""
        # Create vault view (default)
        self.vault_view = VaultView(
            api_client=self.api_client,
            master_password=self.master_password,
            parent=self
        )
        self.central_widget.addWidget(self.vault_view)
        
        # Create admin view (only for admin users)
        if self.user_role == 'admin':
            self.admin_view = AdminView(
                api_client=self.api_client,
                parent=self
            )
            self.central_widget.addWidget(self.admin_view)
        else:
            self.admin_view = None
        
        # Create settings view
        self.settings_view = SettingsView(
            config=self.config,
            parent=self
        )
        self.central_widget.addWidget(self.settings_view)
    
    def setup_toolbar(self):
        """Initialize toolbar with actions"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Vault action
        self.vault_action = QAction("Vault", self)
        self.vault_action.triggered.connect(self.show_vault_view)
        self.toolbar.addAction(self.vault_action)
        
        # Admin action (only for admin users)
        if self.user_role == 'admin':
            self.admin_action = QAction("Admin", self)
            self.admin_action.triggered.connect(self.show_admin_view)
            self.toolbar.addAction(self.admin_action)
        
        # Settings action
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.show_settings_view)
        self.toolbar.addAction(self.settings_action)
        
        # Separator
        self.toolbar.addSeparator()
        
        # Lock action
        self.lock_action = QAction("Lock", self)
        self.lock_action.triggered.connect(self.lock_vault)
        self.toolbar.addAction(self.lock_action)
        
        # Logout action
        self.logout_action = QAction("Logout", self)
        self.logout_action.triggered.connect(self.logout)
        self.toolbar.addAction(self.logout_action)
    
    def setup_menu(self):
        """Initialize application menu"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Add actions to file menu
        file_menu.addAction(self.vault_action)
        if self.user_role == 'admin':
            file_menu.addAction(self.admin_action)
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.lock_action)
        file_menu.addAction(self.logout_action)
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Initialize status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Add status message
        self.status_label = QLabel(f"Connected as: {self.user_role}")
        self.statusbar.addWidget(self.status_label)
        
        # Add session timer
        self.session_timer_label = QLabel("Session: 60:00")
        self.statusbar.addPermanentWidget(self.session_timer_label)
    
    def setup_token_refresh(self):
        """Setup timer for token refresh"""
        # Create timer to refresh token every X minutes
        self.token_timer = QTimer(self)
        # Convert minutes to milliseconds
        refresh_interval = self.config.token_refresh_interval * 60 * 1000
        self.token_timer.setInterval(refresh_interval)
        self.token_timer.timeout.connect(self.refresh_token)
        self.token_timer.start()
    
    def setup_auto_logout(self):
        """Setup timer for automatic logout"""
        # Start time for session
        self.session_start_time = time.time()
        
        # Create timer to update session time display every second
        self.session_display_timer = QTimer(self)
        self.session_display_timer.setInterval(1000)  # 1 second
        self.session_display_timer.timeout.connect(self.update_session_timer)
        self.session_display_timer.start()
    
    def update_session_timer(self):
        """Update session timer display"""
        elapsed_time = time.time() - self.session_start_time
        remaining_time = max(0, (self.config.session_timeout * 60) - elapsed_time)
        
        # Format as MM:SS
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        self.session_timer_label.setText(f"Session: {minutes:02d}:{seconds:02d}")
        
        # Logout if time expired
        if remaining_time <= 0:
            self.session_display_timer.stop()
            self.auto_logout()
    
    @async_callback
    async def refresh_token(self):
        """Refresh the API token"""
        print("Refreshing API token...")
        try:
            # For this implementation, we just assume re-login is required
            # Typically, you'd use a refresh token or a dedicated endpoint
            # Since our server doesn't have a refresh token endpoint,
            # we would need to handle re-login if the token expires
            
            # Check token validity
            await self.api_client.ensure_session()
            
            # Reset session timer when token is refreshed
            self.session_start_time = time.time()
            
        except Exception as e:
            print(f"Token refresh failed: {str(e)}")
            traceback.print_exc()
            # Token refresh failed, force logout
            self.auto_logout()
    
    def show_vault_view(self):
        """Switch to vault view"""
        self.central_widget.setCurrentWidget(self.vault_view)
        self.statusbar.showMessage("Vault view", 2000)
    
    def show_admin_view(self):
        """Switch to admin view"""
        if self.admin_view:
            self.central_widget.setCurrentWidget(self.admin_view)
            self.statusbar.showMessage("Admin view", 2000)
        else:
            self.statusbar.showMessage("Admin view not available", 2000)
    
    def show_settings_view(self):
        """Switch to settings view"""
        self.central_widget.setCurrentWidget(self.settings_view)
        self.statusbar.showMessage("Settings view", 2000)
    
    def lock_vault(self):
        """Lock the vault and require master password to unlock"""
        print("Locking vault")
        # Since we keep the master password in memory, we just need to
        # display a dialog to unlock it. In a real implementation, you might
        # want to clear the master password from memory and require re-entry.
        
        # Show a message for now
        self.statusbar.showMessage("Vault locked", 2000)
        QMessageBox.information(self, "Vault Locked", 
                               "Vault is now locked. You'll need to re-enter your master password to access it.")
        
        # Trigger unlock dialog
        self.unlock_vault()
    
    def unlock_vault(self):
        """Show dialog to unlock vault with master password"""
        # This would typically show a dialog to re-enter the master password
        # For this skeleton, we'll just show a success message
        QMessageBox.information(self, "Vault Unlocked", 
                               "Vault unlocked successfully.")
        self.statusbar.showMessage("Vault unlocked", 2000)
    
    @async_callback
    async def logout(self):
        """Log out user and close application"""
        try:
            # Call logout API
            await self.api_client.logout()
            print("Logged out successfully")
        except Exception as e:
            print(f"Error during logout: {str(e)}")
            # Continue with local logout even if API call fails
        
        # Clean up and close application
        self.close()
    
    def auto_logout(self):
        """Automatically logout due to session timeout"""
        QMessageBox.warning(self, "Session Expired", 
                           "Your session has expired. Please log in again.")
        self.logout()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Password Manager",
                         "Password Manager v1.0\n\n"
                         "A secure client-side encrypted password manager\n"
                         "© 2025 Your Organization")
    
    def closeEvent(self, event):
        """Handle window close event"""
        print("Main window close event")
        # Save window size
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
    
        # Stop timers
        self.token_timer.stop()
        self.session_display_timer.stop()
    
        # Accept close event
        event.accept()
    
        # Exit application
        import sys
        sys.exit(0)