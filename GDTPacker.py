import sys
import os
import json
import subprocess
import tempfile
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QAction, QStatusBar, QToolTip
)
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt, QTimer
import qtmodern.styles, qtmodern.windows
from modules.gdt_packer import GDTPackerWidget

VERSIONNUM = "1.2.2"

# -------------------------
# Updater Helper Functions
# -------------------------
def get_version_data():
    """
    Loads version metadata from GitHub (raw JSON).
    Expected JSON format:
      {
          "version": "1.1.0",
          "download_url": "https://github.com/YourReleaseRepo/releases/download/v1.1.0/YourApp.exe",
          "updater_download_url": "https://github.com/YourRepo/updater/releases/download/vX/updater.exe"
      }
    """
    try:
        url = "https://raw.githubusercontent.com/Owen-C137/ToolsMain/main/updates.json"
        print("Loading version data from:", url)
        response = requests.get(url)
        if response.status_code == 200:
            version_data = json.loads(response.text)
            print("Version data loaded successfully.")
            return version_data
        else:
            print(f"Failed to load version data, status code: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Failed to load version data: {e}")
        return {}

def get_updater_path(version_data):
    """
    Determines the local path for the updater EXE.
    Downloads the updater if it does not exist.
    """
    updater_dir = os.path.join(os.environ.get("APPDATA", ""), "ToolsMainUpdater")
    if not os.path.exists(updater_dir):
        os.makedirs(updater_dir)
        print(f"Created updater directory: {updater_dir}")
    updater_path = os.path.join(updater_dir, "updater.exe")
    updater_download_url = version_data.get("updater_download_url")
    if updater_download_url:
        if not os.path.exists(updater_path):
            print(f"Updater not found locally. Downloading updater from: {updater_download_url}")
            try:
                r = requests.get(updater_download_url, stream=True)
                if r.status_code == 200:
                    with open(updater_path, "wb") as f:
                        for chunk in r.iter_content(1024):
                            if chunk:
                                f.write(chunk)
                    print("Updater downloaded successfully.")
                    print(f"Updater saved to: {updater_path}")
                else:
                    print(f"Failed to download updater, status code: {r.status_code}")
            except Exception as e:
                print(f"Error downloading updater: {e}")
        else:
            print(f"Updater already exists locally at: {updater_path}")
    else:
        print("No updater_download_url key found in version data.")
    return updater_path

def check_for_updates():
    """
    Checks for a new version by reading the version metadata.
    Returns (remote_version, download_url) if an update is available; otherwise (None, None).
    """
    try:
        url = "https://raw.githubusercontent.com/Owen-C137/ToolsMain/main/updates.json"
        print("Checking for updates...")
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            remote_version = data.get("version")
            download_url = data.get("download_url")
            print(f"Remote version: {remote_version} (Current: {VERSIONNUM})")
            if remote_version and remote_version.strip() != VERSIONNUM.strip():
                return remote_version, download_url
        else:
            print(f"Failed to check for update, status code: {response.status_code}")
        return None, None
    except Exception as e:
        print(f"Update check failed: {e}")
        return None, None

