from PyQt6.QtWidgets import (  
    QListWidget, QListWidgetItem, QMenu, QAbstractItemView,  
    QVBoxLayout, QLabel, QWidget, QHBoxLayout  
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from api.models import PasswordEntry
import json

class EntryListItem(QListWidgetItem):
    """Custom list widget item for password entries"""
    
    def __init__(self, entry: PasswordEntry):
        super().__init__()
        self.entry_id = entry.id
        self.entry_data = entry.encrypted_data
        
        # Try to extract title from encrypted data if possible
        # This would normally be decrypted using the master password
        # For prototype purposes, just use a placeholder title
        self.title = f"Entry {entry.id}"
        
        # Set item text and other properties
        self.setText(self.title)
        self.setToolTip(f"Created: {entry.created_at}\nUpdated: {entry.updated_at}")

class EntryList(QWidget):
    """Widget for displaying password entries"""
    
    # Signal emitted when an entry is selected
    entry_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = {}  # Dictionary to track entries by ID
        self.current_category = "all"
        self.current_filter = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        self.count_label = QLabel("0 entries")
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)
        
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
        self.empty_label.setStyleSheet("color: gray; padding: 20px;")
        layout.addWidget(self.empty_label)
        self.empty_label.hide()
    
    def set_entries(self, entries: list[PasswordEntry]):
        """Set the list of entries to display"""
        # Clear current entries
        self.list.clear()
        self.entries.clear()
        
        # Add new entries
        for entry in entries:
            self.add_entry_item(entry)
        
        # Apply current filters
        self.apply_filters()
        
        # Update count
        self.update_count()
    
    def add_entry_item(self, entry: PasswordEntry):
        """Add an entry item to the list"""
        item = EntryListItem(entry)
        self.list.addItem(item)
        self.entries[entry.id] = (item, entry)
    
    def on_item_clicked(self, item: EntryListItem):
        """Handle item click - emit entry selected signal"""
        self.entry_selected.emit(item.entry_id)
    
    def show_context_menu(self, position):
        """Show context menu for entry management"""
        item = self.list.itemAt(position)
        if not item:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Add view action
        view_action = QAction("View", self)
        view_action.triggered.connect(lambda: self.on_item_clicked(item))
        menu.addAction(view_action)
        
        # Add edit action
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.on_item_clicked(item))
        menu.addAction(edit_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add delete action
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_entry(item))
        menu.addAction(delete_action)
        
        # Show menu
        menu.exec(self.list.viewport().mapToGlobal(position))
    
    def delete_entry(self, item: EntryListItem):
        """Delete an entry (just forwards to entry selected signal)"""
        # The actual deletion is handled by the parent view
        self.entry_selected.emit(item.entry_id)
    
    def filter_entries(self, text: str):
        """Filter entries by search text"""
        self.current_filter = text.lower()
        self.apply_filters()
    
    def filter_by_category(self, category: str):
        """Filter entries by category"""
        self.current_category = category
        self.apply_filters()
    
    def apply_filters(self):
        """Apply current filters to the entries"""
        visible_count = 0
        
        # Loop through all entries
        for entry_id, (item, entry) in self.entries.items():
            # Start with item visible
            visible = True
            
            # Apply category filter (except "all")
            if self.current_category != "all":
                # This would check if the entry belongs to the category
                # For prototype purposes, show all entries for any category
                pass
            
            # Apply text filter
            if self.current_filter and self.current_filter not in item.text().lower():
                visible = False
            
            # Set item visibility
            item.setHidden(not visible)
            
            if visible:
                visible_count += 1
        
        # Show/hide empty state
        if visible_count == 0:
            self.empty_label.show()
            self.list.hide()
        else:
            self.empty_label.hide()
            self.list.show()
        
        # Update count
        self.update_count()
    
    def update_count(self):
        """Update the entry count label"""
        visible_count = 0
        total_count = len(self.entries)
        
        # Count visible items
        for i in range(self.list.count()):
            if not self.list.item(i).isHidden():
                visible_count += 1
        
        # Update label
        if visible_count != total_count:
            self.count_label.setText(f"{visible_count} of {total_count} entries")
        else:
            self.count_label.setText(f"{total_count} entries")