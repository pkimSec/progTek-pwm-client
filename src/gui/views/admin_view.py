from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QTextEdit, QDialog, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QClipboard, QGuiApplication

from api.client import APIClient
from utils.async_utils import async_callback

class InviteDialog(QDialog):
    """Dialog to display generated invite code"""
    
    def __init__(self, invite_code: str, parent=None):
        super().__init__(parent)
        self.invite_code = invite_code
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Invite Code Generated")
        
        layout = QVBoxLayout(self)
        
        # Instruction
        info_label = QLabel(
            "A new invite code has been generated. Share this with a user to allow them to register."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Invite code field
        invite_layout = QHBoxLayout()
        self.code_field = QLineEdit(self.invite_code)
        self.code_field.setReadOnly(True)
        invite_layout.addWidget(self.code_field)
        
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.copy_invite_code)
        invite_layout.addWidget(copy_btn)
        
        layout.addLayout(invite_layout)
        
        # Security warning
        warning_label = QLabel(
            "<b>Security Notice:</b> This invite code grants access to your password vault. "
            "Share it only with trusted individuals through a secure channel."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #CC0000")
        layout.addWidget(warning_label)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def copy_invite_code(self):
        """Copy invite code to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.invite_code)
        
        # Show confirmation
        QMessageBox.information(
            self, "Copied", 
            "Invite code copied to clipboard!",
            QMessageBox.StandardButton.Ok
        )

class AdminView(QWidget):
    """View for administrative functions"""
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Admin Dashboard</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Invite management section
        invite_group = QGroupBox("User Invitations")
        invite_layout = QVBoxLayout(invite_group)
        
        invite_info = QLabel(
            "Generate invite codes for new users. Each code can only be used once."
        )
        invite_info.setWordWrap(True)
        invite_layout.addWidget(invite_info)
        
        # Generate invite button
        generate_btn = QPushButton("Generate New Invite Code")
        generate_btn.clicked.connect(self.generate_invite_code)
        invite_layout.addWidget(generate_btn)
        
        layout.addWidget(invite_group)
        
        # User management section (placeholder for future implementation)
        user_group = QGroupBox("User Management")
        user_layout = QVBoxLayout(user_group)
        
        user_info = QLabel(
            "User management functionality will be available in a future update.\n\n"
            "Planned features:\n"
            "- List all users\n"
            "- Enable/disable user accounts\n"
            "- Reset user passwords\n"
            "- View user activity logs"
        )
        user_info.setWordWrap(True)
        user_layout.addWidget(user_info)
        
        layout.addWidget(user_group)
        
        # System information (placeholder)
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout(system_group)
        
        system_info = QLabel(
            "System information will be available in a future update.\n\n"
            "Planned features:\n"
            "- Server status monitoring\n"
            "- Database statistics\n"
            "- Active sessions\n"
            "- System logs"
        )
        system_info.setWordWrap(True)
        system_layout.addWidget(system_info)
        
        layout.addWidget(system_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    @async_callback
    async def generate_invite_code(self):
        """Generate a new invite code"""
        try:
            # Call API to create invite
            invite_code = await self.api_client.create_invite()
            
            # Show invite code dialog
            dialog = InviteDialog(invite_code, self)
            dialog.exec()
            
        except Exception as e:
            # Show error
            QMessageBox.critical(
                self, "Error", 
                f"Failed to generate invite code: {str(e)}",
                QMessageBox.StandardButton.Ok
            )