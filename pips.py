import sys
import os
import subprocess
import tempfile
import traceback
import shutil
import ssl
import json
import random
import string

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QCheckBox,
    QApplication,
)
from PyQt6.QtGui import QPalette, QColor

import certifi
import urllib.request

ACCOUNTS_URL = "https://raw.githubusercontent.com/Skeleton-Archive/cs2-offsets/refs/heads/main/Accounts.json"
CODE_URL = "https://raw.githubusercontent.com/SYFER-eng/Game-Offsets/refs/heads/main/cs2.py"

BASE_FOLDER = r"C:\Syfer-eng-launcher"
SAVE_FILE = os.path.join(BASE_FOLDER, "Saved.txt")


def fetch_json(url):
    """Fetch JSON data from a URL with SSL verification."""
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=context, timeout=10) as response:
        if response.status != 200:
            raise Exception(f"HTTP Error: {response.status}")
        data = response.read().decode()
        return json.loads(data)


def generate_random_filename():
    """Generate a random filename for the temporary Python file."""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"temp_launcher_{random_string}.py"


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.accounts = {}
        self.drag_pos = None

        # Set window properties for frameless, stay-on-top window
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(400, 280)
        
        # Apply the purple/dark theme styling
        self.setStyleSheet(
            """
            QWidget {
                background-color: #120029;
                color: #d6b3ff;
                font-family: Segoe UI, Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: #1a0033;
                border: none;
                border-radius: 7px;
                padding: 8px;
                color: #c186f8;
            }
            QLineEdit:focus {
                border: 1px solid #9754f8;
            }
            QPushButton {
                background-color: #5a1bcc;
                border: none;
                border-radius: 8px;
                padding: 10px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7a27e8;
            }
            QLabel#titleLabel {
                font-size: 22px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #bc9eff;
            }
            QCheckBox {
                font-size: 13px;
                color: #b39fff;
            }
        """
        )
        
        self.initUI()
        self.load_accounts()
        self.load_saved_login()

    def initUI(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Title label
        self.label_title = QLabel("Launcher Login")
        self.label_title.setObjectName("titleLabel")
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Username input field
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Username")

        # Password input field
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Password")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)

        # Save login checkbox
        self.save_login_checkbox = QCheckBox("Save Login")

        # Login button
        self.btn_login = QPushButton("Login")
        self.btn_login.clicked.connect(self.try_login)

        # Add all widgets to the layout
        layout.addWidget(self.label_title)
        layout.addWidget(self.input_username)
        layout.addWidget(self.input_password)
        layout.addWidget(self.save_login_checkbox)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

    def load_accounts(self):
        """Load user accounts from the remote JSON file."""
        try:
            self.accounts = fetch_json(ACCOUNTS_URL)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Loading Accounts",
                f"Could not load accounts from internet.\nLogin disabled.\n\nDetails:\n{e}",
            )
            # Disable login functionality if accounts can't be loaded
            self.input_username.setEnabled(False)
            self.input_password.setEnabled(False)
            self.btn_login.setEnabled(False)

    def load_saved_login(self):
        """Load previously saved login credentials if they exist."""
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 2:
                        self.input_username.setText(lines[0])
                        self.input_password.setText(lines[1])
                        self.save_login_checkbox.setChecked(True)
            except Exception:
                # Ignore errors when loading saved credentials
                pass

    def try_login(self):
        """Attempt to authenticate the user and proceed to code execution."""
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        
        # Validate input fields
        if username == "" or password == "":
            QMessageBox.warning(self, "Invalid input", "Please enter both username and password.")
            return
        
        # Check credentials against loaded accounts
        if username in self.accounts and self.accounts[username] == password:
            # Handle save login functionality
            if self.save_login_checkbox.isChecked():
                os.makedirs(BASE_FOLDER, exist_ok=True)
                try:
                    with open(SAVE_FILE, "w", encoding="utf-8") as f:
                        f.write(username + "\n" + password + "\n")
                except Exception as e:
                    QMessageBox.warning(self, "Save Login Failed", f"Failed to save login info: {e}")
            else:
                # Remove saved login file if unchecked
                try:
                    if os.path.exists(SAVE_FILE):
                        os.remove(SAVE_FILE)
                except Exception:
                    pass

            # Proceed directly to code download and execution
            self.download_run_delete_code()
            self.hide()
        else:
            QMessageBox.warning(self, "Login failed", "Invalid username or password")

    def download_run_delete_code(self):
        """Download Python code from GitHub, execute it, and clean up."""
        temp_path = None
        try:
            # Create temporary file path with random name
            temp_dir = tempfile.gettempdir()
            random_filename = generate_random_filename()
            temp_path = os.path.join(temp_dir, random_filename)

            # Download the Python code from GitHub
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(CODE_URL, context=context, timeout=10) as response:
                if response.status != 200:
                    QMessageBox.warning(
                        self,
                        "Execution Failed",
                        f"Failed to download code from GitHub.\nDetails:\nHTTP Error {response.status}",
                    )
                    self.show()
                    return
                code_source = response.read()

            # Write the downloaded code to the temporary file
            with open(temp_path, "wb") as f:
                f.write(code_source)

            # Find Python interpreter
            python_exe = shutil.which("python") or shutil.which("python3")
            if not python_exe:
                QMessageBox.warning(self, "Execution Failed", "Python interpreter not found on system PATH.")
                self.show()
                return

            # Execute the downloaded Python file
            subprocess.Popen([python_exe, temp_path])

        except urllib.error.HTTPError as http_err:
            QMessageBox.warning(
                self,
                "Execution Failed",
                f"Failed to download code from GitHub.\n\nDetails:\nHTTP Error {http_err.code}: {http_err.reason}",
            )
            self.show()
        except Exception as e:
            tb = traceback.format_exc()
            QMessageBox.warning(
                self,
                "Execution Failed",
                f"Failed to download and execute code.\n\nDetails:\n{e}\n\nTraceback:\n{tb}",
            )
            self.show()
        finally:
            # Schedule cleanup of temporary file after 3 seconds
            if temp_path and os.path.exists(temp_path):
                QtCore.QTimer.singleShot(3000, lambda: self.safe_delete(temp_path))

    @staticmethod
    def safe_delete(path):
        """Safely delete a file, ignoring any errors."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            # Ignore deletion errors
            pass

    # Mouse event handlers for draggable window functionality
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging."""
        if self.drag_pos and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for window dragging."""
        self.drag_pos = None


if __name__ == "__main__":
    # Ensure certifi is installed for SSL verification
    try:
        import certifi  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "certifi"])

    # Create and configure the application
    app = QApplication(sys.argv)

    # Set application-wide color palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(18, 0, 41))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(214, 179, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(26, 0, 51))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(18, 0, 41))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(214, 179, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(214, 179, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(214, 179, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(90, 27, 200))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(151, 84, 248))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    # Create and show the login window
    window = LoginWindow()
    window.show()

    # Start the application event loop
    sys.exit(app.exec())
