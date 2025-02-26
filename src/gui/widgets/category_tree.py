from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
    QMessageBox, QVBoxLayout, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QContextMenuEvent, QAction

class CategoryTree(QWidget):
    """Widget for displaying and managing password categories"""
    
    # Signal emitted when a category is selected
    category_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = {}  # Dictionary to track categories and their items
        self.setup_ui()
        self.create_default_categories()
    
    def setup_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Categories")
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
        # Add category button
        self.add_btn = QPushButton("Add Category")
        self.add_btn.clicked.connect(self.add_category)
        layout.addWidget(self.add_btn)
    
    def create_default_categories(self):
        """Create default category structure"""
        # Add "All Items" at the top (cannot be deleted)
        all_items = QTreeWidgetItem(self.tree)
        all_items.setText(0, "All Items")
        all_items.setData(0, Qt.ItemDataRole.UserRole, "all")
        all_items.setFlags(all_items.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.categories["all"] = all_items
        
        # Add default categories
        default_categories = [
            "Business", 
            "Finance", 
            "Personal", 
            "Social", 
            "Email", 
            "Shopping"
        ]
        
        for category in default_categories:
            self.add_category_item(category)
        
        # Expand all items
        self.tree.expandAll()
        
        # Select "All Items" by default
        self.tree.setCurrentItem(all_items)
    
    def add_category_item(self, name: str) -> QTreeWidgetItem:
        """Add a category item to the tree"""
        item = QTreeWidgetItem(self.tree)
        item.setText(0, name)
        item.setData(0, Qt.ItemDataRole.UserRole, name.lower())
        self.categories[name.lower()] = item
        return item
    
    def add_category(self):
        """Add a new category"""
        name, ok = QInputDialog.getText(
            self, "Add Category", "Category name:"
        )
        
        if ok and name:
            # Check if category already exists
            if name.lower() in self.categories:
                QMessageBox.warning(
                    self, "Duplicate Category",
                    f"Category '{name}' already exists."
                )
                return
            
            # Add category
            self.add_category_item(name)
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - emit category selected signal"""
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.category_selected.emit(category_id)
    
    def show_context_menu(self, position):
        """Show context menu for category management"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        # Get category ID
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Create context menu
        menu = QMenu(self)
        
        # Add rename action (except for "All Items")
        if category_id != "all":
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self.rename_category(item))
            menu.addAction(rename_action)
            
            # Add delete action
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_category(item))
            menu.addAction(delete_action)
        
        # Show menu
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def rename_category(self, item: QTreeWidgetItem):
        """Rename a category"""
        old_name = item.text(0)
        old_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            # Check if new name already exists
            if new_name.lower() in self.categories and new_name.lower() != old_id:
                QMessageBox.warning(
                    self, "Duplicate Category",
                    f"Category '{new_name}' already exists."
                )
                return
            
            # Update item
            item.setText(0, new_name)
            new_id = new_name.lower()
            item.setData(0, Qt.ItemDataRole.UserRole, new_id)
            
            # Update categories dictionary
            del self.categories[old_id]
            self.categories[new_id] = item
    
    def delete_category(self, item: QTreeWidgetItem):
        """Delete a category"""
        category_name = item.text(0)
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Category",
            f"Are you sure you want to delete the category '{category_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from tree
            index = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(index)
            
            # Remove from categories dictionary
            del self.categories[category_id]
            
            # Select "All Items"
            self.tree.setCurrentItem(self.categories["all"])
            self.category_selected.emit("all")
    
    def get_categories(self) -> list[str]:
        """Get list of all categories"""
        return list(self.categories.keys())