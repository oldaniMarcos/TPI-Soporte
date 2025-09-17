import sys
import math
import yfinance as yf
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import (
    Qt, QSize, QRectF, pyqtSignal, QObject, QThreadPool, QRunnable, QPointF, QUrl
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QDesktopServices
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTextBrowser, QFrame, QMessageBox, QSizePolicy, QSplitter, QGroupBox,
    QScrollArea, QStackedWidget, QProgressBar, QDialog, QDialogButtonBox
)
from qt_material import apply_stylesheet
import pyqtgraph as pg

from tasks import PriceHistoryFetchTask, NewsFetchTask, GenerateSummaryTask

from widgets import WheelRatingSelector, ChartWidget, NewsDetailPopup

# --------- Datos y tareas ---------
# Revisar
@dataclass
class StockData:
    ticker: str
    dates: List
    prices: List[float]
    rating: str
    news_items: List[str]
    summary: str


# --------- Main Window ---------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.resize(1200, 800)
        self.thread_pool = QThreadPool()

        # --- Top bar ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(20, 10, 20, 0)

        self.search_input = QLineEdit()
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 16px;
                font-weight: 600;
            }
        """)
        self.search_input.setPlaceholderText("Ticker (ej: AAPL)")
        self.search_input.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.search_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_input.textEdited.connect(self.capitalize_input)

        self.search_button = QPushButton("Buscar")
        self.search_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_button.clicked.connect(self.on_search_clicked)

        # Allows to press Enter to search
        self.search_input.returnPressed.connect(self.search_button.click)

        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_button)

        # --- Main container ---
        self.central_stack = QStackedWidget()

        # Start page
        start_label = QLabel("🔎 Busque un ticker para comenzar")
        start_label.setStyleSheet("""
            QLabel {
                font-size: 30px;
            }
        """)
        start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.central_stack.addWidget(start_label)

        # Spinner page
        loading_widget = QWidget()
        lv = QVBoxLayout(loading_widget)
        lv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner = QProgressBar()
        spinner.setRange(0, 0)
        spinner.setFixedWidth(400)

        lv.addWidget(spinner)
        self.central_stack.addWidget(loading_widget)

        # Main Page
        self.central_stack.addWidget(self.build_main_content())

        # Ticker Not Found Page
        error_label = QLabel("⛔ No se encontró información del ticker solicitado")
        error_label.setStyleSheet("""
            QLabel {
                font-size: 30px;
            }
        """)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.central_stack.addWidget(error_label)

        # History
        right_panel = QGroupBox("Historial")
        rh_layout = QVBoxLayout(right_panel)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.on_history_clicked)
        rh_layout.addWidget(self.history_list)

        # Main layout
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setContentsMargins(0, 0, 20, 10)
        main_splitter.addWidget(self.central_stack)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 20)
        main_splitter.setStretchFactor(1, 3)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(top_widget, stretch=0)
        wrapper_layout.addWidget(main_splitter, stretch=1)

        self.setCentralWidget(wrapper)
        self.showMaximized()
        self.statusBar().showMessage('')

    def build_main_content(self):
        """Builds the main page"""
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(10, 10, 20, 10)
        central_layout.setSpacing(5)

        self.chart = ChartWidget()
        central_layout.addWidget(self.chart, stretch=4)

        rating_group = QGroupBox("Indicadores")
        rl = QVBoxLayout(rating_group)
        central_layout.addWidget(rating_group, stretch=1)

        news_group = QGroupBox('Últimas Noticias')
        nl = QVBoxLayout(news_group)
        self.news_list = QListWidget()
        self.news_list.itemDoubleClicked.connect(self.on_news_item_double_clicked)
        nl.addWidget(self.news_list)

        summary_group = QGroupBox("Resumen")
        sl = QVBoxLayout(summary_group)
        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(True)
        sl.addWidget(self.summary_view)

        news_summary_container = QWidget()
        ns_layout = QHBoxLayout(news_summary_container)
        ns_layout.setContentsMargins(0, 0, 0, 0)
        ns_layout.addWidget(news_group, stretch=1)
        ns_layout.addWidget(summary_group, stretch=1)

        central_layout.addWidget(news_summary_container, stretch=4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        return scroll

    # Capitalize input text
    def capitalize_input(self, text):
        cursor_position = self.search_input.cursorPosition()
        self.search_input.setText(text.upper())
        self.search_input.setCursorPosition(cursor_position)

    def on_search_clicked(self):
        ticker = self.search_input.text().strip()
        if not ticker:
            QMessageBox.warning(self, "Atención", "Ingrese un ticker.")
            return
        self.central_stack.setCurrentIndex(1)
        self.chart.reset()
        self.news_list.clear()
        self.summary_view.clear()
        self.start_fetch(ticker)

    def start_fetch(self, ticker: str):
        self.current_ticker = ticker
        self.statusBar().showMessage(f"Buscando datos para {ticker} ...")
        
        task = PriceHistoryFetchTask(ticker)
        task.signals.finished.connect(self.on_price_history_fetched)
        task.signals.error.connect(self.on_price_history_error)
        self.thread_pool.start(task)
        
        noticias = NewsFetchTask(ticker)
        noticias.signals.finished.connect(self.on_news_fetched)
        self.thread_pool.start(noticias)
        
        summary = GenerateSummaryTask(ticker)
        summary.signals.finished.connect(self.on_summary_generated)
        summary.signals.error.connect(self.on_summary_error)
        self.thread_pool.start(summary)
    
    def on_price_history_fetched(self, df):
        # Shows main page
        self.central_stack.setCurrentIndex(2)
        self.statusBar().showMessage('Historial descargado correctamente.')

        dates = df.index.to_list()
        prices = df['Close'].iloc[:, 0].tolist()

        self.chart.update_data(dates, prices, self.current_ticker)

    def on_price_history_error(self, msg: str):
        self.central_stack.setCurrentIndex(3)
        self.statusBar().showMessage(msg)
        QMessageBox.warning(self, 'Error', msg)

    def on_news_fetched(self, news: List[dict]):
        self.statusBar().showMessage('Noticias descargadas correctamente.')
        self.news_list.clear()
        #self.summary_view.clear()

        if not news:
            self.news_list.addItem("No se encontraron noticias.")
            return

        for n in news:
            item = QListWidgetItem(f"{n['title']} ({n['publisher']})")
            item.setToolTip(f"Doble clic para ver detalles...\n\n{n['summary']}")
            item.setData(Qt.ItemDataRole.UserRole, n)
            self.news_list.addItem(item)
            """ self.summary_view.append(f"<h3><a href='{n['link']}'>{n['title']}</a></h3>")
            self.summary_view.append(f"<p><i>{n['publisher']} - {n['time']}</i></p>")
            self.summary_view.append(f"<p>{n['summary']}</p>")
            self.summary_view.append("<hr>") """        
    
    def on_summary_generated(self, summary: str):
        self.statusBar().showMessage('Resumen generado correctamente.')
        self.summary_view.clear()
        self.summary_view.append(summary)
        
    def on_summary_error(self, error: str):
        self.statusBar().showMessage('Error al generar el resumen.')
        self.summary_view.clear()
        self.summary_view.append(error)

    def on_news_item_double_clicked(self, item: QListWidgetItem):
        """
        Al hacer doble clic, abre un popup con los detalles de la noticia.
        """
        news_data = item.data(Qt.ItemDataRole.UserRole)
        if news_data:
            # Usamos el nuevo widget en lugar de QDialog
            self.popup = NewsDetailPopup(news_data, self)
            self.popup.show()

    #self.update_history(data.ticker) # recordar esto al final

    def update_history(self, ticker: str):
        if self.history_list.count() > 0:
            last_item = self.history_list.item(self.history_list.count() - 1)
            if last_item.text() == ticker:
                return
        QListWidgetItem(ticker, self.history_list)

    def on_history_clicked(self, item: QListWidgetItem):
        ticker = item.text()
        self.start_fetch(ticker)

    # No utilizado por el momento
    # def on_manual_rating_changed(self, rating: str):
    #     if self.current_data:
    #         self.current_data.rating = rating
    #         self.summary_view.append(f"<p><i>Calificación ajustada manualmente a: {rating}</i></p>")

def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, 'light_cyan_500.xml', invert_secondary=True)
    with open("styles.qss", "r") as f:
        app.setStyleSheet(app.styleSheet() + f.read())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()