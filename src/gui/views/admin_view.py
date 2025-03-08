from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QTextEdit, QDialog, QDialogButtonBox, QMessageBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QComboBox, QCheckBox, QTabWidget, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QClipboard, QGuiApplication

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

class UserTableWidget(QTableWidget):
    """Widget for displaying and managing users"""
    
    user_selected = pyqtSignal(int)  # Signal emitted with user ID when selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.users = {}  # Store user data by ID
        
    def setup_ui(self):
        """Set up the table UI"""
        # Set column headers
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Email", "Role", "Status", "Actions"])
        
        # Set table properties
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        
        # Set column widths
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Email
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Role
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Connect signals
        self.cellClicked.connect(self.on_cell_clicked)
    
    def set_users(self, users):
        """Set the list of users to display"""
        self.clearContents()
        self.setRowCount(len(users))
        self.users = {}
        
        for i, user in enumerate(users):
            # Store user data
            self.users[user['id']] = user
            
            # Set table cells
            self.setItem(i, 0, QTableWidgetItem(str(user['id'])))
            self.setItem(i, 1, QTableWidgetItem(user['email']))
            self.setItem(i, 2, QTableWidgetItem(user['role']))
            
            # Status indicator
            status_text = "Active" if user['is_active'] else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(Qt.GlobalColor.darkGreen if user['is_active'] else Qt.GlobalColor.darkRed)
            self.setItem(i, 3, status_item)
            
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
            
            self.setCellWidget(i, 4, actions_widget)
    
    def on_cell_clicked(self, row, column):
        """Handle cell clicks to emit the user_selected signal"""
        # Only emit signal when clicking on non-action cells
        if column != 4:
            user_id = int(self.item(row, 0).text())
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
                    
                    # Show invite code dialog in the main thread
                    QTimer.singleShot(0, lambda: self.show_invite_dialog(invite_code))
                    
                except Exception as e:
                    import traceback
                    print(f"Exception during invite generation: {str(e)}")
                    traceback.print_exc()
                    # Show error on main thread
                    QTimer.singleShot(0, lambda: self.show_error_dialog(str(e)))
            
            # Create and run the event loop
            async def start():
                task = asyncio.create_task(run_async())
                await task
            
            # Run the async code in a way that works with Qt
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start())
            loop.close()
            
        except Exception as e:
            import traceback
            print(f"Exception setting up async loop: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(
                self, "Error", 
                f"Failed to generate invite code: {str(e)}",
                QMessageBox.StandardButton.Ok
            )

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
        
        # Generate invite button - using a direct approach to bypass potential async issues
        generate_btn = QPushButton("Generate New Invite Code")
        
        # Use a direct method (not async) to test button connection
        def on_generate_button_clicked():
            self.generate_invite_code_direct()
            
        generate_btn.clicked.connect(on_generate_button_clicked)
        invite_layout.addWidget(generate_btn)
        
        # Recent invites (placeholder for now)
        invites_label = QLabel("Recent Invites (Coming Soon)")
        invites_label.setStyleSheet("color: gray; font-style: italic;")
        invite_layout.addWidget(invites_label)
        
        layout.addWidget(invite_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
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
    
    @async_callback
    async def generate_invite_code(self):
        """Generate a new invite code"""
        try:
            # Show loading indicator if available
            if hasattr(self, 'show_loading'):
                self.show_loading(True)
            
            print("AdminView: Generating invite code - calling API")
            
            # Call API to create invite
            invite_code = await self.api_client.create_invite()
            
            print(f"AdminView: Received invite code: {invite_code}")
            
            # Show invite code dialog
            dialog = InviteDialog(invite_code, self)
            dialog.exec()
            
        except APIError as e:
            print(f"AdminView: API Error generating invite code: {e.status_code} - {e.message}")
            # Show error with specific message
            if e.status_code == 403:
                QMessageBox.critical(
                    self, "Permission Denied", 
                    "You don't have permission to generate invite codes. Admin role is required.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to generate invite code: {e.message}",
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            import traceback
            print(f"AdminView: Exception generating invite code: {str(e)}")
            traceback.print_exc()
            # Show general error
            QMessageBox.critical(
                self, "Error", 
                f"Failed to generate invite code: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            print("AdminView: Invite code generation complete")
            # Hide loading indicator if available
            if hasattr(self, 'show_loading'):
                self.show_loading(False)
    
    @async_callback
    async def refresh_users(self):
        """Refresh the user list"""
        try:
            # Show loading indicator if available
            if hasattr(self, 'show_loading'):
                self.show_loading(True)
            
            print("AdminView: Refreshing users list")
            
            # This message will be displayed in the UI for now
            self.user_table.clearContents()
            self.user_table.setRowCount(0)
            
            # Display a message that this feature is waiting for API implementation
            QMessageBox.information(
                self, "Feature Not Available", 
                "User management features are waiting for server API implementation.\n\n"
                "The server-side endpoints for user listing and management need to be "
                "added to your server before these features will work.",
                QMessageBox.StandardButton.Ok
            )
            
        except APIError as e:
            # Show error with specific message
            if e.status_code == 403:
                QMessageBox.critical(
                    self, "Permission Denied", 
                    "You don't have permission to view users. Admin role is required.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to load users: {e.message}",
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
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
                # Note: This endpoint is not implemented in the current server API
                # await self.api_client.update_user_status(user_id, not user_data['is_active'])
                
                # For now, update the mock data
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
                # Note: This endpoint is not implemented in the current server API
                # await self.api_client.update_user_role(user_id, new_role)
                
                # For now, update the mock data
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