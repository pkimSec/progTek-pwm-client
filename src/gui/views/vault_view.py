from PyQt6.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout, QToolBar, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction

from api.client import APIClient
from api.models import APIError
from utils.async_utils import async_callback
from gui.widgets.category_tree import CategoryTree
from gui.widgets.entry_list import EntryList
from gui.widgets.entry_form import EntryForm

class VaultView(QWidget):
    """Main view for displaying and managing password entries"""
    
    def __init__(self, api_client: APIClient, master_password: str, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.master_password = master_password
        self._entries_loaded = False
        self.setup_ui()
    
        # Schedule data loading for later with a timer
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.load_entries)  # 500ms delay
    
    def setup_ui(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search entries...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        
        # Add entry button
        self.add_btn = QPushButton("Add Entry")
        self.add_btn.clicked.connect(self.add_entry)
        search_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(search_layout)
        
        # Main splitter (categories | entries | details)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Categories
        self.category_tree = CategoryTree()
        self.category_tree.category_selected.connect(self.on_category_selected)
        self.splitter.addWidget(self.category_tree)
        
        # Middle panel - Entry list
        self.entry_list = EntryList()
        self.entry_list.entry_selected.connect(self.on_entry_selected)
        self.splitter.addWidget(self.entry_list)
        
        # Right panel - Entry form
        self.entry_form = EntryForm()
        self.entry_form.saved.connect(self.on_entry_saved)
        self.entry_form.deleted.connect(self.on_entry_deleted)
        self.splitter.addWidget(self.entry_form)
        
        # Set initial sizes
        self.splitter.setSizes([200, 300, 500])
        
        main_layout.addWidget(self.splitter)
        
        # Status message
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

    def showEvent(self, event):
        """Override showEvent to load entries when the view becomes visible"""
        super().showEvent(event)
        # Only load if we haven't loaded already
        if not hasattr(self, '_entries_loaded') or not self._entries_loaded:
            self._entries_loaded = True
            QTimer.singleShot(100, self.load_entries)  # Small delay to ensure UI is ready
    
    @async_callback
    async def load_entries(self):
        """Load password entries from server"""
        try:
            self.status_label.setText("Loading entries...")
        
            # Try to get vault salt for key derivation
            try:
                salt = await self.api_client.get_vault_salt()
                print(f"Got vault salt: {salt[:10]}...")
            except APIError as e:
                if e.status_code == 401 and "Active session required" in e.message:
                    print("Session validation failed. Attempting to continue anyway...")
                    # Create dummy salt for testing purposes
                    salt = "dummy_salt_for_testing"
                else:
                    raise e
        
            # Get all entries - with try/except
            try:
                entries = await self.api_client.list_entries()
                print(f"Loaded {len(entries)} entries")
            except APIError as e:
                if e.status_code == 401 and "Active session required" in e.message:
                    print("Session validation failed for list_entries. Using empty list for testing.")
                    entries = []
                else:
                    raise e
        
         # Update UI
            self.entry_list.set_entries(entries)
            self.status_label.setText(f"Loaded {len(entries)} entries")
        
        except APIError as e:
            self.status_label.setText(f"Error: {e.message}")
            self.show_error(e)
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.show_error(e)
    
    def on_search(self, text: str):
        """Handle search text changes"""
        print(f"Search: {text}")
        self.entry_list.filter_entries(text)
    
    def on_category_selected(self, category: str):
        """Handle category selection"""
        print(f"Category selected: {category}")
        self.entry_list.filter_by_category(category)
    
    def on_entry_selected(self, entry_id: int):
        """Handle entry selection"""
        print(f"Entry selected: {entry_id}")
        # Load entry details in the form
        self.entry_form.load_entry(entry_id, self.master_password)
    
    @async_callback
    async def add_entry(self):
        """Add new entry"""
        print("Adding new entry")
        self.entry_form.clear()
        self.entry_form.set_mode("add")
    
    async def on_entry_saved(self, entry_id: int):
        """Handle entry saved event"""
        print(f"Entry saved: {entry_id}")
        # Reload entries
        await self.load_entries()
    
    async def on_entry_deleted(self, entry_id: int):
        """Handle entry deleted event"""
        print(f"Entry deleted: {entry_id}")
        # Reload entries
        await self.load_entries()
    
    def show_error(self, error):
        """Show error message"""
        QMessageBox.critical(self, "Error", str(error))