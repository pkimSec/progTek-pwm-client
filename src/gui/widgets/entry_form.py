from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QToolButton, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from gui.widgets.password_generator import PasswordGenerator
from gui.widgets.strength_meter import PasswordStrengthMeter
from api.client import APIClient
from api.models import APIError, PasswordEntry
from utils.async_utils import async_callback
import json
import base64
import time

class EntryForm(QWidget):
    """Widget for editing password entries"""
    
    # Signals
    saved = pyqtSignal(int)  # Emitted when entry is saved (with entry ID)
    deleted = pyqtSignal(int)  # Emitted when entry is deleted (with entry ID)
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.current_entry_id = None
        self.current_mode = "view"  # "view", "add", "edit"
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Form group
        form_group = QGroupBox("Entry Details")
        form_layout = QFormLayout()
        
        # Title field
        self.title = QLineEdit()
        self.title.setPlaceholderText("Enter title")
        form_layout.addRow("Title:", self.title)
        
        # Username field
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter username or email")
        form_layout.addRow("Username:", self.username)
        
        # Password field
        password_layout = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password)
        
        # Toggle password visibility
        self.toggle_password_btn = QToolButton()
        self.toggle_password_btn.setText("👁️")
        self.toggle_password_btn.setCheckable(True)
        self.toggle_password_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_btn)
        
        # Generate password button
        self.generate_password_btn = QPushButton("Generate")
        self.generate_password_btn.clicked.connect(self.generate_password)
        password_layout.addWidget(self.generate_password_btn)
        
        form_layout.addRow("Password:", password_layout)
        
        # Password strength meter
        self.strength_meter = PasswordStrengthMeter()
        self.password.textChanged.connect(self.update_strength_meter)
        form_layout.addRow("Strength:", self.strength_meter)
        
        # URL field
        self.url = QLineEdit()
        self.url.setPlaceholderText("Enter website URL")
        form_layout.addRow("URL:", self.url)
        
        # Category field
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(["Business", "Finance", "Personal", "Social", "Email", "Shopping"])
        form_layout.addRow("Category:", self.category)
        
        # Notes field
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Enter notes")
        form_layout.addRow("Notes:", self.notes)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Metadata group (only shown in view/edit mode)
        self.metadata_group = QGroupBox("Metadata")
        metadata_layout = QFormLayout()
        
        self.created_label = QLabel()
        metadata_layout.addRow("Created:", self.created_label)
        
        self.updated_label = QLabel()
        metadata_layout.addRow("Updated:", self.updated_label)
        
        self.metadata_group.setLayout(metadata_layout)
        main_layout.addWidget(self.metadata_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Add/Edit buttons (right side)
        edit_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        edit_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_entry)
        edit_layout.addWidget(self.save_btn)
        
        # View buttons (left side)
        view_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.start_edit)
        view_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.confirm_delete)
        view_layout.addWidget(self.delete_btn)
        
        # Add to button layout
        button_layout.addLayout(view_layout)
        button_layout.addStretch()
        button_layout.addLayout(edit_layout)
        
        main_layout.addLayout(button_layout)
        
        # Set initial state
        self.set_mode("view")
    
    def set_mode(self, mode: str):
        """Set the form mode (view, add, edit)"""
        self.current_mode = mode
        
        # Set read-only based on mode
        read_only = (mode == "view")
        self.title.setReadOnly(read_only)
        self.username.setReadOnly(read_only)
        self.password.setReadOnly(read_only)
        self.url.setReadOnly(read_only)
        self.category.setEnabled(not read_only)
        self.notes.setReadOnly(read_only)
        
        # Show/hide buttons based on mode
        if mode == "view":
            # Show view buttons, hide edit buttons
            self.edit_btn.setVisible(True)
            self.delete_btn.setVisible(True)
            self.cancel_btn.setVisible(False)
            self.save_btn.setVisible(False)
            
            # Show metadata
            self.metadata_group.setVisible(True)
            
            # Hide password generator button
            self.generate_password_btn.setVisible(False)
            
        elif mode in ["add", "edit"]:
            # Show edit buttons, hide view buttons
            self.edit_btn.setVisible(False)
            self.delete_btn.setVisible(False)
            self.cancel_btn.setVisible(True)
            self.save_btn.setVisible(True)
            
            # Show metadata only in edit mode, not add mode
            self.metadata_group.setVisible(mode == "edit")
            
            # Show password generator button
            self.generate_password_btn.setVisible(True)
    
    def clear(self):
        """Clear all form fields"""
        self.title.clear()
        self.username.clear()
        self.password.clear()
        self.url.clear()
        self.category.setCurrentIndex(0)
        self.notes.clear()
        self.created_label.clear()
        self.updated_label.clear()
        self.current_entry_id = None
    
    def toggle_password_visibility(self, visible: bool):
        """Toggle password field visibility"""
        self.password.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
    
    def generate_password(self):
        """Show password generator dialog"""
        generator = PasswordGenerator(self)
        if generator.exec() == generator.DialogCode.Accepted:
            # Set generated password
            self.password.setText(generator.generated_password)
            # Update strength meter
            self.update_strength_meter()
    
    def update_strength_meter(self):
        """Update password strength meter"""
        self.strength_meter.update_strength(self.password.text())
    
    def start_edit(self):
        """Switch to edit mode"""
        self.set_mode("edit")
    
    def cancel_edit(self):
        """Cancel editing and return to view mode"""
        if self.current_entry_id:
            # Return to view mode for existing entry
            self.set_mode("view")
            # Reload entry to discard changes
            self.load_entry(self.current_entry_id)
        else:
            # Clear form for new entry
            self.clear()
    
    def confirm_delete(self):
        """Confirm before deleting an entry"""
        if not self.current_entry_id:
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_entry()
    
    @async_callback
    async def load_entry(self, entry_id: int, master_password: str = None):
        """Load an entry by ID"""
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            QMessageBox.critical(self, "Error", "API client not available")
            return
        
        try:
            # Get entry from API
            entry = await self.api_client.get_entry(entry_id)
            
            # Store entry ID
            self.current_entry_id = entry_id
            
            # Parse encrypted data (this would normally be decrypted)
            # For prototype purposes, we use dummy data
            entry_data = {
                "title": f"Entry {entry_id}",
                "username": "user@example.com",
                "password": "password123",
                "url": "https://example.com",
                "category": "Personal",
                "notes": "This is a sample entry",
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            }
            
            # Fill form fields
            self.title.setText(entry_data.get("title", ""))
            self.username.setText(entry_data.get("username", ""))
            self.password.setText(entry_data.get("password", ""))
            self.url.setText(entry_data.get("url", ""))
            
            # Set category if exists
            category = entry_data.get("category", "")
            index = self.category.findText(category)
            if index >= 0:
                self.category.setCurrentIndex(index)
            else:
                self.category.setCurrentText(category)
            
            self.notes.setText(entry_data.get("notes", ""))
            
            # Set metadata
            self.created_label.setText(entry_data.get("created_at", ""))
            self.updated_label.setText(entry_data.get("updated_at", ""))
            
            # Set mode to view
            self.set_mode("view")
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to load entry: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load entry: {str(e)}")
    
    @async_callback
    async def save_entry(self):
        """Save the current entry"""
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            QMessageBox.critical(self, "Error", "API client not available")
            return
        
        # Validate required fields
        if not self.title.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required")
            self.title.setFocus()
            return
        
        # Get entry data
        entry_data = {
            "title": self.title.text().strip(),
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "url": self.url.text().strip(),
            "category": self.category.currentText().strip(),
            "notes": self.notes.toPlainText().strip(),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        try:
            # In a real implementation, we would encrypt the data here
            # For prototype purposes, we just encode as JSON
            encrypted_data = json.dumps(entry_data)
            
            if self.current_mode == "add":
                # Create new entry
                result = await self.api_client.create_entry(encrypted_data)
                self.current_entry_id = result.id
                QMessageBox.information(self, "Success", "Entry created successfully")
            else:
                # Update existing entry
                await self.api_client.update_entry(self.current_entry_id, encrypted_data)
                QMessageBox.information(self, "Success", "Entry updated successfully")
            
            # Switch to view mode
            self.set_mode("view")
            
            # Emit saved signal
            self.saved.emit(self.current_entry_id)
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to save entry: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save entry: {str(e)}")
    
    @async_callback
    async def delete_entry(self):
        """Delete the current entry"""
        if not self.current_entry_id:
            return
        
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            QMessageBox.critical(self, "Error", "API client not available")
            return
        
        try:
            # Delete entry from API
            await self.api_client.delete_entry(self.current_entry_id)
            
            # Clear form
            self.clear()
            
            # Emit deleted signal
            self.deleted.emit(self.current_entry_id)
            
            # Show success message
            QMessageBox.information(self, "Success", "Entry deleted successfully")
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {str(e)}")