from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt
from api.models import APIError

class BaseDialog(QDialog):
    """Base dialog with common functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Remove help button from window
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Initialize progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        
        # Set default size
        self.resize(400, 300)
        
        # Center dialog on screen
        screen = self.screen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )
    
    def show_error(self, error: Exception):
        """Display error message with appropriate styling"""
        title = "Error"
        icon = QMessageBox.Icon.Critical
        
        if isinstance(error, APIError):
            if error.status_code == 401:
                title = "Authentication Error"
                message = "Invalid credentials. Please check your email and password."
            elif error.status_code == 403:
                title = "Permission Denied"
                message = "You don't have permission to perform this action."
            elif error.status_code == 429:
                title = "Rate Limit Exceeded"
                message = "Too many attempts. Please try again later."
            elif error.status_code >= 500:
                title = "Server Error"
                message = "Server encountered an error. Please try again later."
            else:
                message = f"API Error: {error.message}"
        else:
            message = str(error)
            
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def show_success(self, message: str):
        """Display success message"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Success")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show:
            self.progress_bar.setRange(0, 0)  # Infinite progress
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
            self.progress_bar.setRange(0, 100)  # Reset to normal range
    
    def setup_progress_bar(self, layout: QVBoxLayout):
        """Add progress bar to layout"""
        layout.addWidget(self.progress_bar)
        
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Close dialog on Escape
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)