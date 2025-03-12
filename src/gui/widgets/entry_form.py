from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QToolButton, QGroupBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QClipboard, QGuiApplication

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
        category_layout = QHBoxLayout()
        self.category = QComboBox()
        self.category.setEditable(False)
        category_layout.addWidget(self.category)
        
        # Refresh categories button
        self.refresh_categories_btn = QToolButton()
        self.refresh_categories_btn.setText("⟳")
        self.refresh_categories_btn.setToolTip("Refresh Categories")
        self.refresh_categories_btn.clicked.connect(self.load_categories)
        category_layout.addWidget(self.refresh_categories_btn)
        
        form_layout.addRow("Category:", category_layout)
        
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
        
        # Add a progress bar for loading operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # Set initial state
        self.set_mode("view")
        
        # Load categories
        self.load_categories()
        
        # Initialize current_category
        self.current_category_id = None

    @async_callback
    async def load_categories(self):
        """Load categories from server"""
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            print("API client not available")
            return
        
        try:
            # Show loading
            self.show_loading(True)
            
            # Clear existing categories
            self.category.clear()
            
            # Add "None" option
            self.category.addItem("None", None)
            
            # Get categories from server
            categories = await self.api_client.list_categories()
            
            # Add categories to combo box
            for category in categories:
                self.category.addItem(category['name'], category['id'])
            
        except Exception as e:
            print(f"Error loading categories: {str(e)}")
        finally:
            self.show_loading(False)
    
    def set_mode(self, mode: str):
        """Set the form mode (view, add, edit)"""
        print(f"Setting form mode to: {mode}")
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

    def get_entry_data(self) -> dict:
        """Get form data as dictionary"""
        title = self.title.text().strip()
        print(f"Getting form data - title: '{title}'")
        
        return {
            "title": title,
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "url": self.url.text().strip(),
            "category_id": self.category.currentData(),
            "category": self.category.currentText(),
            "notes": self.notes.toPlainText().strip()
        }
    
    @async_callback
    async def load_entry(self, entry_id: int, vault_locked: bool = False):
        """Load an entry by ID"""
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            self.show_error(Exception("API client not available"))
            return
        
        try:
            # Show loading
            self.show_loading(True)
            
            # Get entry from API
            entry = await self.api_client.get_entry(entry_id)
            
            # Store entry ID
            self.current_entry_id = entry_id
            
            # If vault is locked, show placeholder data
            if vault_locked:
                entry_data = {
                    "title": f"Entry {entry_id} (Locked)",
                    "username": "[Encrypted]",
                    "password": "[Encrypted]",
                    "url": "[Encrypted]",
                    "category": "Unknown",
                    "category_id": None,
                    "notes": "The vault is locked. Unlock it to view entry details.",
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat()
                }
            else:
                # Decrypt entry data
                from crypto.vault import get_vault
                vault = get_vault()
                try:
                    entry_data = vault.decrypt_entry(entry.encrypted_data)
                    entry_data['created_at'] = entry.created_at.isoformat()
                    entry_data['updated_at'] = entry.updated_at.isoformat()
                except Exception as e:
                    self.show_error(Exception(f"Failed to decrypt entry: {str(e)}"))
                    return
            
            # Fill form fields
            self.title.setText(entry_data.get("title", ""))
            self.username.setText(entry_data.get("username", ""))
            self.password.setText(entry_data.get("password", ""))
            self.url.setText(entry_data.get("url", ""))
            
            # Set category if exists
            if 'category_id' in entry_data and entry_data['category_id'] is not None:
                category_data = {
                    'id': entry_data['category_id'],
                    'name': entry_data.get('category', '')
                }
                self.set_category(category_data)
            else:
                # Default to "None"
                self.category.setCurrentIndex(0)
            
            self.notes.setText(entry_data.get("notes", ""))
            
            # Set metadata
            self.created_label.setText(entry_data.get("created_at", ""))
            self.updated_label.setText(entry_data.get("updated_at", ""))
            
            # Set mode to view
            self.set_mode("view")
            
        except APIError as e:
            self.show_error(e)
        except Exception as e:
            self.show_error(e)
        finally:
            self.show_loading(False)

    def set_category(self, category_data: dict):
        """Set the category selection"""
        if not category_data or 'id' not in category_data:
            # Set to "None"
            self.category.setCurrentIndex(0)
            return
        
        # Find and select the category
        category_id = category_data['id']
        for i in range(self.category.count()):
            if self.category.itemData(i) == category_id:
                self.category.setCurrentIndex(i)
                return
        
        # If not found, add it
        if 'name' in category_data:
            self.category.addItem(category_data['name'], category_data['id'])
            self.category.setCurrentIndex(self.category.count() - 1)
    
    @async_callback
    async def save_entry(self, *args):
        """Save the current entry"""
        if not self.api_client:
            # Get API client from parent if not provided
            self.api_client = self.parent().api_client if self.parent() and hasattr(self.parent(), 'api_client') else None
        
        if not self.api_client:
            self.show_error(Exception("API client not available"))
            return
        
        # Validate required fields
        if not self.title.text().strip():
            self.show_error(Exception("Title is required"))
            self.title.setFocus()
            return
        
        try:
            # Show loading
            self.show_loading(True)
            
            # Get entry data
            entry_data = self.get_entry_data()
            
            # Debug
            print(f"Saving entry with mode: {self.current_mode}, ID: {self.current_entry_id}")
            print(f"Entry data: {entry_data}")
            
            if self.current_mode == "add" or not self.current_entry_id:
                # Create new entry
                result = await self.api_client.create_entry(entry_data)
                self.current_entry_id = result.id
                self.show_success("Entry created successfully")
                print(f"Created new entry with ID: {self.current_entry_id}")
            else:
                # Update existing entry
                print(f"Updating entry {self.current_entry_id}")
                result = await self.api_client.update_entry(self.current_entry_id, entry_data)
                print(f"Update result: {result}")
                self.show_success("Entry updated successfully")
            
            # Switch to view mode
            self.set_mode("view")
            
            # Emit saved signal
            self.saved.emit(self.current_entry_id)
            
            # Trigger a complete refresh in the parent VaultView
            parent = self.parent()
            if parent and hasattr(parent, 'refresh_data'):
                print("Triggering full refresh after save")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, parent.refresh_data)
            
        except APIError as e:
            self.show_error(e)
        except Exception as e:
            print(f"Error saving entry: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_error(e)
        finally:
            self.show_loading(False)
    
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
            # Show loading
            self.show_loading(True)
            
            # Delete entry from API
            print(f"Deleting entry {self.current_entry_id}")
            result = await self.api_client.delete_entry(self.current_entry_id)
            print(f"Delete result: {result}")
            
            # Store the ID before clearing
            deleted_id = self.current_entry_id
            
            # Clear form
            self.clear()
            
            # Emit deleted signal with the ID
            self.deleted.emit(deleted_id)
            
            # Show success message
            QMessageBox.information(self, "Success", "Entry deleted successfully")
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {str(e)}")
        finally:
            self.show_loading(False)

    def show_error(self, error: Exception):
        """Display error message with appropriate styling"""
        title = "Error"
        message = str(error)
        
        # Show error message
        QMessageBox.critical(self, title, message)
    
    def show_success(self, message: str):
        """Display success message"""
        QMessageBox.information(self, "Success", message)
        
    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show:
            self.progress_bar.setRange(0, 0)  # Infinite progress
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
            self.progress_bar.setRange(0, 100)  # Reset to normal range