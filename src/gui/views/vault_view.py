from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSplitter, QMessageBox, QFrame,
    QToolBar, QLineEdit, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from api.client import APIClient
from api.models import PasswordEntry, APIError
from utils.session import UserSession
from utils.async_utils import async_callback
from crypto.vault import get_vault

from gui.widgets.category_tree import CategoryTree
from gui.widgets.entry_list import EntryList, EntryListItem 
from gui.widgets.entry_form import EntryForm

class VaultView(QWidget):
    """View for the password vault"""
    
    def __init__(self, api_client: APIClient, user_session: UserSession, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.user_session = user_session
        
        try:
            # Initialize UI components
            self.setup_ui()
            
            # Initialize components
            self.load_data()
        except Exception as e:
            print(f"Error initializing VaultView: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create basic UI with error message
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Error initializing vault view: {str(e)}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            
            # Add retry button
            retry_btn = QPushButton("Retry")
            retry_btn.clicked.connect(self.retry_initialization)
            layout.addWidget(retry_btn)

    def retry_initialization(self):
        """Retry initializing the view"""
        try:
            # Clear existing layout if any
            if self.layout():
                # Remove all widgets
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # Remove the layout
                old_layout = self.layout()
                QWidget().setLayout(old_layout)
            
            # Initialize UI components
            self.setup_ui()
            
            # Initialize components
            self.load_data()
            
        except Exception as e:
            print(f"Error during retry: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create basic UI with error message
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Error during retry: {str(e)}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            
            # Add retry button
            retry_btn = QPushButton("Retry")
            retry_btn.clicked.connect(self.retry_initialization)
            layout.addWidget(retry_btn)
            
        except Exception as e:
            print(f"Error during retry: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create basic UI with error message
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Error during retry: {str(e)}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            
            # Add retry button
            retry_btn = QPushButton("Retry")
            retry_btn.clicked.connect(self.retry_initialization)
            layout.addWidget(retry_btn)
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Toolbar
        self.toolbar = QToolBar()
        
        # Add entry button
        self.add_btn = QAction("Add Entry", self)
        self.add_btn.triggered.connect(self.add_entry)
        self.toolbar.addAction(self.add_btn)
        
        # Refresh button
        self.refresh_btn = QAction("Refresh", self)
        self.refresh_btn.triggered.connect(self.refresh_data)
        self.toolbar.addAction(self.refresh_btn)
        
        # Global search
        self.toolbar.addSeparator()
        search_label = QLabel("Search:")
        self.toolbar.addWidget(search_label)
        
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("Search all entries...")
        self.global_search.setClearButtonEnabled(True)
        self.global_search.setMinimumWidth(200)
        self.global_search.textChanged.connect(self.on_global_search)
        self.toolbar.addWidget(self.global_search)
        
        layout.addWidget(self.toolbar)
        
        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - category tree
        self.category_tree = CategoryTree(self.api_client)
        self.category_tree.category_selected.connect(self.on_category_selected)
        self.splitter.addWidget(self.category_tree)
        
        # Middle - entry list
        self.entry_list = EntryList(self.api_client)
        self.entry_list.entry_selected.connect(self.on_entry_selected)
        self.entry_list.new_entry_requested.connect(self.add_entry)
        self.splitter.addWidget(self.entry_list)
        
        # Right side - entry form
        self.entry_form = EntryForm(self.api_client)
        self.entry_form.saved.connect(self.on_entry_saved)
        self.entry_form.deleted.connect(self.on_entry_deleted)
        self.splitter.addWidget(self.entry_form)
        
        # Set initial sizes (categories:entries:form = 1:1:2)
        self.splitter.setSizes([100, 300, 400])
        
        layout.addWidget(self.splitter)
        
        # Status bar
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.entry_count_label = QLabel("0 entries")
        status_layout.addWidget(self.entry_count_label)
        
        layout.addLayout(status_layout)
    
    @async_callback
    async def load_data(self):
        """Load initial data"""
        try:
            # Use safe status update method
            self.safe_update_status("Loading vault data...")
            
            # First, make sure our API client has the user_session
            if hasattr(self, 'api_client') and hasattr(self, 'parent') and self.parent():
                parent = self.parent()
                if hasattr(parent, 'user_session') and parent.user_session:
                    self.api_client.user_session = parent.user_session
                    print(f"Associated user_session with api_client in load_data")
            
            # Check if entry_list is still valid
            if hasattr(self, 'entry_list') and self.entry_list:
                try:
                    # Use synchronous wrapper instead of awaiting
                    self.entry_list.load_entries_sync()
                    
                    # Update entry count after a delay to give entries time to load
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(1000, self.update_entry_count)
                except Exception as entry_error:
                    print(f"Error loading entries: {str(entry_error)}")
                    import traceback
                    traceback.print_exc()
                    self.safe_update_status(f"Error loading entries: {str(entry_error)}")
            else:
                print("Entry list is not available")
            
            self.safe_update_status("Ready")
            
        except Exception as e:
            print(f"Error in load_data: {str(e)}")
            import traceback
            traceback.print_exc()
            self.safe_update_status(f"Error: {str(e)}")

    def safe_update_status(self, message):
        """Update status label safely, handling potential widget deletion"""
        if hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(message)
            except RuntimeError:
                print(f"Cannot update status to '{message}' - label may have been deleted")
        else:
            print(f"Status: {message}")
    
    def update_entry_count(self):
        """Update the entry count label"""
        try:
            # Safely access the entries count
            if hasattr(self, 'entry_list') and hasattr(self.entry_list, 'entries'):
                count = len(self.entry_list.entries)
                
                if hasattr(self, 'entry_count_label') and self.entry_count_label:
                    self.entry_count_label.setText(f"{count} entries")
            else:
                print("Cannot update entry count - entry list not available")
        except RuntimeError:
            print("Cannot update entry count - label may have been deleted")
    
    def on_category_selected(self, category_name: str, category_id: int):
        """Handle category selection"""
        self.entry_list.set_category(category_name, category_id)
    
    def on_entry_selected(self, entry_id: int):
        """Handle entry selection"""
        # Check if entry exists
        if entry_id in self.entry_list.entries:
            # Get entry data
            item, entry, decrypted_data = self.entry_list.entries[entry_id]
            
            # If we couldn't decrypt it earlier, try again
            if decrypted_data is None:
                vault = get_vault()
                if vault.is_unlocked():
                    try:
                        decrypted_data = vault.decrypt_entry(entry.encrypted_data)
                    except Exception as e:
                        print(f"Error decrypting entry {entry_id}: {e}")
            
            # Load entry in form
            self.entry_form.load_entry(entry_id, vault_locked=(not get_vault().is_unlocked()))
    
    def on_entry_saved(self, entry_id: int):
        """Handle entry saved event"""
        # Refresh the entry in the list
        self.refresh_entry(entry_id)
        
        # Also force a full display refresh after a delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.entry_list.force_display_refresh() if hasattr(self.entry_list, 'force_display_refresh') else None)
    
    @async_callback
    async def refresh_entry(self, entry_id: int):
        """Refresh a specific entry"""
        try:
            # Ensure api_client has user_session attached
            if hasattr(self, 'user_session') and not hasattr(self.api_client, 'user_session'):
                self.api_client.user_session = self.user_session

            # Get entry from API
            entry = await self.api_client.get_entry(entry_id)
            
            # Decrypt entry
            vault = get_vault()
            if vault.is_unlocked():
                try:
                    decrypted_data = vault.decrypt_entry(entry.encrypted_data)
                    
                    # Update entry in list
                    self.entry_list.update_entry(entry_id, entry, decrypted_data)
                    
                except Exception as e:
                    print(f"Error decrypting entry {entry_id}: {e}")
            
        except Exception as e:
            print(f"Error refreshing entry {entry_id}: {e}")
    
    def on_entry_deleted(self, entry_id: int):
        """Handle entry deleted event"""
        # Entry was deleted, update UI
        if entry_id in self.entry_list.entries:
            # Get the list item
            item, _, _ = self.entry_list.entries[entry_id]
            
            # Remove from list
            self.entry_list.list.takeItem(self.entry_list.list.row(item))
            
            # Remove from entries dictionary
            del self.entry_list.entries[entry_id]
            
            # Update count
            self.entry_list.update_count()
            
            # Force refresh display
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.entry_list.force_display_refresh() if hasattr(self.entry_list, 'force_display_refresh') else None)
            
            # Clear form
            self.entry_form.clear()
    
    def add_entry(self):
        """Add a new entry"""
        from crypto.vault import get_vault
        vault = get_vault()
        
        # Make sure vault is unlocked
        if not vault.is_unlocked():
            # Try to unlock with user session data
            if hasattr(self, 'api_client'):
                # Get vault unlock params from user session
                master_password = self.api_client._master_password
                vault_salt = None
                
                # Try to get user_session either from api_client or parent
                if hasattr(self.api_client, 'user_session') and self.api_client.user_session:
                    vault_salt = self.api_client.user_session.vault_salt
                elif hasattr(self, 'parent') and self.parent():
                    if hasattr(self.parent(), 'user_session') and self.parent().user_session:
                        vault_salt = self.parent().user_session.vault_salt
                        # Also associate user_session with api_client if needed
                        if not hasattr(self.api_client, 'user_session'):
                            self.api_client.user_session = self.parent().user_session
                            print("Associated api_client with user_session in add_entry")
                
                if master_password and vault_salt:
                    print(f"Attempting to unlock vault before adding entry...")
                    if vault.unlock(master_password, vault_salt):
                        print("Successfully unlocked vault before adding entry")
                        # Continue with entry creation
                    else:
                        print("Failed to unlock vault with available credentials")
                        self.show_vault_locked_message()
                        return
                else:
                    print(f"Missing vault parameters - master_password: {bool(master_password)}, vault_salt: {bool(vault_salt)}")
                    self.show_vault_locked_message()
                    return
            else:
                print("No API client available, cannot add entry")
                self.show_vault_locked_message()
                return
        
        # Clear the form and set mode to add
        self.entry_form.clear()
        self.entry_form.set_mode("add")
        print("Set entry form mode to 'add'")
        
        # Set the current selected category
        if hasattr(self.entry_list, 'current_category_id') and self.entry_list.current_category_id:
            category_data = {
                'id': self.entry_list.current_category_id,
                'name': self.entry_list.current_category_name
            }
            self.entry_form.set_category(category_data)

    @async_callback
    async def delete_entry(self, item: EntryListItem):
        """Delete an entry"""
        if not hasattr(item, 'entry_id'):
            return
                
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Entry",
            "Are you sure you want to delete this entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
                
        try:
            # Call API to delete entry
            await self.api_client.delete_entry(item.entry_id)
            
            # Remove from local data and UI
            self.entry_list.remove_entry(item.entry_id)
            
            # Update count
            self.entry_list.update_count()
            
            # Check if list is now empty
            if self.entry_list.list.count() == 0:
                self.entry_list.empty_label.setText("No entries found")
                self.entry_list.empty_label.show()
                self.entry_list.list.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {str(e)}")

    def show_vault_locked_message(self):
        """Show message about vault being locked with options to unlock"""
        from PyQt6.QtWidgets import QMessageBox, QPushButton
        
        # Create custom message box with unlock button
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Vault Locked")
        msg_box.setText("The vault is locked. You need to unlock it before adding entries.")
        msg_box.setInformativeText("Would you like to unlock the vault now?")
        
        # Add custom buttons
        unlock_button = msg_box.addButton("Unlock Vault", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        # Check which button was clicked
        if msg_box.clickedButton() == unlock_button:
            self.unlock_vault_manually()
    
    def unlock_vault_manually(self):
        """Prompt user for master password and unlock vault"""
        from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
        from crypto.vault import get_vault
        
        # Ask for master password
        master_password, ok = QInputDialog.getText(
            self, 
            "Unlock Vault",
            "Enter your master password:",
            QLineEdit.EchoMode.Password
        )
        
        if ok and master_password:
            # Get salt from user session
            vault_salt = None
            if hasattr(self.user_session, 'vault_salt'):
                vault_salt = self.user_session.vault_salt
            
            if not vault_salt and hasattr(self.api_client, 'get_vault_salt'):
                # Try to get salt from server
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    vault_salt = loop.run_until_complete(self.api_client.get_vault_salt())
                    loop.close()
                    
                    # Store in user session if successful
                    if vault_salt and hasattr(self.user_session, 'set_vault_salt'):
                        self.user_session.set_vault_salt(vault_salt)
                except Exception as e:
                    print(f"Error getting vault salt: {e}")
            
            if vault_salt:
                # Try to unlock the vault
                vault = get_vault()
                if vault.unlock(master_password, vault_salt):
                    QMessageBox.information(
                        self,
                        "Vault Unlocked",
                        "The vault has been successfully unlocked."
                    )
                    # Store master password in API client for future use
                    if hasattr(self.api_client, 'set_master_password'):
                        self.api_client.set_master_password(master_password)
                else:
                    QMessageBox.critical(
                        self,
                        "Unlock Failed",
                        "Failed to unlock the vault. Please check your master password."
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Missing Vault Salt",
                    "Vault salt is not available. Please try logging out and back in."
                )

    def on_global_search(self, search_text: str):
        """Handle global search"""
        self.entry_list.filter_entries(search_text)
    
    def refresh_data(self):
        """Refresh all data - synchronous wrapper"""
        print("Refresh button clicked - performing full refresh")
        
        try:
            self.status_label.setText("Refreshing vault data...")
            
            # First make sure API client and user_session are properly linked
            if hasattr(self, 'api_client') and hasattr(self, 'parent') and self.parent():
                if hasattr(self.parent(), 'user_session') and not hasattr(self.api_client, 'user_session'):
                    self.api_client.user_session = self.parent().user_session
                    print("Linked user_session to api_client during refresh")
                    
            # Ensure the entry_list has the API client
            if hasattr(self, 'entry_list'):
                self.entry_list.api_client = self.api_client
                
                # Completely reload entries
                if hasattr(self.entry_list, 'reload_all_entries'):
                    self.entry_list.reload_all_entries(force_display=True)
                else:
                    self.entry_list.load_entries_sync()
                    
                # Schedule a display refresh
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self.entry_list.force_display_refresh() if hasattr(self.entry_list, 'force_display_refresh') else None)
                    
            # Also refresh categories
            print("Refreshing categories...")
            if hasattr(self, 'category_tree') and hasattr(self.category_tree, 'load_categories'):
                self.category_tree.load_categories()
                
            self.status_label.setText("Data refreshed successfully")
            
        except Exception as e:
            print(f"Error refreshing data: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")