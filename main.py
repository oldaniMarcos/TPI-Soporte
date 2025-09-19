import sys
import math
import yfinance as yf
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QSize, QRectF, pyqtSignal, QObject, QThreadPool, QRunnable, QPointF, QUrl, QSettings
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QDesktopServices
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTextBrowser, QFrame, QMessageBox, QSizePolicy, QSplitter, QGroupBox,
    QScrollArea, QStackedWidget, QProgressBar, QDialog, QDialogButtonBox, QGridLayout
)
from qt_material import apply_stylesheet
import pyqtgraph as pg

from tasks import PriceHistoryFetchTask, NewsFetchTask, GenerateSummaryTask

from widgets import WheelRatingSelector, ChartWidget, NewsDetailPopup, IndicatorWidget

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
        self.load_history()
        self.history_list.setUniformItemSizes(True)
        self.history_list.itemDoubleClicked.connect(self.on_history_clicked)
        rh_layout.addWidget(self.history_list)
        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self.clear_history)
        rh_layout.addWidget(clear_btn)

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
        
        # Indicadores de ejemplo, eliminar despues
        ind1 = IndicatorWidget("Promedio Móvil 50d", 135.7, "good")
        ind2 = IndicatorWidget("RSI", 72, "bad")
        ind3 = IndicatorWidget("Volatilidad", 1.25, "neutral")
        ind4 = IndicatorWidget("Promedio Móvil 50d", 135.7, "good")
        ind5 = IndicatorWidget("RSI", 72, "bad")
        ind6 = IndicatorWidget("Volatilidad", 1.25, "neutral")
        ind7 = IndicatorWidget("Promedio Móvil 50d", 135.7, "good")
        ind8 = IndicatorWidget("RSI", 72, "bad")
        ind9 = IndicatorWidget("Volatilidad", 1.25, "neutral")
        ind10 = IndicatorWidget("Promedio Móvil 50d", 135.7, "good")
        ind11 = IndicatorWidget("RSI", 72, "bad")
        ind12 = IndicatorWidget("Volatilidad", 1.25, "neutral")

        rl = QGridLayout(rating_group)
        rl.addWidget(ind1, 0, 0)
        rl.addWidget(ind2, 0, 1)
        rl.addWidget(ind3, 0, 2)
        rl.addWidget(ind4, 0, 3)
        rl.addWidget(ind5, 0, 4)
        rl.addWidget(ind6, 0, 5)
        rl.addWidget(ind7, 1, 0)
        rl.addWidget(ind8, 1, 1)
        rl.addWidget(ind9, 1, 2)
        rl.addWidget(ind10, 1, 3)
        rl.addWidget(ind11, 1, 4)
        rl.addWidget(ind12, 1, 5)
        
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
        
        # Aca hay un problema, las tareas se ejecutan igual aunque el ticker sea invalido
        # Deberian iniciarse si es valido, es decir primero buscar el historial (ya que es la primera tarea)
        # Y despues cuando esa se ejecute correctamente buscar las noticias y generar el resumen (que es lo mas pesado y tiene limite de requests por dia)
        # Hay que poner el resto de las tareas adentro de on_price_history_fetched
        # Estaria bueno agregar una pantalla de carga para cada widget (no el del grafico porque ese aparece primero)
        
        task = PriceHistoryFetchTask(ticker)
        task.signals.finished.connect(self.on_price_history_fetched)
        task.signals.error.connect(self.on_price_history_error)
        self.thread_pool.start(task)
        
        noticias = NewsFetchTask(ticker)
        noticias.signals.finished.connect(self.on_news_fetched)
        noticias.signals.error.connect(self.on_news_error)
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
        self.add_history_entry(self.current_ticker)

    def on_price_history_error(self, msg: str):
        self.central_stack.setCurrentIndex(3)
        self.statusBar().showMessage(msg)
        QMessageBox.warning(self, 'Error', msg)

    def on_news_fetched(self, news: List[dict]):
        self.statusBar().showMessage('Noticias descargadas correctamente.')
        self.news_list.clear()

        if not news:
            self.news_list.addItem("No se encontraron noticias.")
            return

        for n in news:
            item = QListWidgetItem(f"{n['title']} ({n['publisher']})")
            item.setToolTip(f"Doble clic para ver detalles...\n\n{n['summary']}")
            item.setData(Qt.ItemDataRole.UserRole, n)
            self.news_list.addItem(item)      
    
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

    def on_news_error(self, msg: str):
        self.statusBar().showMessage(msg)
        if hasattr(self, "news_list") and self.news_list is not None:
            self.news_list.clear()
            self.news_list.addItem(msg)

    def add_history_entry(self, ticker: str):
        
        # Remove the same ticker if it's already in the list
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == ticker:
                self.history_list.takeItem(i)
                break
        
        item = QListWidgetItem(f"{ticker}")
        item.setData(Qt.ItemDataRole.UserRole, ticker)
        
        self.history_list.insertItem(0, item)
        self.history_list.setCurrentRow(0)
    
    def clear_history(self):
        self.history_list.clear()
        self.statusBar().showMessage("Historial borrado.")

    def on_history_clicked(self, item: QListWidgetItem):
        ticker = item.data(Qt.ItemDataRole.UserRole)  
        self.search_input.setText(ticker)  
        self.chart.reset()
        self.central_stack.setCurrentIndex(1)
        self.start_fetch(ticker)
        
    def save_history(self):
        settings = QSettings('Dashboard', 'Dashboard')
        tickers = []
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            tickers.append(item.data(Qt.ItemDataRole.UserRole))
        settings.setValue('history', tickers)
    
    def load_history(self):
        settings = QSettings('Dashboard', 'Dashboard')
        tickers = settings.value('history', [])
        if tickers:
            for ticker in tickers:
                self.add_history_entry(ticker)
    
    def closeEvent(self, event):
        self.save_history()
        return super().closeEvent(event)

    # No utilizado por el momento
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