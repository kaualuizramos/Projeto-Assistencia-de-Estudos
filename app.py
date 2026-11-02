"""Ponto de entrada do aplicativo desktop Estuda+. Execute com `python app.py`."""

import logging
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from estuda.database import Database
from estuda.ui import StudyWindow


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(Path(__file__).with_name("estuda.log"), encoding="utf-8"), logging.StreamHandler()],
    )
    database = Database(Path(__file__).with_name("assistente_estudos.db"))
    database.initialize()
    application = QApplication([])
    application.setApplicationName("Estuda+")
    application.setFont(QFont("Segoe UI", 10))
    window = StudyWindow(database)
    window.show()
    application.exec()


if __name__ == "__main__":
    main()
