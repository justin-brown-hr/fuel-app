import sys
from pathlib import Path

# Allow running as `python src/main.py` from project root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.theme import apply_app_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_app_theme(app)
    app.setApplicationName("Fuel Reconcile")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
