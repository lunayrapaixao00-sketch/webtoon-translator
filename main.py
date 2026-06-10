import sys
import os

import numpy as np
import cv2
import mss
import easyocr
import deepl

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPixmap,
    QIcon,
    QPen
)

from dotenv import load_dotenv

from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QTextEdit
)


load_dotenv()
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")


class AreaSelector(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selection_rect = QRect()

        self.setWindowTitle("Selecionar área")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.9)
        self.showFullScreen()

    def mousePressEvent(self, event):
        self.start_point = event.position().toPoint()
        self.end_point = self.start_point
        self.update()

    def mouseMoveEvent(self, event):
        self.end_point = event.position().toPoint()
        self.selection_rect = QRect(self.start_point, self.end_point).normalized()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end_point = event.position().toPoint()
        self.selection_rect = QRect(self.start_point, self.end_point).normalized()

        area = {
            "top": self.selection_rect.y(),
            "left": self.selection_rect.x(),
            "width": self.selection_rect.width(),
            "height": self.selection_rect.height()
        }

        self.callback(area)
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor("B388EB"))
        pen.setWidth(4)

        painter.setPen(pen)
        painter.drawRect(self.selection_rect)


class WebtoonTranslator(QWidget):
    def __init__(self):
        super().__init__()
        from PySide6.QtGui import QIcon
        self.setWindowTitle("Webtoon Screen Translator")
        self.setWindowIcon(QIcon("assets/logo.png"))
        self.setGeometry(80, 80, 430, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QWidget {
                background-color: #FFF7FB;
                font-family: Arial;
                font-size: 14px;
            }

            QPushButton {
                background-color: #B388EB;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #9B6DD6;
            }

            QTextEdit {
                background-color: white;
                Color: #2B2B2B;
                border: 2px solid #E4C1F9;
                border-radius: 10px;
                padding: 8px;
            }
        """)

        self.selected_area = None
        self.last_text = ""

        self.reader = easyocr.Reader(["en"], gpu=False)

        if not DEEPL_API_KEY:
            raise ValueError("A chave DEEPL_API_KEY não foi encontrada no arquivo .env.")

        self.translator = deepl.Translator(DEEPL_API_KEY)

        self.area_button = QPushButton("Selecionar área da tela")
        self.area_button.clicked.connect(self.open_area_selector)

        self.capture_button = QPushButton("Capturar e traduzir")
        self.capture_button.clicked.connect(self.capture_and_translate)

        self.clear_button = QPushButton("Limpar tradução")
        self.clear_button.clicked.connect(self.clear_result)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText(
            "Selecione uma área da webtoon para traduzir."
        )

        logo = QLabel()
        pixmap = QPixmap("assets/logo.png")

        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                60,
                60,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            logo.setPixmap(pixmap)

        logo.setAlignment(Qt.AlignCenter)
        logo.setMaximumHeight(70)

        title = QLabel("Webtoon Translator")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #2B2B2B;
        """)

        layout = QVBoxLayout()
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(self.area_button)
        layout.addWidget(self.capture_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.result_box)

        self.setLayout(layout)

    def open_area_selector(self):
        self.hide()
        QApplication.processEvents()
        self.selector = AreaSelector(self.set_selected_area)
        self.selector.show()

    def set_selected_area(self, area):
        self.selected_area = area
        self.last_text = ""
        self.show()

        self.result_box.setText(
            f"Área selecionada.\n\n"
            f"Agora clique em 'Capturar e traduzir'.\n\n"
            f"Top: {area['top']}\n"
            f"Left: {area['left']}\n"
            f"Largura: {area['width']}\n"
            f"Altura: {area['height']}"
        )

    def capture_screen(self):
        if not self.selected_area:
            return None

        self.hide()
        QApplication.processEvents()

        with mss.mss() as sct:
            screenshot = sct.grab(self.selected_area)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        self.show()
        QApplication.processEvents()

        return img

    def extract_text(self, image):
        results = self.reader.readtext(
            image,
            detail=1,
            paragraph=True,
            decoder="greedy",
            batch_size=1,
            workers=0
        )

        texts = []

        for item in results:
            text = item[1].strip()

            if len(text) > 1:
                texts.append(text)

        return " ".join(texts).strip()

    def translate_text(self, text):
        try:
            result = self.translator.translate_text(
                text,
                source_lang="EN",
                target_lang="PT-BR"
            )
            return result.text
        except Exception as error:
            return f"Erro ao traduzir: {error}"

    def capture_and_translate(self):
        if not self.selected_area:
            self.result_box.setText("Primeiro selecione uma área da tela.")
            return

        self.result_box.setText("Capturando e lendo texto... aguarde.")
        QApplication.processEvents()

        image = self.capture_screen()

        if image is None:
            self.result_box.setText("Erro ao capturar a área.")
            return

        original_text = self.extract_text(image)

        if not original_text:
            self.result_box.setText("Nenhum texto encontrado.")
            return

        if original_text == self.last_text:
            self.result_box.append("\nMesmo texto detectado. Tradução não refeita.")
            return

        self.last_text = original_text

        self.result_box.setText("Traduzindo com DeepL... aguarde.")
        QApplication.processEvents()

        translated_text = self.translate_text(original_text)

        self.result_box.setText(
            f"EN:\n{original_text}\n\n"
            f"PT-BR:\n{translated_text}"
        )

    def clear_result(self):
        self.last_text = ""
        self.result_box.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebtoonTranslator()
    window.show()
    sys.exit(app.exec())