def download_update(download_url):
    """
    Downloads the new executable to a temporary location.
    Returns the full path of the downloaded file.
    """
    try:
        print("Starting download of update...")
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            total_length = response.headers.get('content-length')
            total_length = int(total_length) if total_length is not None else 0
            downloaded = 0
            tmp_dir = tempfile.gettempdir()
            new_exe_path = os.path.join(tmp_dir, "new_version.exe")
            with open(new_exe_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length:
                            percent = (downloaded / total_length) * 100
                            print(f"Downloading update... {percent:.1f}% complete", end="\r")
            print("\nDownload complete.")
            print("New executable downloaded to:", new_exe_path)
            return new_exe_path
        else:
            print("Failed to download update, status code:", response.status_code)
            return None
    except Exception as e:
        print("Download failed:", e)
        return None

def run_update(new_exe_path, updater_exe_path):
    """
    Launches the updater EXE with the current executable and the new executable as arguments.
    """
    try:
        print("Launching external updater...")
        print(f"Updater exe: {updater_exe_path}")
        print(f"Current exe: {sys.executable}")
        print(f"New exe: {new_exe_path}")
        subprocess.Popen([updater_exe_path, sys.executable, new_exe_path])
        print("Exiting current version.")
        sys.exit(0)
    except Exception as e:
        print("Update launch failed:", e)


# -------------------------
# Original Base Code (with Updater Integration)
# -------------------------
# --- Custom Menu Bar that Uses QMenuBar.actionAt() ---
class CustomMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        # We'll use QToolTip from PyQt5 directly.
    
    def mouseMoveEvent(self, event):
        # Use the actionAt() method to find the action under the mouse.
        action = self.actionAt(event.pos())
        if action and action.toolTip():
            # Show the tooltip at the global cursor position.
            QToolTip.showText(self.mapToGlobal(event.pos()), action.toolTip(), self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)
    
    def addMenu(self, icon, title):
        # Create the menu with the icon and an empty text string so no text is shown.
        menu = super().addMenu(icon, "")
        # Set the tooltip text to the provided title.
        tooltip_text = title
        menu.setToolTip(tooltip_text)
        # Also set the tooltip on the underlying QAction.
        menu.menuAction().setToolTip(tooltip_text)
        # Reassign the icon explicitly so it doesn't disappear when clicked.
        menu.menuAction().setIcon(icon)
        return menu

# --- Custom Resizable ModernWindow (as before) ---
class ResizableModernWindow(qtmodern.windows.ModernWindow):
    def __init__(self, widget):
        super().__init__(widget)
        self._resizing = False
        self._resizeMargin = 8  # Margin in pixels for detecting edges
        self._mousePressPos = None
        self._mousePressGeo = None
        self._resizeDirection = (False, False, False, False)  # (left, top, right, bottom)
        self.setMouseTracking(True)
        self.installEventFilter(self)
    
    def _getResizeDirection(self, pos):
        rect = self.rect()
        left = pos.x() <= self._resizeMargin
        top = pos.y() <= self._resizeMargin
        right = (rect.width() - pos.x()) <= self._resizeMargin
        bottom = (rect.height() - pos.y()) <= self._resizeMargin
        return (left, top, right, bottom)
    
    def eventFilter(self, obj, event):
        if event.type() == event.MouseMove:
            if self._resizing:
                diff = event.globalPos() - self._mousePressPos
                geo = self._mousePressGeo.adjusted(0, 0, diff.x(), diff.y())
                self.setGeometry(geo)
                return True
            else:
                direction = self._getResizeDirection(event.pos())
                left, top, right, bottom = direction
                if (left and top) or (right and bottom):
                    self.setCursor(Qt.SizeFDiagCursor)
                elif (right and top) or (left and bottom):
                    self.setCursor(Qt.SizeBDiagCursor)
                elif left or right:
                    self.setCursor(Qt.SizeHorCursor)
                elif top or bottom:
                    self.setCursor(Qt.SizeVerCursor)
                else:
                    self.unsetCursor()
        elif event.type() == event.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                direction = self._getResizeDirection(event.pos())
                if any(direction):
                    self._resizing = True
                    self._resizeDirection = direction
                    self._mousePressPos = event.globalPos()
                    self._mousePressGeo = self.geometry()
                    return True
        elif event.type() == event.MouseButtonRelease:
            if event.button() == Qt.LeftButton and self._resizing:
                self._resizing = False
                self.unsetCursor()
                return True
        return super().eventFilter(obj, event)

def main():
    app = QApplication(sys.argv)
    qtmodern.styles.dark(app)
    
    # Create a QMainWindow for a native menu bar and status bar.
    mainWindow = QMainWindow()
    widget = GDTPackerWidget()
    mainWindow.setCentralWidget(widget)
    mainWindow.setWindowTitle(f"GDT Packer {VERSIONNUM}")
    mainWindow.setWindowIcon(QIcon(os.path.join("resources", "icon.ico")))
    
    # Setup the status bar (optional, for additional messages)
    status_bar = QStatusBar(mainWindow)
    mainWindow.setStatusBar(status_bar)
    
    # Use our custom menu bar that shows tooltips based on the action under the cursor.
    menu_bar = CustomMenuBar(mainWindow)
    mainWindow.setMenuBar(menu_bar)
    
    # Build the File menu with only an icon (empty text) and a tooltip.
    file_menu = menu_bar.addMenu(QIcon("resources/files.ico"), "File")
    
    open_action = QAction(QIcon("resources/open.ico"), "Open", mainWindow)
    open_action.setStatusTip("Open File Menu")
    open_action.hovered.connect(lambda: status_bar.showMessage("Open File Menu"))
    file_menu.addAction(open_action)
    
    save_action = QAction(QIcon("resources/save.ico"), "Save", mainWindow)
    save_action.setStatusTip("Save current settings")
    save_action.hovered.connect(lambda: status_bar.showMessage("Save current settings"))
    file_menu.addAction(save_action)
    
    file_menu.addSeparator()
    
    exit_action = QAction("Exit", mainWindow)
    exit_action.setStatusTip("Exit the application")
    exit_action.setShortcut("Ctrl+Q")
    exit_action.hovered.connect(lambda: status_bar.showMessage("Exit the application"))
    exit_action.triggered.connect(app.quit)
    file_menu.addAction(exit_action)
    
    # Build the Other menu with only an icon (empty text) and a tooltip.
    other_menu = menu_bar.addMenu(QIcon("resources/refresh.ico"), "Other")
    
    option1_action = QAction("Option 1", mainWindow)
    option1_action.setStatusTip("Option 1 description")
    option1_action.hovered.connect(lambda: status_bar.showMessage("Option 1 description"))
    other_menu.addAction(option1_action)
    
    option2_action = QAction("Option 2", mainWindow)
    option2_action.setStatusTip("Option 2 description")
    option2_action.hovered.connect(lambda: status_bar.showMessage("Option 2 description"))
    other_menu.addAction(option2_action)
    
    # Wrap the QMainWindow in our custom resizable modern window.
    mw = ResizableModernWindow(mainWindow)
    mw.show()
    
    # --- Updater Integration ---
    # Delay auto-update check until after the GUI is loaded (1000ms).
    QTimer.singleShot(1000, auto_update)
    
    sys.exit(app.exec_())

def auto_update():
    # Load version metadata from GitHub.
    version_data = get_version_data()
    # Get (or download) the updater EXE.
    updater_exe_path = get_updater_path(version_data)
    # Check if a new version is available.
    remote_version, download_url = check_for_updates()
    if remote_version:
        from PyQt5.QtWidgets import QMessageBox  # Import here to avoid circular issues if needed.
        print("Remote version:", repr(remote_version))
        print("Current version:", repr(VERSIONNUM))
        reply = QMessageBox.question(
            None, "Update Available",
            f"A new version ({remote_version}) is available. Update now?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            new_exe = download_update(download_url)
            if new_exe:
                run_update(new_exe, updater_exe_path)
            else:
                print("Update download failed.")

if __name__ == "__main__":
    main()
