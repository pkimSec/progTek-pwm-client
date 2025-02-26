import sys
import asyncio
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from gui.dialogs.login import LoginDialog
from gui.dialogs.register import RegisterDialog
from gui.main_window import MainWindow
from utils.config import AppConfig
from api.models import LoginResponse
from utils.async_utils import async_callback

def handle_login_success(login_response: LoginResponse, master_password: str):
    """Handle successful login by creating and showing the main window"""
    print(f"Login successful for user: {login_response.user_id} (Role: {login_response.role})")
    
    try:
        # Important: Pass the existing API client that has the active session
        api_client = login_dialog.api_client
        
        # Create and show main window
        window = MainWindow(
            api_token=login_response.access_token,
            user_id=login_response.user_id, 
            user_role=login_response.role,
            master_password=master_password,
            config=app_config,
            api_client=api_client  # Pass the client with active session
        )
        
        # Store reference to window to prevent garbage collection
        global main_window
        main_window = window
        
        print("Main window created, about to show...")
        
        # Make sure window is actually displayed
        window.show()
        window.showMaximized()  # Show maximized
        
        print("Main window shown")
        
        # Hide login dialog
        if login_dialog:
            login_dialog.hide()
            
    except Exception as e:
        print(f"Error creating main window: {str(e)}")
        import traceback
        traceback.print_exc()
        show_error(f"Error starting application: {str(e)}")

@async_callback
async def check_session_status(api_client):
    """Check if session is valid"""
    try:
        print("Checking session status...")
        # Use an endpoint that requires a session
        user_info = await api_client._request('GET', api_client.endpoints._url('/api/debug/token'), include_auth=True)
        print(f"Session verified: {user_info}")
        return True
    except Exception as e:
        print(f"Session validation error: {str(e)}")
        return False

def show_register_dialog():
    """Show registration dialog"""
    print("Showing registration dialog")
    global register_dialog
    try:
        # Create and show register dialog
        register_dialog = RegisterDialog(app_config)
        register_dialog.register_successful.connect(on_register_successful)
        result = register_dialog.exec()
        
        # If register dialog is closed or cancelled, show login dialog again
        if result != QDialog.DialogCode.Accepted:
            login_dialog.show()
    except Exception as e:
        print(f"Error showing register dialog: {str(e)}")
        traceback.print_exc()
        show_error(f"Error showing registration form: {str(e)}")
        login_dialog.show()

def on_register_successful():
    """Handle successful registration by showing login dialog"""
    print("Registration successful, showing login dialog")
    login_dialog.show()
    # Pre-fill email from registration if available
    if hasattr(register_dialog, 'email') and register_dialog.email.text():
        login_dialog.email.setText(register_dialog.email.text())
        login_dialog.password.setFocus()

def show_error(message: str):
    """Show error message box"""
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Error")
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

def main():
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Password Manager")
    
    # Load configuration
    global app_config
    app_config = AppConfig.load()
    
    # Create login dialog
    global login_dialog
    login_dialog = LoginDialog(app_config)
    login_dialog.login_successful.connect(handle_login_success)
    
    # Show login dialog and handle result
    result = login_dialog.exec()
    
    # Handle special return codes
    if result == 2:  # Register code
        show_register_dialog()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    # Global variables
    # Global variables
    app_config = None
    login_dialog = None
    register_dialog = None
    main_window = None  

    if sys.platform == "win32":
        # Windows specific event loop configuration
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()