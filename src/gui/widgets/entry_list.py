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
        
        # Header with add button and sorting options
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # New entry button
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Add Entry")
        self.add_btn.setMaximumWidth(24)
        self.add_btn.clicked.connect(self.new_entry_requested.emit)
        header_layout.addWidget(self.add_btn)
        
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
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entries...")
        self.search_box.textChanged.connect(self.filter_entries)
        layout.addWidget(self.search_box)
        
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
        
        # Empty state message
        self.empty_label = QLabel("No entries found")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; margin: 20px;")
        layout.addWidget(self.empty_label)
        self.empty_label.hide()
        
        # Status message
        self.status_label = QLabel("Loading entries...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
    
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
            self.status_label.setText("Loading entries...")
            self.status_label.setVisible(True)
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
            # Clear current entries
            self.list.clear()
            self.entries = {}
            
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
            for entry in entries:
                try:
                    print(f"Processing entry {entry.id}, encrypted_data length: {len(entry.encrypted_data)}")
                    decrypted_data = vault.decrypt_entry(entry.encrypted_data)
                    print(f"Successfully decrypted entry {entry.id}: {decrypted_data.get('title', 'Unknown')}")
                    
                    # Create list item with decrypted data
                    item = EntryListItem(entry, decrypted_data)
                    self.list.addItem(item)
                    self.entries[entry.id] = (item, entry, decrypted_data)
                    successful_entries += 1
                    
                except Exception as e:
                    print(f"Error decrypting entry {entry.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Add with minimal data
                    item = EntryListItem(entry)
                    self.list.addItem(item)
                    self.entries[entry.id] = (item, entry, None)
            
            print(f"Processed {successful_entries} entries successfully out of {len(entries)}")
            
            # Make sure the list is visible if we have entries
            if len(entries) > 0:
                print(f"Making list visible with {len(entries)} entries")
                self.list.setVisible(True)
                self.empty_label.setVisible(False)
                self.status_label.setVisible(False)
                
                # Force a layout update
                self.list.update()
                
                # Show count
                if hasattr(self, 'count_label'):
                    self.count_label.setText(f"{len(entries)} entries")
                    self.count_label.setVisible(True)
            else:
                self.status_label.setText("No entries found")
                self.status_label.setVisible(True)
                self.list.setVisible(False)
            
            # Apply filters (with fix to ensure items stay visible)
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
            
            # Remove from local data
            if item.entry_id in self.entries:
                del self.entries[item.entry_id]
            
            # Remove from list
            self.list.takeItem(self.list.row(item))
            
            # Update entry count
            self.update_count()
            
            # Check if list is now empty
            if self.list.count() == 0:
                self.empty_label.show()
                self.list.hide()
            
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
            
            # Refresh display if needed
            if self.list.count() > 0:
                self.list.setVisible(True)
                self.empty_label.setVisible(False)
            else:
                self.list.setVisible(False)
                self.empty_label.setText("No entries found")
                self.empty_label.setVisible(True)
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
        
        # Show/hide empty state based on actual item count, not filter results
        if self.list.count() > 0:
            # We have items, just maybe none visible after filtering
            if visible_count == 0:
                self.empty_label.setText("No matching entries found")
                self.empty_label.setVisible(True)
                self.list.setVisible(False)
            else:
                self.empty_label.setVisible(False)
                self.list.setVisible(True)
        else:
            # No items at all
            self.empty_label.setText("No entries found")
            self.empty_label.setVisible(True)
            self.list.setVisible(False)
        
        # Apply sort
        self.apply_sort()
        
        # Update count
        self.update_count()

    def reload_all_entries(self, force_display=True):
        """Completely reload all entries from scratch"""
        print("Performing complete entry reload")
        
        try:
            # Clear everything
            self.list.clear()
            self.entries = {}
            
            # Show loading
            self.status_label.setText("Loading entries...")
            self.status_label.setVisible(True)
            
            # Get a fresh API client if needed
            if not self.api_client and hasattr(self, 'parent'):
                parent = self.parent()
                if hasattr(parent, 'api_client'):
                    self.api_client = parent.api_client
                    
            if not self.api_client:
                self.status_label.setText("No API client available")
                return
                    
            # Load the entries through the load_entries_sync method
            self.load_entries_sync()
            
            # Force display if requested
            if force_display:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(300, self.force_display_refresh)
        
        except Exception as e:
            print(f"Error in reload_all_entries: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            
        # Make sure count is updated
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.update_count)
    
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
        """Apply current sort settings to the list"""
        try:
            # First, apply basic sorting by text
            self.list.sortItems(self.current_sort_order)
            
            # Skip custom sorting for title since the basic sort already handles it
            if self.current_sort_field == "title":
                return
                
            # Custom sorting for non-title fields - make a safe copy
            visible_items = []
            for i in range(self.list.count()):
                item = self.list.item(i)
                if item and not item.isHidden():
                    visible_items.append(item)
            
            if not visible_items:
                return  # No items to sort
            
            # Sort items based on selected field
            if self.current_sort_field == "username":
                # Safe sort - check if attribute exists before using it
                def get_username(x):
                    if hasattr(x, 'username') and x.username:
                        return x.username.lower()
                    return x.text().lower()
                    
                visible_items.sort(
                    key=get_username, 
                    reverse=(self.current_sort_order == Qt.SortOrder.DescendingOrder)
                )
            elif self.current_sort_field == "updated_at":
                # Safe sort with fallback for entries without updated_at
                def get_update_time(x):
                    if hasattr(x, 'entry_data') and hasattr(x.entry_data, 'updated_at'):
                        return x.entry_data.updated_at
                    elif hasattr(x, 'updated_at'):
                        return x.updated_at
                    else:
                        from datetime import datetime
                        return datetime.min
                        
                visible_items.sort(
                    key=get_update_time,
                    reverse=(self.current_sort_order == Qt.SortOrder.DescendingOrder)
                )
            
            # Only modify list if we have items to sort
            if visible_items:
                # Take all items from the list without deleting them
                for i in range(self.list.count()-1, -1, -1):
                    self.list.takeItem(i)
                
                # Re-add in sorted order
                for item in visible_items:
                    self.list.addItem(item)
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
            self.empty_label.setVisible(False)
            self.status_label.setVisible(False)
        else:
            print("No entries to display")
            self.empty_label.setVisible(True)
            self.list.setVisible(False)

    def force_display_refresh(self):
        """Force a refresh of the display"""
        print("Forcing display refresh...")
        
        try:
            # Make sure the list is visible
            self.list.setVisible(True)
            self.empty_label.setVisible(False)
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