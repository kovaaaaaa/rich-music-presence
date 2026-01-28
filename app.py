import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    win.show()
    app.aboutToQuit.connect(win._stop_worker)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
