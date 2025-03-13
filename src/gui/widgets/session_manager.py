from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from utils.async_utils import async_callback
from datetime import datetime, timedelta

class SessionManagerWidget(QWidget):
    """Widget for managing active sessions"""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.sessions = []
        self.users_with_sessions = {}  # Dictionary of users with sessions
        self.current_selected_user_id = None  # Track the currently selected user
        self.setup_ui()
        
        # Create timer to refresh sessions every 30 seconds
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_sessions)
        self.refresh_timer.setInterval(30000)  # 30 seconds
        
        # Start loading
        self.load_sessions()
        self.refresh_timer.start()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Header with refresh button
        header_layout = QHBoxLayout()
        title = QLabel("Active Sessions")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_sessions)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Splitter for users and sessions
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Users list group
        users_group = QGroupBox("Users with Sessions")
        users_layout = QVBoxLayout(users_group)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(3)
        self.users_table.setHorizontalHeaderLabels(["User ID", "Email", "Sessions"])
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.itemClicked.connect(self.on_user_selected)
        
        users_layout.addWidget(self.users_table)
        splitter.addWidget(users_group)
        
        # Sessions list group
        sessions_group = QGroupBox("Active Sessions")
        sessions_layout = QVBoxLayout(sessions_group)
        
        # Sessions table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(4)
        self.sessions_table.setHorizontalHeaderLabels(["Session Token", "Created", "Last Activity", ""])
        self.sessions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sessions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sessions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sessions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        sessions_layout.addWidget(self.sessions_table)
        
        # Add terminate button
        self.terminate_btn = QPushButton("Terminate Selected Session")
        self.terminate_btn.clicked.connect(self.terminate_selected_session)
        self.terminate_btn.setEnabled(False)
        sessions_layout.addWidget(self.terminate_btn)
        
        splitter.addWidget(sessions_group)
        
        layout.addWidget(splitter)
        
        # Status label
        self.status_label = QLabel("Loading sessions...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Set initial splitter sizes (1:2 ratio)
        splitter.setSizes([200, 400])
    
    @async_callback
    async def load_sessions(self, *args):
        """Load active sessions from server"""
        try:
            self.refresh_btn.setEnabled(False)
            self.status_label.setText("Loading sessions...")
            
            # Call API endpoint to get sessions
            if hasattr(self.api_client.endpoints, 'admin_sessions'):
                endpoint = self.api_client.endpoints.admin_sessions
            else:
                endpoint = f"{self.api_client.endpoints.base_url}/api/admin/sessions"
                
            response = await self.api_client._request(
                'GET',
                endpoint,
                include_auth=True
            )
            
            if not isinstance(response, dict) or 'sessions' not in response:
                raise ValueError("Invalid response format")
            
            # Store session data
            self.sessions = response['sessions']
            
            # Process sessions into users
            self.process_sessions()
            
            # Update UI
            self.update_users_table()
            
            # Update status
            self.status_label.setText(f"Loaded {len(self.sessions)} active sessions")
            
            # Clear sessions table if no sessions
            if not self.sessions:
                self.users_table.setRowCount(0)
                self.sessions_table.setRowCount(0)
                self.terminate_btn.setEnabled(False)
            
        except Exception as e:
            print(f"Error loading sessions: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            
            # Clear tables on error
            self.users_table.setRowCount(0)
            self.sessions_table.setRowCount(0)
            self.terminate_btn.setEnabled(False)
            
            # Set a reasonable interval for retrying
            if hasattr(self, 'refresh_timer'):
                current_interval = self.refresh_timer.interval()
                # If already at 30s or more, keep it, otherwise increase to 30s
                if current_interval < 30000:
                    print("Increasing refresh interval due to errors")
                    self.refresh_timer.setInterval(30000)  # 30 seconds
        finally:
            self.refresh_btn.setEnabled(True)
    
    def process_sessions(self):
        """Process sessions into users with sessions"""
        self.users_with_sessions = {}
        
        # Display message if no sessions
        if not self.sessions:
            self.status_label.setText("No active sessions found")
            self.sessions_table.setRowCount(0)  # Clear sessions table
            self.terminate_btn.setEnabled(False)
            return
        
        # Group sessions by user
        for session in self.sessions:
            user_id = session.get('user_id')
            if user_id is None:
                continue
                
            # Convert user_id to string to ensure consistent keys
            user_id = str(user_id)
                
            if user_id not in self.users_with_sessions:
                self.users_with_sessions[user_id] = {
                    'user_id': user_id,
                    'email': session.get('email', 'Unknown'),
                    'role': session.get('role', 'Unknown'),
                    'sessions': []
                }
            
            self.users_with_sessions[user_id]['sessions'].append(session)
            
        # Auto-update the currently selected user's sessions if there was a selection
        if self.current_selected_user_id and self.current_selected_user_id in self.users_with_sessions:
            user_data = self.users_with_sessions[self.current_selected_user_id]
            sessions = user_data['sessions']
            self.update_sessions_table(sessions)
            
            # Find and select the user in the table to highlight it
            self.select_user_in_table(self.current_selected_user_id)
        else:
            # Clear sessions table if selected user no longer exists
            if self.current_selected_user_id and self.current_selected_user_id not in self.users_with_sessions:
                self.sessions_table.setRowCount(0)
                self.terminate_btn.setEnabled(False)
                self.current_selected_user_id = None
                
    def select_user_in_table(self, user_id):
        """Find and select a user in the table by user ID"""
        for row in range(self.users_table.rowCount()):
            item = self.users_table.item(row, 0)
            if item and item.text() == user_id:
                # Select this row
                self.users_table.selectRow(row)
                break
    
    def update_users_table(self):
        """Update the users table"""
        self.users_table.setRowCount(len(self.users_with_sessions))
        
        # Sort users by user ID
        sorted_users = sorted(self.users_with_sessions.items(), key=lambda x: x[0])
        
        for i, (user_id, user_data) in enumerate(sorted_users):
            # User ID
            self.users_table.setItem(i, 0, QTableWidgetItem(str(user_id)))
            
            # Email
            self.users_table.setItem(i, 1, QTableWidgetItem(user_data['email']))
            
            # Sessions count
            sessions_count = len(user_data['sessions'])
            sessions_item = QTableWidgetItem(str(sessions_count))
            self.users_table.setItem(i, 2, sessions_item)
    
    def on_user_selected(self, item):
        """Handle user selection"""
        # Get the user ID from the first column in the same row
        row = item.row()
        user_id_item = self.users_table.item(row, 0)
        if not user_id_item:
            return
            
        user_id = user_id_item.text()
        if not user_id or user_id not in self.users_with_sessions:
            return
            
        # Store the selected user ID
        self.current_selected_user_id = user_id
            
        # Get user's sessions
        user_data = self.users_with_sessions[user_id]
        sessions = user_data['sessions']
        
        # Update sessions table
        self.update_sessions_table(sessions)
    
    def update_sessions_table(self, sessions):
        """Update the sessions table with the given sessions"""
        self.sessions_table.setRowCount(len(sessions))
        
        # Sort sessions by creation time (newest first)
        sorted_sessions = sorted(
            sessions, 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        for i, session in enumerate(sorted_sessions):
            # Session token (truncated for display)
            token = session.get('session_token', '')
            token_display = token[:10] + '...' if len(token) > 10 else token
            token_item = QTableWidgetItem(token_display)
            token_item.setToolTip(token)
            self.sessions_table.setItem(i, 0, token_item)
            
            # Created timestamp
            created_at = session.get('created_at')
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    created_str = created_at
            else:
                created_str = 'Unknown'
            self.sessions_table.setItem(i, 1, QTableWidgetItem(created_str))
            
            # Last activity
            last_activity = session.get('last_activity')
            if last_activity:
                try:
                    activity_dt = datetime.fromisoformat(last_activity)
                    activity_str = activity_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Calculate time since last activity
                    time_since = datetime.now() - activity_dt
                    if time_since < timedelta(minutes=5):
                        activity_item = QTableWidgetItem(activity_str)
                        activity_item.setForeground(QColor('green'))
                    elif time_since < timedelta(minutes=30):
                        activity_item = QTableWidgetItem(activity_str)
                        activity_item.setForeground(QColor('orange'))
                    else:
                        activity_item = QTableWidgetItem(activity_str)
                        activity_item.setForeground(QColor('red'))
                    
                    activity_item.setToolTip(f"Time since: {self.format_timedelta(time_since)}")
                    self.sessions_table.setItem(i, 2, activity_item)
                except ValueError:
                    self.sessions_table.setItem(i, 2, QTableWidgetItem(last_activity))
            else:
                self.sessions_table.setItem(i, 2, QTableWidgetItem('Unknown'))
            
            # Terminate button
            terminate_btn = QPushButton("Terminate")
            terminate_btn.setProperty('session_token', token)
            terminate_btn.clicked.connect(self.on_terminate_clicked)
            self.sessions_table.setCellWidget(i, 3, terminate_btn)
            
        # Enable/disable terminate selected button
        self.terminate_btn.setEnabled(len(sessions) > 0)
    
    def on_terminate_clicked(self):
        """Handle terminate button click"""
        sender = self.sender()
        if not sender or not sender.property('session_token'):
            return
            
        session_token = sender.property('session_token')
        self.terminate_session(session_token)
    
    def terminate_selected_session(self):
        """Terminate the selected session"""
        selected_rows = self.sessions_table.selectedIndexes()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        token_item = self.sessions_table.item(row, 0)
        if not token_item:
            return
            
        # Get the full token from the tooltip
        session_token = token_item.toolTip()
        if not session_token:
            return
            
        self.terminate_session(session_token)
    
    @async_callback
    async def terminate_session(self, session_token):
        """Terminate the specified session"""
        try:
            # Confirm termination
            reply = QMessageBox.question(
                self, 
                "Confirm Termination",
                f"Are you sure you want to terminate the session?\n\nToken: {session_token[:10]}...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            # Call API to terminate session
            if hasattr(self.api_client.endpoints, 'admin_session'):
                endpoint = self.api_client.endpoints.admin_session(session_token)
            else:
                endpoint = f"{self.api_client.endpoints.base_url}/api/admin/sessions/{session_token}"
                
            response = await self.api_client._request(
                'DELETE',
                endpoint,
                include_auth=True
            )
            
            # Show success message
            QMessageBox.information(
                self, 
                "Session Terminated",
                "The session has been terminated successfully.",
                QMessageBox.StandardButton.Ok
            )
            
            # Schedule reload using QTimer instead of directly awaiting
            # This avoids event loop issues
            QTimer.singleShot(500, self.load_sessions)
            
        except Exception as e:
            print(f"Error terminating session: {str(e)}")
            QMessageBox.critical(
                self, 
                "Error",
                f"Failed to terminate session: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
    
    def format_timedelta(self, delta):
        """Format a timedelta into a human-readable string"""
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        return ", ".join(parts)
    
    def hideEvent(self, event):
        """Pause the timer when widget is hidden"""
        try:
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
        except Exception as e:
            print(f"Error stopping timer: {e}")
        super().hideEvent(event)
    
    def showEvent(self, event):
        """Resume the timer when widget is shown"""
        # Use a QTimer for a safer immediate check to prevent thread issues
        QTimer.singleShot(100, self.load_sessions)
        
        try:
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.start()
        except Exception as e:
            print(f"Error starting timer: {e}")
        
        super().showEvent(event)
        
    def __del__(self):
        """Clean up timers on deletion"""
        try:
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")