from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
    QCheckBox, QLineEdit, QGroupBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard, QGuiApplication

import random
import string

class PasswordGenerator(QDialog):
    """Dialog for generating secure passwords"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.generated_password = ""
        self.setup_ui()
        self.generate()
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Password Generator")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Password display
        password_group = QGroupBox("Generated Password")
        password_layout = QVBoxLayout()
        
        self.password_field = QLineEdit()
        self.password_field.setReadOnly(True)
        password_layout.addWidget(self.password_field)
        
        # Copy button
        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        copy_layout.addWidget(self.copy_btn)
        password_layout.addLayout(copy_layout)
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()
        
        # Length slider
        length_layout = QVBoxLayout()
        
        self.length_label = QLabel("Length: 16")
        length_layout.addWidget(self.length_label)
        
        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(8, 64)
        self.length_slider.setValue(16)
        self.length_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.length_slider.setTickInterval(4)
        self.length_slider.valueChanged.connect(self.on_length_changed)
        length_layout.addWidget(self.length_slider)
        
        options_layout.addRow("Length:", length_layout)
        
        # Character options
        self.include_uppercase = QCheckBox("Uppercase (A-Z)")
        self.include_uppercase.setChecked(True)
        self.include_uppercase.stateChanged.connect(self.generate)
        options_layout.addRow("", self.include_uppercase)
        
        self.include_lowercase = QCheckBox("Lowercase (a-z)")
        self.include_lowercase.setChecked(True)
        self.include_lowercase.stateChanged.connect(self.generate)
        options_layout.addRow("", self.include_lowercase)
        
        self.include_digits = QCheckBox("Digits (0-9)")
        self.include_digits.setChecked(True)
        self.include_digits.stateChanged.connect(self.generate)
        options_layout.addRow("", self.include_digits)
        
        self.include_symbols = QCheckBox("Symbols (!@#$...)")
        self.include_symbols.setChecked(True)
        self.include_symbols.stateChanged.connect(self.generate)
        options_layout.addRow("", self.include_symbols)
        
        self.exclude_similar = QCheckBox("Exclude similar characters (i, l, 1, L, o, 0, O)")
        self.exclude_similar.setChecked(True)
        self.exclude_similar.stateChanged.connect(self.generate)
        options_layout.addRow("", self.exclude_similar)
        
        # Custom excluded characters
        self.exclude_chars = QLineEdit()
        self.exclude_chars.setPlaceholderText("e.g. {}[]()/'\"\\")
        self.exclude_chars.textChanged.connect(self.generate)
        options_layout.addRow("Exclude:", self.exclude_chars)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("Generate New")
        self.generate_btn.clicked.connect(self.generate)
        button_layout.addWidget(self.generate_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.use_btn = QPushButton("Use Password")
        self.use_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.use_btn)
        
        layout.addLayout(button_layout)
    
    def on_length_changed(self, value):
        """Handle length slider value change"""
        self.length_label.setText(f"Length: {value}")
        self.generate()
    
    def generate(self):
        """Generate a password with the current settings"""
        # Get length
        length = self.length_slider.value()
        
        # Get character sets
        chars = ""
        
        if self.include_uppercase.isChecked():
            uppercase = string.ascii_uppercase
            if self.exclude_similar.isChecked():
                uppercase = ''.join(c for c in uppercase if c not in 'IO')
            chars += uppercase
        
        if self.include_lowercase.isChecked():
            lowercase = string.ascii_lowercase
            if self.exclude_similar.isChecked():
                lowercase = ''.join(c for c in lowercase if c not in 'ilo')
            chars += lowercase
        
        if self.include_digits.isChecked():
            digits = string.digits
            if self.exclude_similar.isChecked():
                digits = ''.join(c for c in digits if c not in '01')
            chars += digits
        
        if self.include_symbols.isChecked():
            symbols = string.punctuation
            # Remove any excluded characters
            exclude = self.exclude_chars.text()
            symbols = ''.join(c for c in symbols if c not in exclude)
            chars += symbols
        
        # If no character sets selected, use lowercase as fallback
        if not chars:
            chars = string.ascii_lowercase
        
        # Generate password
        self.generated_password = ''.join(random.choice(chars) for _ in range(length))
        
        # Display generated password
        self.password_field.setText(self.generated_password)
    
    def copy_to_clipboard(self):
        """Copy generated password to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.generated_password)