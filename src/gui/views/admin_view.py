from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QTextEdit, QDialog, QDialogButtonBox, QMessageBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QCheckBox, QTabWidget, QSplitter, QListWidget, QListWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QClipboard, QGuiApplication, QAction, QColor

from api.client import APIClient
from api.models import APIError
from utils.async_utils import async_callback


class InviteDialog(QDialog):
    """Dialog to display generated invite code"""
    
    def __init__(self, invite_code: str, parent=None):
        super().__init__(parent)
        self.invite_code = invite_code
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Invite Code Generated")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Instruction
        info_label = QLabel(
            "A new invite code has been generated. Share this with a user to allow them to register."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Invite code field
        invite_layout = QHBoxLayout()
        self.code_field = QLineEdit(self.invite_code)
        self.code_field.setReadOnly(True)
        self.code_field.setMinimumWidth(300)
        invite_layout.addWidget(self.code_field)
        
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.copy_invite_code)
        invite_layout.addWidget(copy_btn)
        
        layout.addLayout(invite_layout)
        
        # Security warning
        warning_label = QLabel(
            "<b>Security Notice:</b> This invite code grants access to your password vault. "
            "Share it only with trusted individuals through a secure channel."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #CC0000")
        layout.addWidget(warning_label)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def copy_invite_code(self):
        """Copy invite code to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.invite_code)
        
        # Show confirmation
        QMessageBox.information(
            self, "Copied", 
            "Invite code copied to clipboard!",
            QMessageBox.StandardButton.Ok
        )


class InviteListWidget(QWidget):
    """Widget for displaying and managing invite codes"""
    
    refresh_requested = pyqtSignal()  # Signal to request a refresh of the list
    deactivate_requested = pyqtSignal(str)  # Signal to request deactivation of an invite code
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invite_codes = []  # List of invite codes
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Generated Invite Codes")
        title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title_label)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)
        
        # Empty state message
        self.empty_label = QLabel("No invite codes have been generated yet.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.empty_label)
        
        # Initially show empty state
        self.list_widget.hide()
        self.empty_label.show()
    
    def set_invite_codes(self, invite_codes):
        """Set the list of invite codes"""
        self.invite_codes = invite_codes
        self.update_list()
    
    def update_list(self):
        """Update the list widget with invite codes"""
        self.list_widget.clear()
        
        if not self.invite_codes:
            self.list_widget.hide()
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        self.list_widget.show()
        
        for invite in self.invite_codes:
            item = QListWidgetItem()
            
            # Create display text
            display_text = invite['code']
            if 'email' in invite and invite['email']:
                display_text = f"{display_text} - Used by: {invite['email']}"
            
            item.setText(display_text)
            
            # Set data for context menu
            item.setData(Qt.ItemDataRole.UserRole, invite)
            
            # Set color based on status
            if invite.get('is_used', False):
                item.setForeground(QColor('gray'))
                item.setToolTip(f"Used by {invite.get('email', 'unknown')}")
            else:
                item.setForeground(QColor('green'))
                item.setToolTip("Available for use")
            
            self.list_widget.addItem(item)
    
    def add_invite_code(self, invite_code):
        """Add a newly generated invite code to the list"""
        # Create a new invite code entry
        new_invite = {
            'code': invite_code,
            'is_used': False
        }
        
        # Add to list and update
        self.invite_codes.insert(0, new_invite)  # Add at the beginning
        self.update_list()
    
    def on_refresh_clicked(self):
        """Handle refresh button click"""
        self.refresh_requested.emit()
    
    def show_context_menu(self, position):
        """Show context menu for invite code actions"""
        item = self.list_widget.itemAt(position)
        if not item:
            return
            
        # Get invite data
        invite = item.data(Qt.ItemDataRole.UserRole)
        if not invite:
            return
            
        # Create menu
        menu = QMenu(self)
        
        # Copy action
        copy_action = QAction("Copy Code", self)
        copy_action.triggered.connect(lambda: self.copy_to_clipboard(invite['code']))
        menu.addAction(copy_action)
        
        # Deactivate action (only if not used)
        if not invite.get('is_used', False):
            deactivate_action = QAction("Deactivate", self)
            deactivate_action.triggered.connect(lambda: self.deactivate_invite(invite['code']))
            menu.addAction(deactivate_action)
        
        menu.exec(self.list_widget.viewport().mapToGlobal(position))
    
    def copy_to_clipboard(self, invite_code):
        """Copy invite code to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(invite_code)
        
        # Show confirmation
        QMessageBox.information(
            self, "Copied", 
            "Invite code copied to clipboard!",
            QMessageBox.StandardButton.Ok
        )
    
    def deactivate_invite(self, invite_code):
        """Request to deactivate an invite code"""
        # Confirm deactivation
        reply = QMessageBox.question(
            self, "Confirm Deactivation",
            f"Are you sure you want to deactivate this invite code?\n\n{invite_code}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.deactivate_requested.emit(invite_code)


class UserTableWidget(QWidget):
    """Widget for displaying and managing users"""
    
    user_selected = pyqtSignal(int)  # Signal emitted with user ID when selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.users = {}  # Store user data by ID
        
    def setup_ui(self):
        """Set up the table UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the table
        self.table = QTableWidget()
        
        # Set column headers
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Email", "Role", "Status", "Actions"])
        
        # Set table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Email
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Role
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Connect signals
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        layout.addWidget(self.table)
    
    def set_users(self, users):
        """Set the list of users to display"""
        self.table.clearContents()
        self.table.setRowCount(len(users))
        self.users = {}
        
        for i, user in enumerate(users):
            # Store user data
            self.users[user['id']] = user
            
            # Set table cells
            self.table.setItem(i, 0, QTableWidgetItem(str(user['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(user['email']))
            self.table.setItem(i, 2, QTableWidgetItem(user['role']))
            
            # Status indicator
            status_text = "Active" if user['is_active'] else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor('darkGreen') if user['is_active'] else QColor('darkRed'))
            self.table.setItem(i, 3, status_item)
            
            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            
            # Toggle status button
            toggle_btn = QPushButton("Disable" if user['is_active'] else "Enable")
            toggle_btn.setProperty("user_id", user['id'])
            toggle_btn.setProperty("action", "toggle_status")
            toggle_btn.clicked.connect(self.on_action_button_clicked)
            actions_layout.addWidget(toggle_btn)
            
            # Edit role button (disabled for admin users for safety)
            if user['role'] != 'admin':
                edit_role_btn = QPushButton("Edit Role")
                edit_role_btn.setProperty("user_id", user['id'])
                edit_role_btn.setProperty("action", "edit_role")
                edit_role_btn.clicked.connect(self.on_action_button_clicked)
                actions_layout.addWidget(edit_role_btn)
            
            self.table.setCellWidget(i, 4, actions_widget)
    
    def on_cell_clicked(self, row, column):
        """Handle cell clicks to emit the user_selected signal"""
        # Only emit signal when clicking on non-action cells
        if column != 4:
            user_id = int(self.table.item(row, 0).text())
            self.user_selected.emit(user_id)
    
    def on_action_button_clicked(self):
        """Handle action button clicks"""
        sender = self.sender()
        user_id = sender.property("user_id")
        action = sender.property("action")
        
        if action == "toggle_status":
            # Forward to the parent widget
            parent = self.parent()
            while parent and not hasattr(parent, 'toggle_user_status'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'toggle_user_status'):
                parent.toggle_user_status(user_id)
        elif action == "edit_role":
            parent = self.parent()
            while parent and not hasattr(parent, 'edit_user_role'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'edit_user_role'):
                parent.edit_user_role(user_id)


class RoleDialog(QDialog):
    """Dialog for editing user roles"""
    
    def __init__(self, user_id, current_role, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.current_role = current_role
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Edit User Role")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Role selection
        form_layout = QFormLayout()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["user", "admin"])
        
        # Set current role
        index = self.role_combo.findText(self.current_role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
            
        form_layout.addRow("Role:", self.role_combo)
        layout.addLayout(form_layout)
        
        # Warning for admin role
        self.admin_warning = QLabel(
            "<b>Warning:</b> Assigning admin role grants full access to all vault data "
            "and user management capabilities."
        )
        self.admin_warning.setWordWrap(True)
        self.admin_warning.setStyleSheet("color: #CC0000")
        self.admin_warning.setVisible(self.role_combo.currentText() == "admin")
        layout.addWidget(self.admin_warning)
        
        # Connect role change to show/hide warning
        self.role_combo.currentTextChanged.connect(self.on_role_changed)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_role_changed(self, role):
        """Show warning when admin role is selected"""
        self.admin_warning.setVisible(role == "admin")
    
    def get_selected_role(self):
        """Get the selected role"""
        return self.role_combo.currentText()


class UserDetailWidget(QWidget):
    """Widget for displaying user details"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_user_id = None
    
    def setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        
        # Title
        self.title_label = QLabel("User Details")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Form layout for details
        form_layout = QFormLayout()
        
        self.user_id_label = QLabel()
        form_layout.addRow("User ID:", self.user_id_label)
        
        self.email_label = QLabel()
        form_layout.addRow("Email:", self.email_label)
        
        self.role_label = QLabel()
        form_layout.addRow("Role:", self.role_label)
        
        self.status_label = QLabel()
        form_layout.addRow("Status:", self.status_label)
        
        self.created_label = QLabel()
        form_layout.addRow("Created:", self.created_label)
        
        layout.addLayout(form_layout)
        
        # Add actions
        actions_layout = QHBoxLayout()
        
        self.toggle_status_btn = QPushButton()
        self.toggle_status_btn.clicked.connect(self.on_toggle_status)
        actions_layout.addWidget(self.toggle_status_btn)
        
        self.edit_role_btn = QPushButton("Edit Role")
        self.edit_role_btn.clicked.connect(self.on_edit_role)
        actions_layout.addWidget(self.edit_role_btn)
        
        layout.addLayout(actions_layout)
        
        # Add placeholder for activity log, session info, etc.
        self.placeholder = QLabel("Additional user data will be displayed here in future updates.")
        self.placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Hide initially until a user is selected
        self.setVisible(False)
    
    def set_user(self, user_data):
        """Set the user data to display"""
        if not user_data:
            self.setVisible(False)
            self.current_user_id = None
            return
        
        self.current_user_id = user_data['id']
        
        # Set labels
        self.user_id_label.setText(str(user_data['id']))
        self.email_label.setText(user_data['email'])
        self.role_label.setText(user_data['role'])
        
        status_text = "Active" if user_data['is_active'] else "Inactive"
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(
            "color: darkgreen;" if user_data['is_active'] else "color: darkred;"
        )
        
        if 'created_at' in user_data:
            self.created_label.setText(user_data['created_at'])
        else:
            self.created_label.setText("Unknown")
        
        # Update toggle button
        self.toggle_status_btn.setText("Disable User" if user_data['is_active'] else "Enable User")
        
        # Disable edit controls for admin user (for safety)
        is_admin = user_data['role'] == 'admin'
        self.edit_role_btn.setEnabled(not is_admin)
        
        # Show the widget
        self.setVisible(True)
    
    def on_toggle_status(self):
        """Handle toggle status button click"""
        if self.current_user_id:
            # Forward to the parent widget
            parent = self.parent()
            while parent and not hasattr(parent, 'toggle_user_status'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'toggle_user_status'):
                parent.toggle_user_status(self.current_user_id)
    
    def on_edit_role(self):
        """Handle edit role button click"""
        if self.current_user_id:
            # Forward to the parent widget
            parent = self.parent()
            while parent and not hasattr(parent, 'edit_user_role'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'edit_user_role'):
                parent.edit_user_role(self.current_user_id)


class AdminView(QWidget):
    """View for administrative functions"""
    
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setup_ui()
        
        # Load data when view is shown
        self.refresh_users()
    
    def setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Admin Dashboard</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Create tab widget for different admin functions
        self.tab_widget = QTabWidget()
        
        # User Management tab
        user_management_tab = QWidget()
        self.setup_user_management_tab(user_management_tab)
        self.tab_widget.addTab(user_management_tab, "User Management")
        
        # Invite Management tab
        invite_management_tab = QWidget()
        self.setup_invite_management_tab(invite_management_tab)
        self.tab_widget.addTab(invite_management_tab, "Invite Management")
        
        # System Information tab (placeholder for future implementation)
        system_tab = QWidget()
        self.setup_system_tab(system_tab)
        self.tab_widget.addTab(system_tab, "System Information")
        
        main_layout.addWidget(self.tab_widget)
    
    def setup_user_management_tab(self, tab):
        """Set up the user management tab"""
        layout = QVBoxLayout(tab)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.refresh_users_btn = QPushButton("Refresh Users")
        self.refresh_users_btn.clicked.connect(self.refresh_users)
        action_layout.addWidget(self.refresh_users_btn)
        
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        # Splitter for user list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # User table
        self.user_table = UserTableWidget()
        self.user_table.user_selected.connect(self.on_user_selected)
        splitter.addWidget(self.user_table)
        
        # User details
        self.user_details = UserDetailWidget()
        splitter.addWidget(self.user_details)
        
        # Set initial sizes
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
    
    def setup_invite_management_tab(self, tab):
        """Set up the invite management tab"""
        layout = QVBoxLayout(tab)
        
        # Invite management section
        invite_group = QGroupBox("User Invitations")
        invite_layout = QVBoxLayout(invite_group)
        
        invite_info = QLabel(
            "Generate invite codes for new users. Each code can only be used once."
        )
        invite_info.setWordWrap(True)
        invite_layout.addWidget(invite_info)
        
        # Generate invite button
        generate_btn = QPushButton("Generate New Invite Code")
        generate_btn.clicked.connect(self.generate_invite_code_direct)
        invite_layout.addWidget(generate_btn)
        
        # Invite list
        self.invite_list = InviteListWidget()
        self.invite_list.refresh_requested.connect(self.refresh_invite_codes)
        self.invite_list.deactivate_requested.connect(self.deactivate_invite_code)
        invite_layout.addWidget(self.invite_list)
        
        layout.addWidget(invite_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Initial refresh of invite codes
        self.refresh_invite_codes()
    
    def setup_system_tab(self, tab):
        """Set up the system information tab"""
        layout = QVBoxLayout(tab)
        
        # System information section
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout(system_group)
        
        system_info = QLabel(
            "System information will be available in a future update.\n\n"
            "Planned features:\n"
            "- Server status monitoring\n"
            "- Database statistics\n"
            "- Active sessions\n"
            "- System logs"
        )
        system_info.setWordWrap(True)
        system_layout.addWidget(system_info)
        
        layout.addWidget(system_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def generate_invite_code_direct(self):
        """Non-async version of invite code generation for debugging"""
        print("Direct invite generation method called")
        try:
            # Import the needed tools for a manual async call
            import asyncio
            from PyQt6.QtCore import QTimer
        
            # Create a function to run the async code
            async def run_async():
                try:
                    print("Beginning invite code generation...")
                
                    # Call API to create invite
                    invite_code = await self.api_client.create_invite()
                
                    print(f"Received invite code: {invite_code}")
                
                    # Use closure to capture invite_code
                    def show_and_add():
                        self.show_invite_dialog(invite_code)
                        self.add_invite_to_list(invite_code)
                
                    # Show invite code dialog in the main thread
                    QTimer.singleShot(0, show_and_add)
                
                except Exception as e:
                    import traceback
                    print(f"Exception during invite generation: {str(e)}")
                    traceback.print_exc()
                
                    # Capture exception in closure for the timer callback
                    error_msg = str(e)
                    QTimer.singleShot(0, lambda: self.show_error_dialog(error_msg))
        
            # Use a global event loop from asyncio directly
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        
            # Run coroutine without closing the loop
            future = asyncio.ensure_future(run_async(), loop=loop)
            loop.run_until_complete(future)
        
        except Exception as e:
            import traceback
            print(f"Exception setting up async loop: {str(e)}")
            traceback.print_exc()
            self.show_error_dialog(f"Failed to generate invite code: {str(e)}")
    
    def show_invite_dialog(self, invite_code):
        """Show the invite dialog with the generated code"""
        dialog = InviteDialog(invite_code, self)
        dialog.exec()
        
    def show_error_dialog(self, error_message):
        """Show error dialog with the given message"""
        QMessageBox.critical(
            self, "Error", 
            f"Failed to generate invite code: {error_message}",
            QMessageBox.StandardButton.Ok
        )
    
    def add_invite_to_list(self, invite_code):
        """Add a newly generated invite code to the list"""
        if hasattr(self, 'invite_list'):
            self.invite_list.add_invite_code(invite_code)
    
    def refresh_invite_codes(self):
        """Refresh the list of invite codes"""
        try:
            # Import the needed tools for a manual async call
            import asyncio
            from PyQt6.QtCore import QTimer
        
            # Create a function to run the async code
            async def run_async():
                try:
                    print("Refreshing invite codes...")
                
                    # Call API to get invite codes
                    invite_codes = await self.api_client.list_invite_codes()
                
                    print(f"Received {len(invite_codes)} invite codes")
                
                    # Capture invite_codes in closure
                    def update_list():
                        self.update_invite_list(invite_codes)
                
                    # Update UI in the main thread
                    QTimer.singleShot(0, update_list)
                
                except Exception as e:
                    import traceback
                    print(f"Exception during invite refresh: {str(e)}")
                    traceback.print_exc()
                    # Empty list if error
                    QTimer.singleShot(0, lambda: self.update_invite_list([]))
        
            # Use a global event loop from asyncio directly
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        
            # Run coroutine without closing the loop
            future = asyncio.ensure_future(run_async(), loop=loop)
            loop.run_until_complete(future)
        
        except Exception as e:
            import traceback
            print(f"Exception setting up async loop: {str(e)}")
            traceback.print_exc()
    
    def update_invite_list(self, invite_codes):
        """Update the invite list widget with the given invite codes"""
        if hasattr(self, 'invite_list'):
            self.invite_list.set_invite_codes(invite_codes)
    
    def deactivate_invite_code(self, invite_code):
        """Deactivate the given invite code"""
        try:
            # Import the needed tools for a manual async call
            import asyncio
            from PyQt6.QtCore import QTimer
        
            # Create a function to run the async code
            async def run_async():
                try:
                    print(f"Deactivating invite code: {invite_code}")
                
                    # Call API to deactivate invite code
                    result = await self.api_client.deactivate_invite_code(invite_code)
                
                    print(f"Deactivation result: {result}")
                
                    # Show success message and refresh the list
                    QTimer.singleShot(0, self.show_deactivation_success)
                    QTimer.singleShot(100, self.refresh_invite_codes)
                
                except Exception as e:
                    import traceback
                    print(f"Exception during invite deactivation: {str(e)}")
                    traceback.print_exc()
                
                    # Capture exception message
                    error_msg = str(e)
                    QTimer.singleShot(0, lambda: self.show_error_dialog(f"Failed to deactivate invite code: {error_msg}"))
        
            # Use a global event loop from asyncio directly
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        
            # Run coroutine without closing the loop
            future = asyncio.ensure_future(run_async(), loop=loop)
            loop.run_until_complete(future)
        
        except Exception as e:
            import traceback
            print(f"Exception setting up async loop: {str(e)}")
            traceback.print_exc()
            self.show_error_dialog(f"Failed to deactivate invite code: {str(e)}")
    
    def show_deactivation_success(self):
        """Show success message for invite code deactivation"""
        QMessageBox.information(
            self, "Success", 
            "Invite code deactivated successfully.",
            QMessageBox.StandardButton.Ok
        )
        
    @async_callback
    async def refresh_users(self):
        """Refresh the user list"""
        try:
            # Show loading indicator if available
            if hasattr(self, 'status_label'):
                self.status_label.setText("Loading users...")
                self.status_label.setVisible(True)
            
            print("AdminView: Refreshing users list")
            
            # Clear existing data
            self.user_table.table.clearContents()
            self.user_table.table.setRowCount(0)
            
            # Fetch users from API
            try:
                users = await self.api_client.list_users()
                print(f"Fetched {len(users)} users from server")
                
                # Display users in table
                self.user_table.set_users(users)
                
                # Update status
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"Loaded {len(users)} users")
                    self.status_label.setVisible(False)
                
            except APIError as e:
                print(f"API Error: {e.status_code} - {e.message}")
                # Show specific error message
                if e.status_code == 403:
                    QMessageBox.critical(
                        self, "Permission Denied", 
                        "You don't have permission to view users.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    QMessageBox.critical(
                        self, "Error", 
                        f"Failed to load users: {e.message}",
                        QMessageBox.StandardButton.Ok
                    )
                
        except Exception as e:
            print(f"AdminView: Error refreshing users: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Error: {str(e)}")
                
            # Show general error
            QMessageBox.critical(
                self, "Error", 
                f"Failed to load users: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            # Hide loading indicator if available
            if hasattr(self, 'show_loading'):
                self.show_loading(False)
    
    def on_user_selected(self, user_id):
        """Handle user selection in the table"""
        # Find user data
        if hasattr(self, 'user_table') and hasattr(self.user_table, 'users'):
            user_data = self.user_table.users.get(user_id)
            if user_data:
                self.user_details.set_user(user_data)
    
    @async_callback
    async def toggle_user_status(self, user_id):
        """Toggle user active status"""
        # Get current user data
        if hasattr(self, 'user_table') and hasattr(self.user_table, 'users'):
            user_data = self.user_table.users.get(user_id)
            if not user_data:
                return
                
            # Confirm action
            current_status = "active" if user_data['is_active'] else "inactive"
            new_status = "inactive" if user_data['is_active'] else "active"
            
            confirm_msg = f"Are you sure you want to change the user's status from {current_status} to {new_status}?"
            if user_data['role'] == 'admin':
                confirm_msg += "\n\nWARNING: This is an admin user. Changing their status may impact system access."
                
            reply = QMessageBox.question(
                self, "Confirm Status Change",
                confirm_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            try:
                # Show loading indicator if available
                if hasattr(self, 'show_loading'):
                    self.show_loading(True)
                
                # Call API to update user status
                await self.api_client.update_user_status(user_id, not user_data['is_active'])
                
                # Update local data after successful API call
                user_data['is_active'] = not user_data['is_active']
                
                # Update UI
                self.user_table.set_users(list(self.user_table.users.values()))
                
                # If the current user is selected in the details panel, update it
                if self.user_details.current_user_id == user_id:
                    self.user_details.set_user(user_data)
                    
                # Show success message
                QMessageBox.information(
                    self, "Success",
                    f"User status updated successfully.",
                    QMessageBox.StandardButton.Ok
                )
                
            except APIError as e:
                print(f"AdminView: API Error updating user status: {e.status_code} - {e.message}")
                # Show error with specific message
                if e.status_code == 403:
                    QMessageBox.critical(
                        self, "Permission Denied", 
                        "You don't have permission to update user status.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    QMessageBox.critical(
                        self, "Error", 
                        f"Failed to update user status: {e.message}",
                        QMessageBox.StandardButton.Ok
                    )
            except Exception as e:
                import traceback
                print(f"AdminView: Exception updating user status: {str(e)}")
                traceback.print_exc()
                # Show general error
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to update user status: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )
            finally:
                # Hide loading indicator if available
                if hasattr(self, 'show_loading'):
                    self.show_loading(False)
    
    @async_callback
    async def edit_user_role(self, user_id):
        """Edit user role"""
        # Get current user data
        if hasattr(self, 'user_table') and hasattr(self.user_table, 'users'):
            user_data = self.user_table.users.get(user_id)
            if not user_data:
                return
                
            # Show role dialog
            dialog = RoleDialog(user_id, user_data['role'], self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
                
            # Get selected role
            new_role = dialog.get_selected_role()
            if new_role == user_data['role']:
                return  # No change
                
            try:
                # Show loading indicator if available
                if hasattr(self, 'show_loading'):
                    self.show_loading(True)
                
                # Call API to update user role
                await self.api_client.update_user_role(user_id, new_role)
                
                # Update local data after successful API call
                user_data['role'] = new_role
                
                # Update UI
                self.user_table.set_users(list(self.user_table.users.values()))
                
                # If the current user is selected in the details panel, update it
                if self.user_details.current_user_id == user_id:
                    self.user_details.set_user(user_data)
                    
                # Show success message
                QMessageBox.information(
                    self, "Success",
                    f"User role updated successfully.",
                    QMessageBox.StandardButton.Ok
                )
                
            except APIError as e:
                print(f"AdminView: API Error updating user role: {e.status_code} - {e.message}")
                # Show error with specific message
                if e.status_code == 403:
                    QMessageBox.critical(
                        self, "Permission Denied", 
                        "You don't have permission to update user roles.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    QMessageBox.critical(
                        self, "Error", 
                        f"Failed to update user role: {e.message}",
                        QMessageBox.StandardButton.Ok
                    )
            except Exception as e:
                import traceback
                print(f"AdminView: Exception updating user role: {str(e)}")
                traceback.print_exc()
                # Show general error
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to update user role: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )
            finally:
                # Hide loading indicator if available
                if hasattr(self, 'show_loading'):
                    self.show_loading(False)