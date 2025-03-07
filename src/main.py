import sys
import asyncio
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from gui.dialogs.login import LoginDialog
from gui.dialogs.register import RegisterDialog
from gui.dialogs.master_password import MasterPasswordDialog
from gui.main_window import MainWindow
from api.client import APIClient
from api.models import LoginResponse
from utils.config import AppConfig
from utils.session import UserSession
from utils.async_utils import async_callback

class PasswordManagerApp:
    """Main application class for Password Manager"""
    
    def __init__(self):
        """Initialize application"""
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("progTek-pwm")
        
        # Load configuration
        self.config = AppConfig.load()
        
        # Initialize variables
        self.main_window = None
        self.api_client = None
        self.user_session = None
        self.session_timer = QTimer()  # Timer for session checks
        self.login_dialog = None  # Reference to login dialog
        
        # Setup session check timer
        self.session_timer.timeout.connect(self.check_session)
        self.session_timer.setInterval(60000)  # Check every minute
    
    def run(self):
        """Run the application"""
        # Check for existing session
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        
        # Try to load existing session
        user_session = UserSession.load(config_dir)
        if user_session and user_session.is_active:
            # Session exists - show master password dialog
            master_dlg = MasterPasswordDialog()
            if master_dlg.exec():
                # User entered master password
                master_password = master_dlg.get_password()
                user_session.master_password = master_password
                self.user_session = user_session
                
                # Create API client with existing token
                self.api_client = APIClient(self.config.api_base_url)
                self.api_client._access_token = user_session.access_token
                self.api_client._session_token = user_session.session_token
                self.api_client.set_master_password(master_password)
                self.api_client._user_email = user_session._user_email  # Set email for display
                
                # Show main window
                self.show_main_window()
                self.session_timer.start()
            else:
                # User clicked Logout in master password dialog
                self.handle_logout(from_master_dialog=True)
        else:
            # No valid session - show login
            self.show_login_dialog()
            
        # Start the event loop
        return self.app.exec()
    
    def show_login_dialog(self):
        """Show login dialog"""
        self.login_dialog = LoginDialog(self.config)
        self.login_dialog.login_successful.connect(self.handle_login_success)
        self.login_dialog.register_clicked.connect(self.show_register_dialog)
        
        if self.login_dialog.exec():
            # Dialog was accepted (login successful)
            pass
        else:
            # User canceled - exit application
            sys.exit(0)
    
    def show_register_dialog(self):
        """Show registration dialog"""
        # Get API client from login dialog
        api_client = APIClient(self.config.api_base_url)
        register_dialog = RegisterDialog(api_client, self.config)
        register_dialog.registration_successful.connect(self.handle_registration_success)
        
        register_dialog.exec()
    
    def handle_registration_success(self, email: str):
        """Handle successful registration"""
        # Show success message and pre-fill login dialog with email
        login_dialog = LoginDialog(self.config)
        login_dialog.login_successful.connect(self.handle_login_success)
        login_dialog.email.setText(email)
        
        if login_dialog.exec():
            # Dialog was accepted (login successful)
            pass
        else:
            # User canceled - exit application
            sys.exit(0)
    
    def handle_login_success(self, response: LoginResponse, master_password: str):
        """Handle successful login"""
        print(f"Login successful for user: {response.user_id}")
        
        # Create API client with token
        self.api_client = APIClient(self.config.api_base_url)
        self.api_client._access_token = response.access_token
        self.api_client.set_master_password(master_password)
        
        # Save the email from the login dialog
        if self.login_dialog and hasattr(self.login_dialog, 'email'):
            user_email = self.login_dialog.email.text().strip()
            self.api_client._user_email = user_email
        else:
            user_email = None
            
        # Create user session
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        
        self.user_session = UserSession(
            user_id=response.user_id,
            role=response.role,
            access_token=response.access_token,
            session_token=getattr(response, 'session_token', None),
            master_password=master_password,
            email=user_email
        )
        self.user_session.save(config_dir)
    
    def show_main_window(self):
        """Show main application window"""
        print("Showing main window...")
        try:
            if not self.main_window:
                print("Creating new MainWindow instance")
                self.main_window = MainWindow(self.api_client, self.user_session, self.config)
                self.main_window.logout_requested.connect(self.handle_logout)
                
            self.main_window.show()
            print("MainWindow show() called")
        except Exception as e:
            print(f"Error showing main window: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def handle_logout(self, from_master_dialog=False):
        """Handle logout request"""
        # Stop session timer
        self.session_timer.stop()
        
        # Clear session
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        UserSession.clear(config_dir)
        
        # Close main window
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # Perform API logout if not coming from master dialog
        if not from_master_dialog and self.api_client:
            self.logout_api()
        
        # Reset API client 
        self.api_client = None
        
        # Create a fresh login dialog
        print("Opening login dialog after logout")
        self.show_login_dialog()
    
    @async_callback
    async def logout_api(self):
        """Log out from API"""
        try:
            await self.api_client.logout()
        except Exception as e:
            print(f"Error during API logout: {str(e)}")
    
    def check_session(self):
        """Check if session is still valid"""
        # Session check logic
        if not self.user_session or not self.user_session.is_active:
            # Session expired or invalid
            self.handle_session_expired()
    
    def handle_session_expired(self):
        """Handle session expiration"""
        # Stop timer
        self.session_timer.stop()
        
        # Show expired dialog
        QMessageBox.warning(
            self.main_window if self.main_window else None,
            "Session Expired",
            "Your session has expired. Please log in again.",
            QMessageBox.StandardButton.Ok
        )
        
        # Close main window
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # Show login dialog
        self.show_login_dialog()

def main():
    """Application entry point"""
    if sys.platform == "win32":
        # Windows specific event loop configuration
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Create and run application
    app = PasswordManagerApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()