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
from gui.widgets.entry_list import EntryList
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
            
            # Check if entry_list is still valid
            if hasattr(self, 'entry_list') and self.entry_list:
                try:
                    # Load entries
                    await self.entry_list.load_entries()
                    
                    # Update entry count
                    self.update_entry_count()
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
            try:
                QMessageBox.critical(self, "Error", f"Failed to load vault data: {str(e)}")
            except RuntimeError:
                print("Cannot show error message - widget may have been deleted")

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
    
    @async_callback
    async def refresh_entry(self, entry_id: int):
        """Refresh a specific entry"""
        try:
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
            self.update_entry_count()
            
            # Clear form
            self.entry_form.clear()
    
    def add_entry(self):
        """Add a new entry"""
        # Make sure vault is unlocked
        if not get_vault().is_unlocked():
            QMessageBox.warning(
                self,
                "Vault Locked",
                "The vault is locked. Please unlock it before adding entries."
            )
            return
        
        # Clear the form and set mode to add
        self.entry_form.clear()
        
        # Set the current selected category
        if hasattr(self.entry_list, 'current_category_id') and self.entry_list.current_category_id:
            category_data = {
                'id': self.entry_list.current_category_id,
                'name': self.entry_list.current_category_name
            }
            self.entry_form.set_category(category_data)
    
    def on_global_search(self, search_text: str):
        """Handle global search"""
        self.entry_list.filter_entries(search_text)
    
    @async_callback
    async def refresh_data(self):
        """Refresh all data"""
        try:
            self.status_label.setText("Refreshing vault data...")
            
            # Load entries
            await self.entry_list.load_entries()
            
            # Update entry count
            self.update_entry_count()
            
            self.status_label.setText("Data refreshed successfully")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")