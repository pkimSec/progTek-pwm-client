import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.dialogs.login import LoginDialog
from utils.config import AppConfig

def main():
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Password Manager")
    
    # Load configuration
    config = AppConfig.load()
    
    # Show login dialog
    login_dialog = LoginDialog(config)
    login_dialog.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    if sys.platform == "win32":
        # Windows specific event loop configuration
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()