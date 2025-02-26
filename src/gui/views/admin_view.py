from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QGroupBox, QFormLayout,
    QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QClipboard, QGuiApplication, QAction

from api.client import APIClient
from api.models import APIError
from utils.async_utils import async_callback

class AdminView(QWidget):
    """Admin view for managing users and invite codes"""
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.invite_codes = []
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Admin Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Invite code section
        invite_group = QGroupBox("Invite Codes")
        invite_layout = QVBoxLayout()
        
        # Create invite button
        self.create_invite_btn = QPushButton("Generate New Invite Code")
        self.create_invite_btn.clicked.connect(self.create_invite_code)
        invite_layout.addWidget(self.create_invite_btn)
        
        # Invite codes table
        self.invite_table = QTableWidget(0, 2)  # Rows, Columns
        self.invite_table.setHorizontalHeaderLabels(["Invite Code", "Actions"])
        self.invite_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.invite_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        invite_layout.addWidget(self.invite_table)
        
        invite_group.setLayout(invite_layout)
        layout.addWidget(invite_group)
        
        # Status message
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    @async_callback
    async def create_invite_code(self):
        """Generate a new invite code"""
        try:
            self.status_label.setText("Generating invite code...")
            self.create_invite_btn.setEnabled(False)
            
            # Call API to create invite code
            invite_code = await self.api_client.create_invite()
            print(f"Generated invite code: {invite_code}")
            
            # Add to table
            self.add_invite_to_table(invite_code)
            
            self.status_label.setText("Invite code generated successfully")
            QMessageBox.information(self, "Success", "New invite code generated successfully.")
            
        except APIError as e:
            self.status_label.setText(f"Error: {e.message}")
            QMessageBox.critical(self, "Error", f"Failed to generate invite code: {e.message}")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to generate invite code: {str(e)}")
        finally:
            self.create_invite_btn.setEnabled(True)
    
    def add_invite_to_table(self, invite_code: str):
        """Add invite code to the table"""
        # Add to stored list
        self.invite_codes.append(invite_code)
        
        # Add row to table
        row_position = self.invite_table.rowCount()
        self.invite_table.insertRow(row_position)
        
        # Add invite code
        code_item = QTableWidgetItem(invite_code)
        code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
        self.invite_table.setItem(row_position, 0, code_item)
        
        # Add action buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        
        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: self.copy_invite_code(invite_code))
        actions_layout.addWidget(copy_btn)
        
        self.invite_table.setCellWidget(row_position, 1, actions_widget)
    
    def copy_invite_code(self, invite_code: str):
        """Copy invite code to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(invite_code)
        self.status_label.setText("Invite code copied to clipboard")    