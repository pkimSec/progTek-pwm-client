from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFormLayout,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.widgets.strength_meter import PasswordStrengthMeter
from gui.dialogs.base_dialog import BaseDialog
from utils.async_utils import async_callback

class PasswordChangeDialog(BaseDialog):
    """Dialog for changing the user's password"""
    
    password_changed = pyqtSignal()  # Signal emitted when password is successfully changed
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Info text
        info_label = QLabel(
            "Change your master password. Make sure to use a strong, "
            "unique password that you can remember."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        
        # Current password
        self.current_password = QLineEdit()
        self.current_password.setPlaceholderText("Enter your current password")
        self.current_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Current Password:", self.current_password)
        
        # New password
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Enter your new password")
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("New Password:", self.new_password)
        
        # Password strength meter
        self.strength_meter = PasswordStrengthMeter()
        self.new_password.textChanged.connect(self.strength_meter.update_strength)
        form_layout.addRow("Strength:", self.strength_meter)
        
        # Confirm new password
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Confirm your new password")
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Confirm Password:", self.confirm_password)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.change_btn = QPushButton("Change Password")
        self.change_btn.clicked.connect(self.change_password)
        button_layout.addWidget(self.change_btn)
        
        layout.addLayout(button_layout)
        
        # Add progress bar
        self.setup_progress_bar(layout)
        
        # Set initial focus
        self.current_password.setFocus()
    
    def validate_form(self):
        """Validate form inputs"""
        # Check if all fields are filled
        if not self.current_password.text():
            self.show_error(Exception("Please enter your current password"))
            self.current_password.setFocus()
            return False
            
        if not self.new_password.text():
            self.show_error(Exception("Please enter your new password"))
            self.new_password.setFocus()
            return False
            
        if not self.confirm_password.text():
            self.show_error(Exception("Please confirm your new password"))
            self.confirm_password.setFocus()
            return False
            
        # Check if new password has minimum strength
        if len(self.new_password.text()) < 8:
            self.show_error(Exception("New password must be at least 8 characters long"))
            self.new_password.setFocus()
            return False
            
        # Check if passwords match
        if self.new_password.text() != self.confirm_password.text():
            self.show_error(Exception("Passwords do not match"))
            self.confirm_password.setFocus()
            return False
            
        return True
    
    def change_password(self):
        """Handle password change button click"""
        if not self.validate_form():
            return
            
        # Define the async function that will perform the password change
        @async_callback
        async def perform_password_change(parent_dialog):
            """Async function to perform the password change"""
            try:
                parent_dialog.show_loading(True)
                parent_dialog.change_btn.setEnabled(False)
                parent_dialog.cancel_btn.setEnabled(False)
                
                # Call API to change password
                result = await parent_dialog.api_client.change_password(
                    parent_dialog.current_password.text(), 
                    parent_dialog.new_password.text()
                )
                
                # Show success message
                parent_dialog.show_success("Password changed successfully!")
                
                # Emit signal
                parent_dialog.password_changed.emit()
                
                # Store a reference to the new password (optional, for auto re-login)
                if hasattr(parent_dialog.api_client, 'set_master_password'):
                    parent_dialog.api_client.set_master_password(parent_dialog.new_password.text())
                
                # Close dialog with a small delay to ensure success message is displayed
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1500, parent_dialog.accept)
                
            except Exception as e:
                try:
                    # Only show error if dialog still exists
                    if parent_dialog and parent_dialog.isVisible():
                        parent_dialog.show_error(e)
                        parent_dialog.change_btn.setEnabled(True)
                        parent_dialog.cancel_btn.setEnabled(True)
                except RuntimeError:
                    # Dialog already deleted, log the error instead
                    print(f"Error changing password: {e}")
            finally:
                try:
                    # Only hide loading if dialog still exists
                    if parent_dialog and parent_dialog.isVisible():
                        parent_dialog.show_loading(False)
                except RuntimeError:
                    # Dialog already deleted, ignore
                    pass
        
        # Call the async function, passing self as the parameter
        perform_password_change(self)