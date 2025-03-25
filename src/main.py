import sys
import asyncio
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt, QTimer, QObject

from gui.dialogs.login import LoginDialog
from gui.dialogs.register import RegisterDialog
from gui.dialogs.master_password import MasterPasswordDialog
from gui.main_window import MainWindow
from api.client import APIClient
from api.models import LoginResponse
from utils.config import AppConfig
from utils.session import UserSession
from utils.async_utils import async_callback

class PasswordManagerApp(QObject):
    """Main application class for Password Manager"""
    
    def __init__(self):
        """Initialize application"""
        # Create Qt application
        self.qapp = QApplication(sys.argv)
        self.qapp.setApplicationName("progTek-pwm")
        
        # Initialize QObject after QApplication exists
        super().__init__()
        
        # Load configuration
        self.config = AppConfig.load()

        # Apply theme
        from utils.theme import apply_theme, create_theme_assets
        create_theme_assets()  # Create missing icons if needed
        apply_theme(self.config.theme)
        
        # Initialize variables
        self.main_window = None
        self.api_client = None
        self.user_session = None
        self.session_timer = QTimer()  # Timer for session checks
        self.login_dialog = None  # Reference to login dialog
        self.registered_email = None  # Store email from registration
        self.is_registering = False  # Flag to track registration state
        
        # Setup session check timer
        self.session_timer.timeout.connect(self.check_session)
        self.session_timer.setInterval(60000)  # Check every minute
    
    def run(self):
        """Run the application"""
        # Clear any potentially stale session data at startup
        print("Application starting - clearing any stale session data")
        self.clear_session_data()
        
        # Check for existing session
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'progtek_pwm'
        
        # Try to load existing session
        user_session = UserSession.load(config_dir)
        if user_session and user_session.is_active:
            print(f"Found existing session for user {user_session.user_id}")
            # Session exists - show master password dialog
            master_dlg = MasterPasswordDialog()
            if master_dlg.exec():
                # User entered master password
                master_password = master_dlg.get_password()
                user_session.master_password = master_password
                self.user_session = user_session
                
                # Create API client with existing token
                print("Creating API client with existing token")
                self.api_client = APIClient(self.config.api_base_url)
                self.api_client._access_token = user_session.access_token
                self.api_client._session_token = user_session.session_token
                self.api_client.set_master_password(master_password)
                self.api_client._user_email = user_session._user_email  # Set email for display
                
                # Validate the token before proceeding
                print("Validating existing token")
                self.validate_token()
            else:
                # User clicked Logout in master password dialog
                print("User canceled master password dialog - going to login")
                self.handle_logout(from_master_dialog=True)
        else:
            print("No valid session found - showing login dialog")
            # No valid session - show login
            self.show_login_dialog()
            
        # Start the event loop
        return self.qapp.exec()
    
    def clear_session_data(self):
        """Clear all session data"""
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'progtek_pwm'
        
        # Clear session file
        UserSession.clear(config_dir)
        
        # Clear any cached APIClient instances
        if hasattr(APIClient, '_instance_cache'):
            for client in list(APIClient._instance_cache.values()):
                try:
                    if hasattr(client, 'session') and client.session:
                        print(f"Forcing close of session in client {client}")
                        asyncio.create_task(client.close())
                except Exception as e:
                    print(f"Error closing client: {e}")
            
            # Clear the cache
            APIClient.clear_all_instances()
            
        # Add a short delay to let tasks complete
        QTimer.singleShot(100, self._check_cleanup_complete)
        
        print("Session data cleared")
        
    def _check_cleanup_complete(self):
        """Check if cleanup is complete and log status"""
        # Import here to avoid circular imports
        from api.client import _active_sessions
        print(f"Active sessions after cleanup: {len(_active_sessions)}")
        if _active_sessions:
            print("Warning: Some sessions are still active")
    
    def validate_token(self):
        """Validate existing token and show appropriate UI"""
        print("Validating token...")
        
        # Check if we have an API client
        if not self.api_client:
            print("No API client available")
            self.show_login_dialog()
            return
            
        # Start the validation process using standalone task
        from utils.async_utils import standalone_async_task
        standalone_async_task(self._validate_token_async, self.api_client)

    async def _validate_token_async(self, api_client):
        """Async part of token validation"""
        try:
            # Make a test request
            print("Making test API request")
            await api_client.get_vault_salt()
            print("Token is valid - showing main window")
            
            # Token is valid, show main window
            # Need to use the main thread for UI operations
            QTimer.singleShot(0, lambda: self.show_main_window())
            QTimer.singleShot(0, lambda: self.session_timer.start())
        except Exception as e:
            print(f"Token validation failed: {str(e)}")
            # Token invalid, show login (on main thread)
            QTimer.singleShot(0, lambda: self.handle_token_error())
    
    def handle_token_error(self):
        """Handle token validation error"""
        print("Handling token error")
        # Reset state
        self.user_session = None
        self.api_client = None
        
        # Clear any saved session
        self.clear_session_data()
        
        # Show error message
        QMessageBox.warning(
            None,
            "Session Expired",
            "Your saved session has expired. Please log in again.",
            QMessageBox.StandardButton.Ok
        )
        
        # Show login dialog
        self.show_login_dialog()
    
    def show_login_dialog(self):
        """Show login dialog"""
        # First, close any existing login dialog
        if self.login_dialog is not None:
            try:
                print("Closing existing login dialog")
                self.login_dialog.hide()
                self.login_dialog.close()
                self.login_dialog.deleteLater()
            except Exception as e:
                print(f"Error closing existing login dialog: {str(e)}")
            # Clear the reference
            self.login_dialog = None

        # Create a fresh login dialog
        print("Creating new LoginDialog instance")
        self.login_dialog = LoginDialog(self.config)
        self.login_dialog.login_successful.connect(self.handle_login_success)
        self.login_dialog.register_clicked.connect(self.show_register_dialog)

        # Set the email if we have one from registration
        if self.registered_email:
            print(f"Setting email from previous registration: {self.registered_email}")
            self.login_dialog.email.setText(self.registered_email)
            # Also focus on password field
            self.login_dialog.password.setFocus()

        # Show the dialog
        print("Showing login dialog")
        result = self.login_dialog.exec()
        print(f"Login dialog exec result: {result}")

        # If dialog was rejected and we're not registering, exit
        if result == QDialog.DialogCode.Rejected and not self.is_registering:
            print("Login dialog rejected, exiting application")
            # Make sure to clean up all sessions before exiting
            self.cleanup_and_exit()

    def cleanup_and_exit(self):
        """Properly clean up all resources and exit the application"""
        print("Performing cleanup before exit")
        
        # First, clear all session data
        self.clear_session_data()
        
        # Add a small delay to ensure asynchronous cleanup tasks have time to complete
        QTimer.singleShot(100, self.force_exit)

    def force_exit(self):
        """Force the application to exit after cleanup"""
        print("Forcing application exit")
        # This will ensure the application exits even if there are pending operations
        self.qapp.exit(0)
    
    def show_register_dialog(self):
        """Show registration dialog"""
        print("Showing registration dialog")
        # Set the registration flag
        self.is_registering = True
        
        try:
            # Get API client from login dialog
            server_url = self.config.api_base_url
            if self.login_dialog and hasattr(self.login_dialog, 'server_url'):
                server_url = self.login_dialog.server_url.text().strip()
            
            # Create a fresh API client for registration
            api_client = APIClient(server_url)
            
            # Create register dialog
            register_dialog = RegisterDialog(api_client, self.config)
            register_dialog.registration_successful.connect(self.handle_registration_success)
            
            # Execute dialog
            result = register_dialog.exec()
            
            # Clean up API client
            if api_client and hasattr(api_client, 'session') and api_client.session:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(api_client.close())
                    loop.close()
                    print("Successfully closed API client session after registration")
                except Exception as e:
                    print(f"Error closing API client: {str(e)}")
            
            # If cancelled, clear registration flag and show login dialog again
            if not result:
                print("Registration cancelled by user")
                self.is_registering = False
                self.show_login_dialog()
                
        except Exception as e:
            print(f"Error in show_register_dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            # Clear the registration flag
            self.is_registering = False
            # Show login dialog again
            self.show_login_dialog()
    
    def handle_registration_success(self, email: str):
        """Handle successful registration"""
        print(f"Handling registration success for email: {email}")
        
        # Store registered email
        self.registered_email = email
        
        # Schedule the creation of a new login dialog
        QTimer.singleShot(500, self.create_new_login_dialog)
    
    def create_new_login_dialog(self):
        """Create a new login dialog after registration"""
        try:
            print("Creating new login dialog after registration")
            # Clear registration flag now that we're showing the login dialog
            self.is_registering = False
            self.show_login_dialog()
            
        except Exception as e:
            print(f"Error creating new login dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            # Exit application if we can't show the login dialog
            self.qapp.quit()
    
    def handle_login_success(self, response: LoginResponse, master_password: str):
        """Handle successful login"""
        print(f"Login successful for user: {response.user_id}")

        # Store the login dialog reference to close it later
        login_dialog_to_close = self.login_dialog

        # Clear the login dialog reference immediately to prevent multiple instances
        self.login_dialog = None

        # Close any existing main window before creating new resources
        if self.main_window:
            print("Closing existing main window before creating new session")
            try:
                self.main_window.close()
            except Exception as e:
                print(f"Error closing existing window: {str(e)}")
            self.main_window = None

        # Create API client with token
        print("Creating new API client with fresh token")
        self.api_client = APIClient(self.config.api_base_url)
        self.api_client._access_token = response.access_token
        self.api_client._session_token = getattr(response, 'session_token', None)
        
        # Store the master password before initializing vault
        self.api_client._master_password = master_password
        
        # Save the email from the login dialog
        user_email = None
        if login_dialog_to_close and hasattr(login_dialog_to_close, 'email'):
            user_email = login_dialog_to_close.email.text().strip()
            self.api_client._user_email = user_email
            print(f"Using email from login dialog: {user_email}")
        else:
            print("No email from login dialog")
                
        # Create user session
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        
        print("Creating new user session")
        self.user_session = UserSession(
            user_id=response.user_id,
            role=response.role,
            access_token=response.access_token,
            session_token=getattr(response, 'session_token', None),
            master_password=master_password,
            email=user_email
        )
        
        # Associate user_session with api_client immediately
        self.api_client.user_session = self.user_session
        
        # Save session to disk
        self.user_session.save(config_dir)
        
        # Fetch vault salt before showing main window
        self.fetch_salt_and_continue(login_dialog_to_close)

    def handle_login_error(self):
        """Handle login errors gracefully"""
        print("Handling login error")
        # Display an error message
        QMessageBox.critical(
            None,
            "Login Error",
            "There was an error logging in. The application will now restart.",
            QMessageBox.StandardButton.Ok
        )
        
        # Clean up resources
        self.clear_session_data()
        
        # Show login dialog again
        QTimer.singleShot(100, self.show_login_dialog)

    @async_callback
    async def fetch_salt_and_continue(self, login_dialog_to_close=None):
        """Fetch vault salt and then show main window"""
        try:
            print("Fetching vault salt before showing main window...")
            
            # Check if API client exists
            if not self.api_client:
                print("Warning: API client is None, creating a new one")
                # Create a new API client from the session data
                if hasattr(self, 'user_session') and self.user_session:
                    self.api_client = APIClient(self.config.api_base_url)
                    self.api_client._access_token = self.user_session.access_token
                    self.api_client._session_token = self.user_session.session_token
                    if hasattr(self.user_session, 'master_password') and self.user_session.master_password:
                        self.api_client._master_password = self.user_session.master_password
                    if hasattr(self.user_session, '_user_email'):
                        self.api_client._user_email = self.user_session._user_email
                    
                    # Associate user_session with api_client
                    self.api_client.user_session = self.user_session
                else:
                    print("Cannot create API client - missing user session data")
                    
            # If we now have an API client, try to fetch salt
            if self.api_client:
                try:
                    salt = await self.api_client.get_vault_salt()
                    
                    if salt:
                        print(f"Successfully retrieved vault salt: {salt[:10]}...")
                        self.user_session.set_vault_salt(salt)
                        self.user_session.save(Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config') / 'password_manager')
                        
                        # Now set the master password to unlock the vault
                        if hasattr(self.api_client, '_master_password') and self.api_client._master_password:
                            self.api_client.set_master_password(self.api_client._master_password)
                    else:
                        print("Warning: Could not retrieve vault salt")
                except Exception as e:
                    print(f"Error getting salt: {str(e)}")
                    # Continue without salt - the main window will try again
        except TypeError as e:
            print(f"Type error fetching vault salt: {str(e)}")
            # Continue despite the error
        except Exception as e:
            print(f"Error fetching vault salt: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Close the login dialog using a direct approach
            if login_dialog_to_close:
                try:
                    print("Closing login dialog")
                    # First hide it so it disappears from screen immediately
                    login_dialog_to_close.hide()
                    # Then close it
                    login_dialog_to_close.close()
                    # For good measure, try to delete it
                    login_dialog_to_close.deleteLater()
                    print("Login dialog scheduled for deletion")
                except Exception as e:
                    print(f"Error closing login dialog: {str(e)}")
            
            # Make sure we have a valid API client before showing the main window
            if not self.api_client and hasattr(self, 'user_session') and self.user_session:
                print("Re-creating API client as final fallback")
                self.api_client = APIClient(self.config.api_base_url)
                self.api_client._access_token = self.user_session.access_token
                self.api_client._session_token = self.user_session.session_token
                self.api_client.user_session = self.user_session
            
            # Schedule showing the main window
            QTimer.singleShot(0, self.show_main_window)
            self.session_timer.start()
        
    def show_main_window(self):
        """Show main application window"""
        print("Showing main window...")
        try:
            # First, check if there's already a MainWindow and close it
            if self.main_window:
                print("Found existing MainWindow, closing it first")
                try:
                    self.main_window.close()
                except Exception as e:
                    print(f"Error closing existing window: {str(e)}")
                self.main_window = None
            
            # Verify that we have a valid API client before creating the main window
            if not self.api_client:
                print("ERROR: Missing API client, cannot show main window")
                # Re-create API client if needed
                if hasattr(self, 'user_session') and self.user_session and self.user_session.access_token:
                    print("Recreating API client from user session data")
                    self.api_client = APIClient(self.config.api_base_url)
                    self.api_client._access_token = self.user_session.access_token
                    self.api_client._session_token = self.user_session.session_token
                    if hasattr(self.user_session, 'master_password'):
                        self.api_client._master_password = self.user_session.master_password
                    self.api_client._user_email = self.user_session._user_email if hasattr(self.user_session, '_user_email') else None
                else:
                    print("Cannot recreate API client, missing user session data")
                    self.handle_login_error()
                    return
            
            print("Creating new MainWindow instance")
            self.main_window = MainWindow(self.api_client, self.user_session, self.config)
            self.main_window.logout_requested.connect(self.handle_logout)
            
            # Show window immediately instead of using QTimer
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            print("Window show completed directly")
            
        except Exception as e:
            print(f"Error showing main window: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to handle the error gracefully
            self.handle_login_error()
    
    def _show_window(self):
        """Actually show the window - called by timer"""
        if self.main_window:
            print("Showing window NOW")
            self.main_window.show()
            # Raise and activate window to bring it to front
            self.main_window.raise_()
            self.main_window.activateWindow()
            print("Window show complete")

    def handle_logout(self, from_master_dialog=False):
        """Handle logout request"""
        print("Handling logout request")
        
        # Stop session timer
        self.session_timer.stop()
        
        # Store the API client reference for logout
        api_client = self.api_client
        
        # Close main window
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # Clear session on disk
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        UserSession.clear(config_dir)
        
        # Clear session in memory
        self.user_session = None
        
        # Perform API logout if not from master dialog and we have an API client
        if not from_master_dialog and api_client is not None:
            print(f"Initiating API logout with client: {api_client}")
            self.logout_api(api_client)
        
        # Reset API client reference after logout is initiated
        self.api_client = None
        
        # Create a fresh login dialog
        print("Opening login dialog after logout")
        self.show_login_dialog()
    
    def logout_api(self, api_client=None):
        """Log out from API - non-async version"""
        # Don't use async_callback here since it can be called with a captured client
        client_to_use = api_client or self.api_client
        
        if client_to_use:
            try:
                # Use a more reliable approach for logout
                import asyncio
                
                async def safe_logout():
                    try:
                        if hasattr(client_to_use, 'logout'):
                            await client_to_use.logout()
                        # Always close the session
                        if hasattr(client_to_use, 'close'):
                            await client_to_use.close()
                    except Exception as e:
                        print(f"Error during API logout: {str(e)}")
                
                # Try to get current event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # Create a new event loop if needed
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the logout function
                if loop.is_running():
                    # Create a task if loop is already running
                    asyncio.create_task(safe_logout())
                else:
                    # Otherwise run it directly
                    loop.run_until_complete(safe_logout())
                    
                print("API logout initiated")
            except Exception as e:
                print(f"Error initiating API logout: {str(e)}")
        else:
            print("No API client available for logout")

    @staticmethod
    async def _logout_api_async(api_client):
        """Static async method to perform API logout"""
        if api_client is None:
            print("No API client provided for logout")
            return
            
        try:
            print(f"Logging out API client: {api_client}")
            await api_client.logout()
            print("API logout completed successfully")
            # Properly close the session
            await api_client.close()
        except Exception as e:
            print(f"Error during API logout: {str(e)}")
            # Still try to close the session even if logout failed
            try:
                await api_client.close()
            except Exception as e2:
                print(f"Error closing API client session: {str(e2)}")

    def _handle_logout_async(self, api_client):
        """Handle the async part of logout"""
        # Create a separate AsyncRunner without parent
        from PyQt6.QtCore import QObject
        class LogoutRunner(QObject):
            def __init__(self):
                super().__init__()
                print("Created LogoutRunner")
            
            def run(self, api_client):
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(PasswordManagerApp._logout_api_async(api_client))
                except Exception as e:
                    print(f"Error in LogoutRunner: {str(e)}")
        
        # Create and run on a timer to not block the UI
        runner = LogoutRunner()
        QTimer.singleShot(0, lambda: runner.run(api_client))
    
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

def emergency_cleanup():
    """Emergency cleanup function to close any open resources before exit"""
    print("Performing emergency cleanup")
    
    # Import here to avoid circular imports
    from api.client import _active_sessions
    print(f"Active sessions at exit: {len(_active_sessions)}")
    
    # Force close any active sessions
    for session_ref in list(_active_sessions):
        session = session_ref()
        if session and not session.closed:
            try:
                print(f"Forcing close of session: {id(session)}")
                # Create a new event loop for synchronous cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(session.close())
                loop.close()
            except Exception as e:
                print(f"Error during emergency session close: {e}")
    
    print("Emergency cleanup complete")

def main():
    """Application entry point"""
    if sys.platform == "win32":
        # Windows specific event loop configuration
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Register exit handler
    import atexit
    atexit.register(emergency_cleanup)
    
    # Create and run application
    app = PasswordManagerApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()