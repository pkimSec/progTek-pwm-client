from PyQt6.QtWidgets import (  
    QListWidget, QListWidgetItem, QMenu, QAbstractItemView,  
    QVBoxLayout, QLabel, QWidget, QHBoxLayout, QPushButton,
    QLineEdit, QComboBox, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QColor, QFont

from api.client import APIClient
from api.models import PasswordEntry
from crypto.vault import get_vault
from utils.async_utils import async_callback
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class EntryListItem(QListWidgetItem):
    """Custom list widget item for password entries"""
    
    def __init__(self, entry: PasswordEntry, decrypted_data: Optional[Dict] = None):
        super().__init__()
        self.entry_id = entry.id
        self.entry_data = entry
        self.decrypted_data = decrypted_data
        self._reload_task = None  # Track ongoing reloads
        
        # Extract information from decrypted data if available
        if decrypted_data:
            self.title = decrypted_data.get('title', f'Entry {entry.id}')
            self.username = decrypted_data.get('username', '')
            self.url = decrypted_data.get('url', '')
            self.category = decrypted_data.get('category', '')
            self.notes = decrypted_data.get('notes', '')
            self.password = decrypted_data.get('password', '')
        else:
            # Placeholder information
            self.title = f'Entry {entry.id}'
            self.username = ''
            self.url = ''
            self.category = ''
            self.notes = ''
            self.password = ''
        
        # Format timestamps
        try:
            self.created_at = entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
        except:
            self.created_at = 'Unknown'
            
        try:
            self.updated_at = entry.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        except:
            self.updated_at = 'Unknown'
        
        # Set display properties
        self.setText(self.title)
        self.setToolTip(f"Username: {self.username}\nURL: {self.url}\nCategory: {self.category}\nUpdated: {self.updated_at}")
        
        # Store entry data for filtering and sorting
        self.setSizeHint(QSize(100, 40))  # Make items taller for better readability

class EntryList(QWidget):
    """Widget for displaying password entries"""
    
    # Signal emitted when an entry is selected
    entry_selected = pyqtSignal(int)
    
    # Signal emitted when a new entry is requested
    new_entry_requested = pyqtSignal()
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.entries = {}  # Dictionary to track entries by ID
        self.current_category_id = None
        self.current_category_name = "All Items"
        self.current_filter = ""
        self.current_sort_field = "title"
        self.current_sort_order = Qt.SortOrder.AscendingOrder
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header without add button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Category label
        self.category_label = QLabel("All Items")
        self.category_label.setStyleSheet("font-weight: bold;")
        self.category_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header_layout.addWidget(self.category_label)
        
        # Sort combo box
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Title", "Username", "Updated"])
        self.sort_combo.setToolTip("Sort by")
        self.sort_combo.setMaximumWidth(100)
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        header_layout.addWidget(self.sort_combo)
        
        # Sort order button
        self.sort_order_btn = QPushButton("▲")
        self.sort_order_btn.setToolTip("Sort Order")
        self.sort_order_btn.setMaximumWidth(24)
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        header_layout.addWidget(self.sort_order_btn)
        
        layout.addLayout(header_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Entry count
        self.count_label = QLabel("0 entries")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.count_label)
        
        # Create list widget
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemClicked.connect(self.on_item_clicked)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list)
        
        # Add button at bottom
        bottom_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Entry")
        self.add_btn.setToolTip("Add Entry")
        self.add_btn.clicked.connect(self.new_entry_requested.emit)
        bottom_layout.addWidget(self.add_btn)
        layout.addLayout(bottom_layout)
    
    def load_entries_sync(self):
        """Synchronous wrapper for load_entries that doesn't require await"""
        # Get a fresh reference to the API client if needed
        if not self.api_client and hasattr(self, 'parent') and self.parent():
            parent = self.parent()
            if hasattr(parent, 'api_client') and parent.api_client:
                self.api_client = parent.api_client
                
            # Also ensure user_session is attached
            if hasattr(parent, 'user_session') and parent.user_session:
                if not hasattr(self.api_client, 'user_session'):
                    self.api_client.user_session = parent.user_session
                    
        # Call the async method directly - @async_callback will handle the execution
        try:
            self.load_entries()
        except Exception as e:
            print(f"Error in load_entries_sync: {str(e)}")
            import traceback
            traceback.print_exc()

    @async_callback
    async def load_entries(self):
        """Load all password entries from server"""
        try:
            self.list.setVisible(False)
            
            # Ensure we have an API client
            if not self.api_client and hasattr(self, 'parent'):
                parent = self.parent()
                while parent and not hasattr(parent, 'api_client'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'api_client'):
                    self.api_client = parent.api_client
                    print(f"Got api_client from parent: {self.api_client}")
                    
                    # Get user_session too if available
                    if hasattr(parent, 'user_session') and not hasattr(self.api_client, 'user_session'):
                        self.api_client.user_session = parent.user_session
                        print(f"Associated user_session with api_client in load_entries")
            
            if not self.api_client:
                print("No API client available, cannot load entries")
                self.status_label.setText("Error: No API client available")
                return
                
            print(f"Loading entries using API client at {self.api_client.endpoints.base_url}")
            
            # Make sure session token is present in headers
            if hasattr(self.api_client, '_session_token') and self.api_client._session_token:
                print(f"Using session token: {self.api_client._session_token}")
            else:
                print("Warning: No session token available")
                
            # Get entries from server
            entries = await self.api_client.list_entries()
            print(f"Retrieved {len(entries)} entries from server")
            
            # Process entries
            await self.process_entries(entries)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error loading entries: {str(e)}")
    
    async def process_entries(self, entries: list[PasswordEntry]):
        """Process entries after loading from server"""
        try:
            # Keep track of the previously selected entry ID
            selected_items = self.list.selectedItems()
            previously_selected_id = None
            if selected_items and hasattr(selected_items[0], 'entry_id'):
                previously_selected_id = selected_items[0].entry_id
            
            # Clear entry list UI but keep a copy of old entries for comparison
            old_entries = self.entries.copy()
            self.list.clear()
            
            # Important: Don't immediately clear entries dict
            # We'll replace it with new data only if decryption is successful
            new_entries = {}
            
            # Get vault instance
            vault = get_vault()
            if not vault.is_unlocked():
                print("Vault locked, attempting to unlock...")
                # Try to find master password and salt
                master_password = None
                vault_salt = None
                
                # Get from API client if available
                if hasattr(self, 'api_client') and self.api_client:
                    master_password = self.api_client._master_password
                    if hasattr(self.api_client, 'user_session') and self.api_client.user_session:
                        vault_salt = self.api_client.user_session.vault_salt
                        print(f"Got vault_salt from api_client.user_session: {bool(vault_salt)}")
                
                # Try unlocking if we have both
                if master_password and vault_salt:
                    print(f"Attempting to unlock vault with retrieved credentials")
                    if vault.unlock(master_password, vault_salt):
                        print("Successfully unlocked vault during process_entries")
                    else:
                        print("Failed to unlock vault during process_entries")
                        self.status_label.setText("Vault is locked. Cannot display entries.")
                        return
                else:
                    print(f"Missing vault unlock params - master_password: {bool(master_password)}, vault_salt: {bool(vault_salt)}")
                    self.status_label.setText("Vault is locked. Cannot display entries.")
                    return
                    
            # Process each entry
            successful_entries = 0
            entry_ids_processed = set()
            decryption_failures = 0
            
            for entry in entries:
                try:
                    entry_id = entry.id
                    entry_ids_processed.add(entry_id)
                    print(f"Processing entry {entry_id}, encrypted_data length: {len(entry.encrypted_data)}")
                    
                    # Try to decrypt
                    decrypted_data = None
                    
                    # First try to get from existing entries if the encrypted data hasn't changed
                    if entry_id in old_entries:
                        old_item, old_entry, old_decrypted = old_entries[entry_id]
                        if old_entry.encrypted_data == entry.encrypted_data and old_decrypted is not None:
                            print(f"Using cached decryption for entry {entry_id}")
                            decrypted_data = old_decrypted
                    
                    # If not found in cache, decrypt
                    if decrypted_data is None:
                        try:
                            # Before attempting decryption, make sure vault is in proper state
                            if not vault.is_unlocked():
                                raise ValueError("Vault locked before decryption attempt")
                                
                            decrypted_data = vault.decrypt_entry(entry.encrypted_data)
                            print(f"Successfully decrypted entry {entry_id}: {decrypted_data.get('title', 'Unknown')}")
                            
                            # Validate decrypted data has required fields
                            if 'title' not in decrypted_data or not decrypted_data['title']:
                                print(f"Warning: Entry {entry_id} has no title, using default")
                                decrypted_data['title'] = f"Entry {entry_id}"
                                
                            successful_entries += 1
                        except Exception as decrypt_err:
                            print(f"Error decrypting entry {entry_id}: {decrypt_err}")
                            import traceback
                            traceback.print_exc()
                            decryption_failures += 1
                            
                            # Try to restore from previous data if available
                            if entry_id in old_entries and old_entries[entry_id][2] is not None:
                                print(f"Using previous decryption data for entry {entry_id}")
                                decrypted_data = old_entries[entry_id][2]
                                successful_entries += 1
                    else:
                        successful_entries += 1
                    
                    # Create list item with decrypted data
                    item = EntryListItem(entry, decrypted_data)
                    self.list.addItem(item)
                    new_entries[entry_id] = (item, entry, decrypted_data)
                    
                    # If this was previously selected, reselect it
                    if entry_id == previously_selected_id:
                        self.list.setCurrentItem(item)
                    
                except Exception as e:
                    print(f"Error processing entry {entry.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Add with minimal data
                    item = EntryListItem(entry)
                    self.list.addItem(item)
                    new_entries[entry_id] = (item, entry, None)
            
            # Check for any entries that were removed from the server
            removed_entries = set(old_entries.keys()) - entry_ids_processed
            if removed_entries:
                print(f"Detected {len(removed_entries)} entries removed from server: {removed_entries}")
            
            # Check if decryption was mostly successful 
            if successful_entries > 0 and decryption_failures < len(entries) / 2:
                # Update with new entries
                self.entries = new_entries
                print(f"Processed {successful_entries} entries successfully out of {len(entries)}")
            else:
                # If we had more failures than successes, keep the old entries
                print(f"WARNING: Too many decryption failures ({decryption_failures}/{len(entries)}), keeping previous data")
                if old_entries:
                    self.entries = old_entries
                    # Rebuild entry list with old entries
                    self.list.clear()
                    for entry_id, (old_item, old_entry, old_data) in old_entries.items():
                        item = EntryListItem(old_entry, old_data)
                        self.list.addItem(item) 
                        # Restore selection
                        if entry_id == previously_selected_id:
                            self.list.setCurrentItem(item)
                else:
                    # If we had no previous entries, use what we have
                    self.entries = new_entries
            
            # Make sure the list is visible if we have entries
            if len(self.entries) > 0:
                print(f"Making list visible with {len(self.entries)} entries")
                self.list.setVisible(True)
                self.status_label.setVisible(False)
                
                # Force a layout update
                self.list.update()
                
                # Show count
                if hasattr(self, 'count_label'):
                    self.count_label.setText(f"{len(self.entries)} entries")
                    self.count_label.setVisible(True)
            else:
                self.list.setVisible(True)  # Always keep list visible
                
            # Apply filters in a reliable manner
            self.apply_filters(force_visibility=True)
            
        except Exception as e:
            print(f"Error processing entries: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error processing entries: {str(e)}")
    
    def on_item_clicked(self, item: EntryListItem):
        """Handle item click - emit entry selected signal"""
        if hasattr(item, 'entry_id'):
            self.entry_selected.emit(item.entry_id)
    
    def show_context_menu(self, position):
        """Show context menu for entry management"""
        item = self.list.itemAt(position)
        if not item:
            return
        
        # Create menu
        menu = QMenu(self)
        
        # View action
        view_action = QAction("View", self)
        view_action.triggered.connect(lambda: self.on_item_clicked(item))
        menu.addAction(view_action)
        
        # Edit action
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.on_item_clicked(item))
        menu.addAction(edit_action)
        
        # Copy username and password actions
        if hasattr(item, 'username') and item.username:
            menu.addSeparator()
            copy_username = QAction("Copy Username", self)
            copy_username.triggered.connect(lambda: self.copy_to_clipboard(item.username))
            menu.addAction(copy_username)
            
        if hasattr(item, 'password') and item.password:
            copy_password = QAction("Copy Password", self)
            copy_password.triggered.connect(lambda: self.copy_to_clipboard(item.password))
            menu.addAction(copy_password)
        
        # Delete action
        menu.addSeparator()
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_entry(item))
        menu.addAction(delete_action)
        
        menu.exec(self.list.viewport().mapToGlobal(position))
    
    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        from PyQt6.QtGui import QClipboard, QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        
        # Schedule clipboard clearing after timeout
        # This would be implemented in a more secure way in a real app
        QTimer.singleShot(30000, lambda: clipboard.clear())
    
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
            self.remove_entry(item.entry_id)
            
            # Update count
            self.update_count()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {str(e)}")
    
    def add_entry(self, entry: PasswordEntry, decrypted_data: Dict[str, Any]):
        """Add a new entry to the list"""
        # Create list item
        item = EntryListItem(entry, decrypted_data)
        
        # Add to dictionary
        self.entries[entry.id] = (item, entry, decrypted_data)
        
        # Add to list widget
        self.list.addItem(item)
        
        # Apply filters
        self.apply_filters()
        
        # Update count
        self.update_count()
        
        # Make list visible if it was hidden
        if self.empty_label.isVisible():
            self.empty_label.hide()
            self.list.show()
    
    def update_entry(self, entry_id: int, entry: PasswordEntry, decrypted_data: Dict[str, Any]):
        """Update an existing entry"""
        if entry_id not in self.entries:
            # New entry - add it
            self.add_entry(entry, decrypted_data)
            return
            
        # Get the existing item
        item, _, _ = self.entries[entry_id]
        
        # Update item data
        item.entry_data = entry
        item.decrypted_data = decrypted_data
        
        # Update displayed information
        item.title = decrypted_data.get('title', f'Entry {entry_id}')
        item.username = decrypted_data.get('username', '')
        item.url = decrypted_data.get('url', '')
        item.category = decrypted_data.get('category', '')
        item.notes = decrypted_data.get('notes', '')
        item.password = decrypted_data.get('password', '')
        
        try:
            item.updated_at = entry.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        except:
            item.updated_at = 'Unknown'
        
        # Update display
        item.setText(item.title)
        item.setToolTip(f"Username: {item.username}\nURL: {item.url}\nCategory: {item.category}\nUpdated: {item.updated_at}")
        
        # Update stored entry
        self.entries[entry_id] = (item, entry, decrypted_data)
        
        # Apply filters and sort
        self.apply_filters()

    def remove_entry(self, entry_id: int):
        """Remove an entry from the list"""
        print(f"Removing entry {entry_id} from list")
        if entry_id in self.entries:
            # Get the item
            item, _, _ = self.entries[entry_id]
            
            # Remove from list widget
            row = self.list.row(item)
            if row >= 0:  # Make sure the item exists in the list
                self.list.takeItem(row)
                print(f"Removed entry {entry_id} from list widget at row {row}")
            
            # Remove from dictionary
            del self.entries[entry_id]
            print(f"Removed entry {entry_id} from entries dictionary")
            
            # Update count and visibility
            self.update_count()
        else:
            print(f"Entry {entry_id} not found in entries dictionary")
    
    def set_category(self, category_name: str, category_id: Optional[int]):
        """Set the current category filter"""
        print(f"Setting category filter: {category_name} (ID: {category_id})")
        
        # Store previous values to detect changes
        old_category_id = self.current_category_id
        old_category_name = self.current_category_name
        
        # Update current values
        self.current_category_id = category_id
        self.current_category_name = category_name
        
        # Update category label
        self.category_label.setText(category_name)
        
        # Special case for "All Items"
        if category_name == "All Items":
            print("ALL ITEMS selected - showing entries from all categories")
            # Simply make all entries visible
            for entry_id, (item, entry, _) in self.entries.items():
                item.setHidden(False)
            
            # Update count and sort
            self.update_count()
            self.apply_sort()
        else:
            # Apply filters for other categories
            self.apply_filters()
    
    def filter_entries(self, filter_text: str = None):
        """Filter entries by search text"""
        if filter_text is not None:
            self.current_filter = filter_text.lower()
        
        self.apply_filters()
    
    def apply_filters(self, force_visibility=False):
        """Apply current filters and sort to the entries"""
        visible_count = 0
        
        # Special case for "All Items" - show everything
        is_all_items_view = (self.current_category_name == "All Items")
        
        print(f"Applying filters - Category: '{self.current_category_name}', All Items view: {is_all_items_view}")
        
        # Loop through all entries
        for entry_id, (item, entry, decrypted_data) in self.entries.items():
            if force_visibility:
                # Override filter logic and make all items visible
                item.setHidden(False)
                visible_count += 1
                continue
                
            # Start with item visible
            visible = True
            
            # Skip category filtering for "All Items" view
            if not is_all_items_view and self.current_category_id is not None and decrypted_data:
                # Check if entry belongs to category
                entry_category_id = decrypted_data.get('category_id')
                if entry_category_id != self.current_category_id:
                    visible = False
            
            # Apply text filter
            if self.current_filter:
                # Check if entry matches filter text
                match_found = False
                
                if decrypted_data:
                    # Check title, username, URL, and notes
                    fields_to_check = [
                        decrypted_data.get('title', ''),
                        decrypted_data.get('username', ''),
                        decrypted_data.get('url', ''),
                        decrypted_data.get('notes', '')
                    ]
                    
                    for field in fields_to_check:
                        if field and self.current_filter.lower() in field.lower():
                            match_found = True
                            break
                else:
                    # Fall back to item's displayed text
                    if self.current_filter.lower() in item.text().lower():
                        match_found = True
                
                if not match_found:
                    visible = False
            
            # Set item visibility
            item.setHidden(not visible)
            
            if visible:
                visible_count += 1
        
        print(f"Filter applied: {visible_count} of {len(self.entries)} entries visible")
        
        # Update count and ensure list stays visible
        self.list.setVisible(True)  # Always keep list visible
        
        # Apply sort
        self.apply_sort()
        
        # Update count
        self.update_count()

    def reload_all_entries(self, force_display=True):
        """Completely reload all entries from scratch"""
        print("Performing complete entry reload")
        
        try: 
            # Cancel any ongoing operations
            if hasattr(self, '_reload_task') and self._reload_task:
                print("Cancelling previous reload task")
                self._reload_task = None
            
            # Get a fresh API client if needed
            if not self.api_client and hasattr(self, 'parent'):
                parent = self.parent()
                if hasattr(parent, 'api_client'):
                    self.api_client = parent.api_client
                    
            if not self.api_client:
                self.status_label.setText("No API client available")
                return
            
            # Mark this as an active task
            self._reload_task = True
            
            # Capture selected entry ID before clearing
            selected_items = self.list.selectedItems()
            previously_selected_id = None
            if selected_items and hasattr(selected_items[0], 'entry_id'):
                previously_selected_id = selected_items[0].entry_id
                print(f"Saving selection state for entry: {previously_selected_id}")
            
            # Clear the list UI but don't clear entries dictionary yet
            # (entries will be cleared in process_entries)
            self.list.clear()
            
            # Load the entries through the load_entries_sync method
            self.load_entries_sync()
            
            # Force display if requested, with a delay to ensure entries are loaded
            if force_display:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.force_display_refresh)
            
            # Restore selection if possible, with a delay
            if previously_selected_id is not None:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(600, lambda: self.restore_selection(previously_selected_id))
        
        except Exception as e:
            print(f"Error in reload_all_entries: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
        finally:
            # Clear the task flag
            self._reload_task = None
            
            # Make sure count is updated with a delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(700, self.update_count)

    def restore_selection(self, entry_id):
        """Restore selection to previously selected entry"""
        try:
            if entry_id in self.entries:
                item, _, _ = self.entries[entry_id]
                self.list.setCurrentItem(item)
                print(f"Restored selection to entry: {entry_id}")
                
                # Emit selection signal to update the form
                self.entry_selected.emit(entry_id)
        except Exception as e:
            print(f"Error restoring selection: {str(e)}")
    
    def on_sort_changed(self, sort_field: str):
        """Handle sort field change"""
        field_map = {
            "Title": "title",
            "Username": "username",
            "Updated": "updated_at"
        }
        
        self.current_sort_field = field_map.get(sort_field, "title")
        self.apply_sort()
    
    def toggle_sort_order(self):
        """Toggle sort order between ascending and descending"""
        if self.current_sort_order == Qt.SortOrder.AscendingOrder:
            self.current_sort_order = Qt.SortOrder.DescendingOrder
            self.sort_order_btn.setText("▼")
        else:
            self.current_sort_order = Qt.SortOrder.AscendingOrder
            self.sort_order_btn.setText("▲")
        
        self.apply_sort()
    
    def apply_sort(self):
        """Apply current sort settings to the list reliably"""
        try:
            # Special case for empty list
            if self.list.count() == 0:
                return
                
            # Save currently selected item reference
            current_item = self.list.currentItem()
            current_id = None
            if current_item and hasattr(current_item, "entry_id"):
                current_id = current_item.entry_id
                
            # Create mapping of all items for stable sort
            items_map = {}
            for i in range(self.list.count()):
                item = self.list.item(i)
                if item and hasattr(item, "entry_id"):
                    items_map[item.entry_id] = item
            
            # Create list of visible items only
            visible_items = []
            for i in range(self.list.count()):
                item = self.list.item(i)
                if item and not item.isHidden() and hasattr(item, "entry_id"):
                    visible_items.append(item)
                    
            if not visible_items:
                return  # No visible items to sort
                
            # Define sort key function based on current sort field
            def get_sort_key(item):
                if not hasattr(item, "entry_id"):
                    return ""  # Fallback for invalid items
                    
                entry_id = item.entry_id
                
                # Get entry data from dictionary
                if entry_id in self.entries:
                    _, _, decrypted_data = self.entries[entry_id]
                    
                    # Use decrypted data if available
                    if decrypted_data is not None:
                        if self.current_sort_field == "title":
                            return decrypted_data.get("title", "").lower()
                        elif self.current_sort_field == "username":
                            return decrypted_data.get("username", "").lower()
                        elif self.current_sort_field == "updated_at":
                            return decrypted_data.get("updated_at", "")
                
                # Fallback to item text
                return item.text().lower()
                
            # Sort the visible items
            visible_items.sort(
                key=get_sort_key,
                reverse=(self.current_sort_order == Qt.SortOrder.DescendingOrder)
            )
            
            # Take all items without deleting them
            all_items = []
            for i in range(self.list.count()):
                all_items.append(self.list.takeItem(0))
                
            # Create a new ordering with visible items first, then hidden items
            new_order = []
            
            # First add the visible items in sorted order
            visible_ids = set(item.entry_id for item in visible_items if hasattr(item, "entry_id"))
            new_order.extend(visible_items)
            
            # Then add all hidden items in their original order
            for item in all_items:
                if item and hasattr(item, "entry_id") and item.entry_id not in visible_ids:
                    new_order.append(item)
            
            # Add items back to the list in new order
            for item in new_order:
                self.list.addItem(item)
                
            # Restore selection if possible
            if current_id is not None:
                for i in range(self.list.count()):
                    item = self.list.item(i)
                    if item and hasattr(item, "entry_id") and item.entry_id == current_id:
                        self.list.setCurrentItem(item)
                        break
                        
        except Exception as e:
            print(f"Error during sorting: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_count(self):
        """Update the entry count label"""
        visible_count = 0
        total_count = self.list.count()
        
        # Count visible items
        for i in range(total_count):
            if not self.list.item(i).isHidden():
                visible_count += 1
        
        # Update label
        if visible_count != total_count:
            self.count_label.setText(f"{visible_count} of {total_count} entries")
        else:
            self.count_label.setText(f"{total_count} entries")
        
        # Ensure the list and count label are visible if we have entries
        if total_count > 0:
            print(f"Making list visible with {total_count} entries")
            self.count_label.setVisible(True)
            self.list.setVisible(True)
            # No more empty_label to hide
        else:
            print("No entries to display")
            # Always keep list visible, even when empty
            self.list.setVisible(True)

    def force_display_refresh(self):
        """Force a refresh of the display"""
        print("Forcing display refresh...")
        
        try:
            # Make sure the list is visible
            self.list.setVisible(True)
            self.status_label.setVisible(False)
            
            # Make sure all items are visible (unless filtered)
            visible_count = 0
            for i in range(self.list.count()):
                item = self.list.item(i)
                item.setHidden(False)  # Start with all visible
                visible_count += 1
            
            print(f"Made {visible_count} entries visible")
            
            # Refresh count
            self.update_count()
            
            # Force a repaint
            self.list.repaint()
        except Exception as e:
            print(f"Error during force display refresh: {str(e)}")
            import traceback
            traceback.print_exc()