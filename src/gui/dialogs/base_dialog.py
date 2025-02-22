from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from api.models import APIError

class BaseDialog(QDialog):
    """Base dialog with common functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
    
    def show_error(self, error: Exception):
        """Display error message"""
        title = "Error"
        if isinstance(error, APIError):
            message = f"API Error: {error.message}"
            if error.status_code == 401:
                title = "Authentication Error"
            elif error.status_code == 403:
                title = "Permission Denied"
            elif error.status_code == 429:
                title = "Rate Limit Exceeded"
        else:
            message = str(error)
            
        QMessageBox.critical(self, title, message)
    
    def show_success(self, message: str):
        """Display success message"""
        QMessageBox.information(self, "Success", message)
    
    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show:
            self.progress_bar.setRange(0, 0)  # Infinite progress
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
    
    def setup_progress_bar(self, layout: QVBoxLayout):
        """Add progress bar to layout"""
        layout.addWidget(self.progress_bar)