# progTek-pwm-Client

progTek-pwm-Client is the desktop client application for the progTek Password Manager system. It provides a secure, user-friendly interface for managing passwords with client-side encryption ensuring your sensitive data remains protected.

## Features

### Core Authentication & Connectivity
- **Secure Authentication**: JWT token-based authentication with proper session management
- **Registration Process**: Register using invite codes from server administrators
- **Session Management**: Handle session expiration, auto-reconnect, and secure logout

### Vault Management & Encryption
- **Master Password Protection**: Secure your vault with a master password
- **Client-Side Encryption**: All sensitive data is encrypted/decrypted locally
- **PBKDF2 Key Derivation**: Industry-standard key derivation from master password
- **Password Entry Management**: Create, view, edit, and delete password entries
- **Auto-Lock**: Vault locks after configurable period of inactivity

### Security Features
- **Password Generator**: Create strong, customizable passwords
- **Password Strength Meter**: Visual feedback on password strength (powered by zxcvbn)
- **Secure Clipboard Handling**: Automatic clipboard clearing after use
- **Entry History**: Track changes with version history support

### Organization & Usability
- **Category Management**: Organize entries with customizable categories
- **Search & Filter**: Quickly find entries with powerful search capabilities
- **Theme Support**: Light and dark mode themes

## Screenshots
*(Coming soon)*

## Installation

### Prerequisites
- Python 3.12 or higher
- PyQt6
- pip package manager

### Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/pkimSec/progTek-pwm-Client.git
   cd progTek-pwm-Client
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python run.py
   ```

### Connection to Server
To use this client, you'll need a running instance of the [progTek-pwm-Server](https://github.com/pkimSec/progTek-pwm-Server). Configure the client to connect to your server instance by entering the server URL in the login dialog.

## Development

### Project Structure
```
progTek-pwm-Client/
├── src/                    # Source code
│   ├── api/                # API client for server communication
│   │   ├── client.py       # API client implementation
│   │   ├── endpoints.py    # API endpoint configuration
│   │   └── models.py       # Data models
│   ├── crypto/             # Cryptography utilities
│   ├── gui/                # User interface
│   │   ├── dialogs/        # Dialog windows
│   │   ├── views/          # Main application views
│   │   └── widgets/        # Reusable UI components
│   ├── utils/              # Utility functions
│   └── main.py             # Application entry point
├── tests/                  # Test suite
├── assets/                 # Application assets
│   └── styles/             # UI styles
├── requirements.txt        # Python dependencies
├── run.py                  # Launcher script
└── README.md
```

### Running Tests
```
pytest
```

## Current Development Status

This project is under active development. The client implements a phased approach according to the development plan:

### Phase 1: Core Authentication & Connectivity ✅
- Login Dialog & Authentication Flow
- Registration Process with invite codes

### Phase 2: Vault Management & Encryption 🔄
- Password Entry List & Management
- Entry Creation & Editing

### Phase 3: Security Features 🔄
- Password Generator
- Password Strength Meter
- Secure Data Handling

### Phase 4: Polish & Advanced Features 📋
- Settings Management
- Admin Functions
- Import/Export Functionality

## Planned Features

- **Offline Mode**: Cache encrypted vault data for offline access
- **Password Health Analysis**: Check for weak or reused passwords
- **Advanced UX Improvements**: Quick copy buttons, keyboard shortcuts
- **Enhanced Security**: Auto-clear clipboard, panic button, screen masking

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [cryptography](https://cryptography.io/) - Cryptographic primitives
- [zxcvbn](https://github.com/dropbox/zxcvbn) - Password strength estimation
- [progTek-pwm-Server](https://github.com/pkimSec/progTek-pwm-Server) - Server component