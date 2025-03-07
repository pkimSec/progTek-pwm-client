import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import json
from dotenv import load_dotenv

@dataclass
class AppConfig:
    """Application configuration"""
    # API Configuration
    api_base_url: str = "http://localhost:5000"
    api_timeout: int = 30
    
    # UI Configuration
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    
    # Security Configuration
    token_refresh_interval: int = 45  # minutes
    session_timeout: int = 60  # minutes
    
    # User Preferences
    remember_email: bool = False
    last_email: str = ""
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration from environment and config file"""
        # Load .env file if exists
        load_dotenv()
        
        # Get config directory
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        config_file = config_dir / 'config.json'
        
        # Create default config if doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {}
            
        # Create instance with defaults
        instance = cls()
        
        # Override with environment variables
        if api_url := os.getenv('PM_API_URL'):
            instance.api_base_url = api_url
            
        if timeout := os.getenv('PM_API_TIMEOUT'):
            instance.api_timeout = int(timeout)
            
        if theme := os.getenv('PM_THEME'):
            instance.theme = theme
            
        # Override with config file values
        for key, value in config_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
                
        return instance
    
    def save(self):
        """Save current configuration to file"""
        config_dir = Path(os.getenv('APPDATA') or os.getenv('XDG_CONFIG_HOME') or Path.home() / '.config')
        config_dir = config_dir / 'password_manager'
        config_file = config_dir / 'config.json'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        config_data = {
            'api_base_url': self.api_base_url,
            'api_timeout': self.api_timeout,
            'theme': self.theme,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'token_refresh_interval': self.token_refresh_interval,
            'session_timeout': self.session_timeout,
            'remember_email': self.remember_email,
            'last_email': self.last_email
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)