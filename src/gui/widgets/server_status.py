from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from datetime import datetime, timedelta
from utils.async_utils import async_callback
import json
from typing import Optional

class ServerStatusWidget(QWidget):
    """Widget for displaying server status"""
    
    status_changed = pyqtSignal(bool)  # Signal emitted when status changes (online/offline)
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.last_status = None  # None, True (online), or False (offline)
        self.last_check_time = None
        self.offline_start_time = None
        self.last_offline_period = None
        self.setup_ui()
        
        # Create timer to check server status every 15 seconds
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_server_status)
        self.status_timer.setInterval(15000)  # 15 seconds
        
        # Start checking
        self.check_server_status()
        self.status_timer.start()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Status indicators
        status_layout = QHBoxLayout()
        
        # Server status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setStyleSheet("background-color: gray; border-radius: 8px;")
        status_layout.addWidget(self.status_indicator)
        
        # Status text
        self.status_text = QLabel("Checking server status...")
        status_layout.addWidget(self.status_text)
        
        status_layout.addStretch()
        
        # Last check time
        self.last_check_label = QLabel("Last check: Never")
        status_layout.addWidget(self.last_check_label)
        
        # Manual refresh button
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.check_server_status)
        status_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(status_layout)
        
        # Server info section
        self.server_info_group = QGroupBox("Server Information")
        server_info_layout = QVBoxLayout(self.server_info_group)
        
        # Server details
        self.hostname_label = QLabel("Hostname: Unknown")
        server_info_layout.addWidget(self.hostname_label)
        
        self.platform_label = QLabel("Platform: Unknown")
        server_info_layout.addWidget(self.platform_label)
        
        self.uptime_label = QLabel("Uptime: Unknown")
        server_info_layout.addWidget(self.uptime_label)
        
        # Offline period info
        self.offline_group = QGroupBox("Offline Periods")
        offline_layout = QVBoxLayout(self.offline_group)
        
        self.last_offline_label = QLabel("Last offline period: None detected")
        offline_layout.addWidget(self.last_offline_label)
        
        self.current_offline_label = QLabel()
        self.current_offline_label.setVisible(False)  # Hidden by default
        offline_layout.addWidget(self.current_offline_label)
        
        layout.addWidget(self.server_info_group)
        layout.addWidget(self.offline_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    @async_callback
    async def check_server_status(self, *args):
        """Check server status by calling the API"""
        try:
            self.refresh_btn.setEnabled(False)
            self.last_check_time = datetime.now()
            self.last_check_label.setText(f"Last check: {self.last_check_time.strftime('%H:%M:%S')}")
            
            # Call API endpoint using the proper endpoint method if available
            if hasattr(self.api_client.endpoints, 'admin_system'):
                endpoint = self.api_client.endpoints.admin_system
            else:
                # Fallback for backward compatibility
                endpoint = f"{self.api_client.endpoints.base_url}/api/admin/system"
                
            response = await self.api_client._request(
                'GET', 
                endpoint,
                include_auth=True
            )
            
            # Process response
            if isinstance(response, dict) and response.get('status') == 'online':
                self.update_status(True, response)
            else:
                # Invalid response format
                self.update_status(False)
                
        except Exception as e:
            print(f"Server status check failed: {str(e)}")
            self.update_status(False)
        finally:
            self.refresh_btn.setEnabled(True)
    
    def update_status(self, is_online: bool, data: Optional[dict] = None):
        """Update the UI with server status"""
        # Check if status changed
        status_changed = (self.last_status != is_online)
        old_status = self.last_status
        self.last_status = is_online
        
        if is_online:
            # Server is online
            self.status_indicator.setStyleSheet("background-color: green; border-radius: 8px;")
            self.status_text.setText("Server Status: Online")
            
            # If it was previously offline, calculate the offline period
            if old_status is False and self.offline_start_time:
                offline_duration = datetime.now() - self.offline_start_time
                self.last_offline_period = offline_duration
                self.last_offline_label.setText(
                    f"Last offline period: {self.format_duration(offline_duration)}"
                )
                self.offline_start_time = None
                self.current_offline_label.setVisible(False)
            
            # Update server info if data is provided
            if data:
                self.update_server_info(data)
                
        else:
            # Server is offline
            self.status_indicator.setStyleSheet("background-color: red; border-radius: 8px;")
            self.status_text.setText("Server Status: Offline")
            
            # Clear server info when offline
            self.hostname_label.setText("Hostname: Unavailable")
            self.platform_label.setText("Platform: Unavailable")
            self.uptime_label.setText("Uptime: Unavailable")
            
            # If it just went offline, record the start time
            if old_status is not False:  # True or None (first check)
                self.offline_start_time = datetime.now()
                
            # Update current offline period if tracking an outage
            if self.offline_start_time:
                try:
                    current_duration = datetime.now() - self.offline_start_time
                    self.current_offline_label.setText(
                        f"Current offline period: {self.format_duration(current_duration)}"
                    )
                    self.current_offline_label.setVisible(True)
                except Exception as e:
                    print(f"Error calculating offline duration: {e}")
                    self.current_offline_label.setText("Current offline period: Calculating...")
                    self.current_offline_label.setVisible(True)
        
        # Emit signal if status changed
        if status_changed:
            self.status_changed.emit(is_online)
    
    def update_server_info(self, data: dict):
        """Update server information display"""
        # Update hostname
        if 'hostname' in data:
            self.hostname_label.setText(f"Hostname: {data['hostname']}")
            
        # Update platform
        if 'platform' in data:
            self.platform_label.setText(f"Platform: {data['platform']}")
            
        # Update uptime
        if 'uptime_seconds' in data and data['uptime_seconds']:
            uptime = timedelta(seconds=data['uptime_seconds'])
            self.uptime_label.setText(f"Uptime: {self.format_duration(uptime)}")
        elif 'start_time' in data and data['start_time']:
            try:
                start_time = datetime.fromisoformat(data['start_time'])
                current_time = datetime.fromisoformat(data['server_time'])
                uptime = current_time - start_time
                self.uptime_label.setText(f"Uptime: {self.format_duration(uptime)}")
            except (ValueError, TypeError):
                self.uptime_label.setText("Uptime: Unknown")
    
    def format_duration(self, duration: timedelta) -> str:
        """Format a timedelta into a human-readable string"""
        total_seconds = int(duration.total_seconds())
        
        # For very short durations
        if total_seconds < 60:
            return f"{total_seconds} seconds"
            
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
    
    def hideEvent(self, event):
        """Pause the timer when widget is hidden"""
        try:
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
        except Exception as e:
            print(f"Error stopping timer: {e}")
        super().hideEvent(event)
    
    def showEvent(self, event):
        """Resume the timer when widget is shown"""
        # Use a QTimer for a safer immediate check to prevent thread issues
        QTimer.singleShot(100, self.check_server_status)
        
        try:
            if hasattr(self, 'status_timer'):
                self.status_timer.start()
        except Exception as e:
            print(f"Error starting timer: {e}")
        
        super().showEvent(event)
        
    def __del__(self):
        """Clean up timers on deletion"""
        try:
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")