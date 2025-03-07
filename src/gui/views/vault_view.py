from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSplitter
)
from PyQt6.QtCore import Qt

from api.client import APIClient
from utils.session import UserSession
from utils.async_utils import async_callback

# Later import these components when they're implemented
# from gui.widgets.category_tree import CategoryTree
# from gui.widgets.entry_list import PasswordEntryList
# from gui.widgets.entry_form import PasswordEntryForm

class VaultView(QWidget):
    """View for the password vault"""
    
    def __init__(self, api_client: APIClient, user_session: UserSession, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.user_session = user_session
        self.setup_ui()
        self.load_entries()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Add entry button
        self.add_btn = QPushButton("Add Entry")
        self.add_btn.clicked.connect(self.add_entry)
        toolbar_layout.addWidget(self.add_btn)
        
        # Search field (to be implemented)
        # self.search_field = SearchField()
        # toolbar_layout.addWidget(self.search_field)
        
        # Placeholder for search
        toolbar_layout.addWidget(QLabel("Search (coming soon)"))
        toolbar_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_entries)
        toolbar_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Main content - will use a splitter to allow resizing
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - categories (placeholder for now)
        self.categories_placeholder = QLabel("Categories\n(Coming Soon)")
        self.categories_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.categories_placeholder.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ddd;")
        self.splitter.addWidget(self.categories_placeholder)
        
        # Middle - entry list (placeholder for now)
        self.entries_placeholder = QLabel("Entry List\n(Coming Soon)")
        self.entries_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entries_placeholder.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        self.splitter.addWidget(self.entries_placeholder)
        
        # Right side - entry details (placeholder for now)
        self.details_placeholder = QLabel("Entry Details\n(Coming Soon)")
        self.details_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_placeholder.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd;")
        self.splitter.addWidget(self.details_placeholder)
        
        # Set initial sizes
        self.splitter.setSizes([200, 300, 500])
        
        layout.addWidget(self.splitter)
        
        # Status message
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    @async_callback
    async def load_entries(self):
        """Load password entries from server"""
        try:
            self.status_label.setText("Loading entries...")
            
            # When the actual entry list widget is implemented,
            # call api_client.list_entries() and populate it
            
            self.status_label.setText("Entries loaded successfully")
        except Exception as e:
            print(f"Error loading entries: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
    
    def add_entry(self):
        """Add a new password entry"""
        # This will be implemented later
        self.status_label.setText("Add entry functionality coming soon")