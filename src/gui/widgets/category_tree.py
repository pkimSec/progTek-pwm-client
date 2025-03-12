from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
    QMessageBox, QVBoxLayout, QPushButton, QWidget,
    QHBoxLayout, QLabel, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QContextMenuEvent, QAction, QColor

from api.client import APIClient
from api.models import APIError
from utils.async_utils import async_callback
from typing import Dict, List, Optional, Any

class CategoryTree(QWidget):
    """Widget for displaying and managing password categories"""
    
    # Signal emitted when a category is selected
    category_selected = pyqtSignal(str, int)  # Category name, category ID
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.categories = {}  # Dictionary to track categories by ID
        self.category_items = {}  # Dictionary to track QTreeWidgetItems by category ID
        self.setup_ui()
        
        # Load categories from server
        self.load_categories()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with title and add button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Categories")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Add Category")
        self.add_btn.setMaximumWidth(24)
        self.add_btn.clicked.connect(self.add_category)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search categories...")
        self.search_box.textChanged.connect(self.filter_categories)
        layout.addWidget(self.search_box)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(15)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
        # Status label
        self.status_label = QLabel("Loading categories...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
    
    @async_callback
    async def load_categories(self):
        """Load categories from server"""
        try:
            # Create local variables for UI elements to prevent object deleted errors
            tree = self.tree if hasattr(self, 'tree') else None
            if not tree:
                print("Tree widget not available, aborting load")
                return
                
            status_label = self.status_label if hasattr(self, 'status_label') else None
            if status_label:
                try:
                    status_label.setText("Loading categories...")
                    status_label.setVisible(True)
                except RuntimeError:
                    print("Status label no longer available")
                    # Continue without updating the label
            
            # Clear existing items
            tree.clear()
            self.categories = {}
            self.category_items = {}
            
            # Create "All Items" at the top (cannot be deleted)
            all_items = QTreeWidgetItem(tree)
            all_items.setText(0, "All Items")
            all_items.setData(0, Qt.ItemDataRole.UserRole, {"id": None, "name": "All Items"})
            all_items.setFlags(all_items.flags() & ~Qt.ItemFlag.ItemIsEditable)
            all_items.setIcon(0, self.get_icon("folder"))
            self.category_items["all"] = all_items
            
            # Get categories from server
            categories = await self.api_client.list_categories()
            
            # Create a dictionary of categories by ID
            category_dict = {category['id']: category for category in categories}
            self.categories = category_dict
            
            # Process categories - first create items for all categories
            for category in categories:
                item = QTreeWidgetItem()
                item.setText(0, category['name'])
                item.setData(0, Qt.ItemDataRole.UserRole, category)
                item.setIcon(0, self.get_icon("folder"))
                self.category_items[category['id']] = item
            
            # Now build the tree structure
            for category in categories:
                item = self.category_items[category['id']]
                parent_id = category.get('parent_id')
                
                if parent_id is not None and parent_id in self.category_items:
                    # Add as child of parent
                    self.category_items[parent_id].addChild(item)
                else:
                    # Add as top-level item
                    tree.addTopLevelItem(item)
            
            # Expand all items
            tree.expandAll()
            
            # Select "All Items" by default
            tree.setCurrentItem(all_items)
            self.category_selected.emit("All Items", None)
            
            # Update status
            if status_label:
                try:
                    if len(categories) == 0:
                        status_label.setText("No categories found")
                    else:
                        status_label.setVisible(False)
                except RuntimeError:
                    print("Status label no longer available")
            
        except APIError as e:
            print(f"API Error loading categories: {e.message}")
            try:
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"Error: {e.message}")
                QMessageBox.critical(self, "Error", f"Failed to load categories: {e.message}")
            except RuntimeError:
                print("Widget no longer available for error display")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error loading categories: {str(e)}")
            
            try:
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Error loading categories")
                QMessageBox.critical(self, "Error", f"Failed to load categories: {str(e)}")
            except RuntimeError:
                print("Widget no longer available for error display")
    
    def get_icon(self, icon_type):
        """Get icon for tree items"""
        # Create QIcon from built-in resources or return empty icon
        from PyQt6.QtGui import QIcon
        if icon_type == "folder":
            # Return an empty icon for now - safer than returning None
            return QIcon()
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - emit category selected signal"""
        category_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(category_data, dict) and category_data.get('name') == "All Items":
            # All items - use None for category ID to show all entries
            print("All Items selected - showing entries from all categories")
            self.category_selected.emit("All Items", None)
        elif isinstance(category_data, dict):
            # Regular category
            category_id = category_data.get('id')
            category_name = category_data.get('name', '')
            print(f"Category selected: {category_name} (ID: {category_id})")
            self.category_selected.emit(category_name, category_id)
        else:
            print(f"Unknown category data: {category_data}")
    
    def filter_categories(self, filter_text: str):
        """Filter categories by text"""
        filter_text = filter_text.lower()
        
        # Function to check if item or any of its children match
        def check_item_match(item):
            item_text = item.text(0).lower()
            if filter_text in item_text:
                return True
                
            # Check children
            for i in range(item.childCount()):
                if check_item_match(item.child(i)):
                    return True
                    
            return False
        
        # Check all top-level items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            
            # Special case for "All Items"
            if item == self.category_items.get("all"):
                item.setHidden(False)
                continue
                
            # Check if item or its children match the filter
            is_match = check_item_match(item)
            item.setHidden(not is_match)
            
            # If matches, make sure all parent items are visible
            if is_match:
                parent = item.parent()
                while parent:
                    parent.setHidden(False)
                    parent = parent.parent()
    
    def add_category(self, parent_id=None):
        """Add a new category"""
        name, ok = QInputDialog.getText(
            self, "Add Category", "Category name:"
        )
        
        if ok and name:
            # Create category on server
            self.create_category(name, parent_id)
    
    @async_callback
    async def create_category(self, name: str, parent_id: Optional[int] = None):
        """Create a new category on the server"""
        try:
            # Call API to create category
            category = await self.api_client.create_category(name, parent_id)
            
            # Add to local categories
            self.categories[category['id']] = category
            
            # Add to tree
            item = QTreeWidgetItem()
            item.setText(0, category['name'])
            item.setData(0, Qt.ItemDataRole.UserRole, category)
            item.setIcon(0, self.get_icon("folder"))
            self.category_items[category['id']] = item
            
            # Add to parent
            if parent_id and parent_id in self.category_items:
                self.category_items[parent_id].addChild(item)
            else:
                self.tree.addTopLevelItem(item)
            
            # Expand parent
            if parent_id and parent_id in self.category_items:
                self.category_items[parent_id].setExpanded(True)
            
            # Update status
            self.status_label.setVisible(False)
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to create category: {e.message}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to create category: {str(e)}")
    
    def show_context_menu(self, position):
        """Show context menu for category management"""
        item = self.tree.itemAt(position)
        if not item:
            return
            
        # Get category data
        category_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Don't show menu for "All Items"
        if category_data == "all" or (isinstance(category_data, dict) and category_data.get('id') is None):
            return
            
        # Create menu
        menu = QMenu(self)
        
        # Add new category (as child)
        add_action = QAction("Add Subcategory", self)
        add_action.triggered.connect(lambda: self.add_category(category_data.get('id')))
        menu.addAction(add_action)
        
        # Rename category
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.rename_category(item))
        menu.addAction(rename_action)
        
        # Delete category
        menu.addSeparator()
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_category(item))
        menu.addAction(delete_action)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def rename_category(self, item: QTreeWidgetItem):
        """Rename a category"""
        category_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(category_data, dict) or 'id' not in category_data:
            return
            
        category_id = category_data['id']
        current_name = item.text(0)
        
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:",
            text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            self.update_category(category_id, new_name)
    
    @async_callback
    async def update_category(self, category_id: int, name: str):
        """Update a category on the server"""
        try:
            # Call API to update category
            updated = await self.api_client.update_category(category_id, name)
            
            # Update local data
            self.categories[category_id] = updated
            
            # Update tree item
            item = self.category_items.get(category_id)
            if item:
                item.setText(0, name)
                item.setData(0, Qt.ItemDataRole.UserRole, updated)
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to update category: {e.message}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to update category: {str(e)}")
    
    @async_callback
    async def delete_category(self, item: QTreeWidgetItem):
        """Delete a category"""
        category_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(category_data, dict) or 'id' not in category_data:
            return
            
        category_id = category_data['id']
        category_name = category_data['name']
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Category",
            f"Are you sure you want to delete the category '{category_name}'?\n\n"
            f"This will also delete all subcategories.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Call API to delete category
            await self.api_client.delete_category(category_id)
            
            # Remove from local data
            if category_id in self.categories:
                del self.categories[category_id]
            
            # Remove from tree
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree.indexOfTopLevelItem(item)
                self.tree.takeTopLevelItem(index)
            
            # Remove from item dictionary
            if category_id in self.category_items:
                del self.category_items[category_id]
            
            # Select "All Items"
            self.tree.setCurrentItem(self.category_items.get("all"))
            self.category_selected.emit("All Items", None)
            
            # Update status if no categories left
            if len(self.categories) == 0:
                self.status_label.setText("No categories found")
                self.status_label.setVisible(True)
            
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to delete category: {e.message}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to delete category: {str(e)}")