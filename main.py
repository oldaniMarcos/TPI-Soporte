import sys
from typing import List

from PyQt6.QtCore import (
    Qt, QThreadPool
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTextBrowser, QMessageBox, QSizePolicy, QSplitter, QGroupBox,
    QScrollArea, QStackedWidget, QProgressBar, QGridLayout
)
from PyQt6.QtGui import QIcon
from qt_material import apply_stylesheet

from tasks import PriceHistoryFetchTask, NewsFetchTask, GenerateSummaryTask, GenerateDatosIndicadoresTask

from widgets import ChartWidget, NewsDetailPopup, IndicatorWidget

from db import SessionLocal, TickerHistory, init_db

# --------- Main Window ---------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("Dashboard")
        self.resize(1020, 600)
        self.setMinimumSize(1020, 600)
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

        # Loading page
        loading_widget = QWidget()
        lv = QVBoxLayout(loading_widget)
        lv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setFixedWidth(400)

        lv.addWidget(progress)
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
        right_panel.setMaximumWidth(250)
        rh_layout = QVBoxLayout(right_panel)
        self.history_list = QListWidget()
        self.load_history()
        self.history_list.setUniformItemSizes(True)
        self.history_list.setTextElideMode(Qt.TextElideMode.ElideRight) # <---
        self.history_list.setWordWrap(False)
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
        self.chart.period_changed.connect(self.on_period_changed)
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.chart.setSizePolicy(size_policy)
        self.chart.setFixedHeight(320)

        central_layout.addWidget(self.chart, stretch=4)

        self.rating_group = QGroupBox("Indicadores")
        self.indicators_layout = QGridLayout(self.rating_group)
        
        central_layout.addWidget(self.rating_group, stretch=1)

        # News stack
        self.news_stack = QStackedWidget()
        self.news_stack.setMinimumHeight(330)

        # News loading screen
        news_loading = QGroupBox('Últimas Noticias')
        nl_loading = QVBoxLayout(news_loading)
        nl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        news_progress = QProgressBar()
        news_progress.setRange(0, 0)
        news_progress.setFixedWidth(200)
        nl_loading.addWidget(news_progress)
        self.news_stack.addWidget(news_loading)

        # News
        news_group = QGroupBox('Últimas Noticias')
        nl_content = QVBoxLayout(news_group)
        self.news_list = QListWidget()
        self.news_list.itemDoubleClicked.connect(self.on_news_item_double_clicked)
        nl_content.addWidget(self.news_list)
        self.news_stack.addWidget(news_group)

        self.news_stack.setCurrentIndex(0)

        # Summary stack
        self.summary_stack = QStackedWidget()

        # Summary loading screen
        summary_loading = QGroupBox('Resumen')
        sl_loading = QVBoxLayout(summary_loading)
        sl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_progress = QProgressBar()
        summary_progress.setRange(0, 0)
        summary_progress.setFixedWidth(200)
        sl_loading.addWidget(summary_progress)
        self.summary_stack.addWidget(summary_loading)

        # Summary
        summary_group = QGroupBox("Resumen")
        sl_content = QVBoxLayout(summary_group)
        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(True)
        sl_content.addWidget(self.summary_view)
        self.summary_stack.addWidget(summary_group)

        #summary_Error
        summary_error = QGroupBox("Resumen")
        sl_error = QVBoxLayout(summary_error)
        error_summary_label = QLabel("⛔ No se pudo generar el resumen")
        error_summary_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
            }
        """)
        error_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl_error.addWidget(error_summary_label)
        summary_error.setLayout(sl_error)
        self.summary_stack.addWidget(summary_error)
        

        self.summary_stack.setCurrentIndex(0)

        news_summary_container = QWidget()
        ns_layout = QHBoxLayout(news_summary_container)
        ns_layout.setContentsMargins(0, 0, 0, 0)
        ns_layout.addWidget(self.news_stack, stretch=1)
        ns_layout.addWidget(self.summary_stack, stretch=1)

        central_layout.addWidget(news_summary_container, stretch=4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
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
        self.statusBar().showMessage(f"Buscando datos para {ticker} ...", 3000)
        
        self.news_stack.setCurrentIndex(0)
        self.summary_stack.setCurrentIndex(0)
        
        self.chart.reset_period()
        
        self._fetched_news_data = None
        self._fetched_indicators_data = None

        price_history = PriceHistoryFetchTask(ticker, period='1y')
        price_history.signals.finished.connect(self.on_price_history_fetched)
        price_history.signals.error.connect(self.on_price_history_error)
        self.thread_pool.start(price_history)
    
    def on_price_history_fetched(self, period, df):
        """
        Shows main page, starts other tasks, updates ticker history chart
        """

        news = NewsFetchTask(self.current_ticker)
        news.signals.finished.connect(self.on_news_fetched)
        news.signals.error.connect(self.on_news_error)
        self.thread_pool.start(news)

        self.central_stack.setCurrentIndex(2)
        self.statusBar().showMessage('Historial descargado correctamente.', 3000)
        
        indicadores = GenerateDatosIndicadoresTask(self.current_ticker)
        indicadores.signals.finished.connect(self.indicators_generated)
        indicadores.signals.error.connect(self.on_indicator_error)
        self.thread_pool.start(indicadores)

        if(period == '1y'):
            self.update_chart(period, df)

    def indicators_generated(self, datos_indicadores):

        self._fetched_indicators_data = datos_indicadores
        # Limpiar el layout actual
        for i in reversed(range(self.indicators_layout.count())):
            self.indicators_layout.itemAt(i).widget().setParent(None) 

        # Agregar nuevos widgets de indicadores
        row, col = 0, 0
        for name, data_tuple in datos_indicadores.items():
            display_value = ""
            state = "neutral"
            info_text = ""

            if name in ['SMA10', 'SMA50', 'SMA200', 'RSI', 'Volatilidad', 'ATR14']:
                # Tupla de (valor, estado, info)
                value, state, info_text = data_tuple
                display_value = f"{value:.2f}"
            
            elif name == 'MACD':
                # Tupla de (linea, señal, hist, estado, info)
                macd_line, signal_line, _, state, info_text = data_tuple
                display_value = f"L: {macd_line:.2f} S: {signal_line:.2f}"

            elif name == 'Estocastico':
                # Tupla de (k, d, estado, info)
                k_percent, d_percent, state, info_text = data_tuple
                display_value = f"%K: {k_percent:.2f} %D: {d_percent:.2f}"

            # Crear y añadir el widget
            widget = IndicatorWidget(name, display_value, state, info_text)
            self.indicators_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= 4:  # 4 indicadores por fila
                col = 0
                row += 1
            self.statusBar().showMessage("Indicadores calculados correctamente.", 3000)

        self._check_if_ready_for_summary()

    def on_indicator_error(self, msg: str):
        self.statusBar().showMessage(msg, 3000)

    def update_chart(self, period, df):
        dates = df.index.to_list()
        prices = df['Close'].iloc[:, 0].tolist()
        self.chart.update_data(dates, prices, self.current_ticker, period)
        self.add_history_entry(self.current_ticker)

    def on_period_changed(self):
        period = self.chart.get_period()
        task = PriceHistoryFetchTask(self.current_ticker, period=period)
        task.signals.finished.connect(self.update_chart)
        task.signals.error.connect(self.on_price_history_error)
        self.thread_pool.start(task)

    def on_price_history_error(self, msg: str):
        self.central_stack.setCurrentIndex(3)
        self.statusBar().showMessage(msg, 3000)
        QMessageBox.warning(self, 'Error', msg)

    def on_news_fetched(self, news: List[dict]):
        self._fetched_news_data = news
        self.statusBar().showMessage('Noticias descargadas correctamente.', 3000)
        self.news_list.clear()

        if not news:
            self.news_list.addItem("No se encontraron noticias.")
            return

        for n in news:
            item = QListWidgetItem(f"{n['title']} ({n['publisher']})")
            item.setToolTip(f"Doble clic para ver detalles...\n\n{n['summary']}")
            item.setData(Qt.ItemDataRole.UserRole, n)
            self.news_list.addItem(item)   

        self.news_stack.setCurrentIndex(1)   

        self._check_if_ready_for_summary()
    
    def _check_if_ready_for_summary(self):
        if self._fetched_news_data is not None and self._fetched_indicators_data is not None:

            news = self._fetched_news_data
            indicators = self._fetched_indicators_data
            ticker = self.current_ticker

            self._fetched_news_data = None
            self._fetched_indicators_data = None


            self._generate_summary(ticker, news, indicators)

    def _generate_summary(self, ticker, news, indicadores):
        self.statusBar().showMessage("Generando resumen...", 3000)
        
        summary_task = GenerateSummaryTask(ticker, news, indicadores)
        summary_task.signals.finished.connect(self.on_summary_generated)
        summary_task.signals.error.connect(self.on_summary_error)
        self.thread_pool.start(summary_task)

    def on_summary_generated(self, ticker: str, summary: str):

        # Ignore old tickers
        if ticker != self.current_ticker:
            return
        
        self.statusBar().showMessage('Resumen generado correctamente.', 3000)
        self.summary_view.clear()
        self.summary_view.append(summary)
        self.summary_stack.setCurrentIndex(1)
        
    def on_summary_error(self, error: str):
        self.statusBar().showMessage('Error al generar el resumen.', 3000)
        self.summary_view.clear()
        self.summary_view.append(error)
        self.summary_stack.setCurrentIndex(2)

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
        self.statusBar().showMessage(msg, 3000)
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
        
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.history_list.insertItem(0, item)
        self.history_list.setCurrentRow(0)
    
    def clear_history(self):
        self.history_list.clear()
        self.statusBar().showMessage("Historial borrado.", 3000)

    def on_history_clicked(self, item: QListWidgetItem):
        ticker = item.data(Qt.ItemDataRole.UserRole)  
        self.search_input.setText(ticker)  
        self.chart.reset()
        self.central_stack.setCurrentIndex(1)
        self.start_fetch(ticker)

    def save_history(self):
        session = SessionLocal()
        session.query(TickerHistory).delete()
        
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            ticker = item.data(Qt.ItemDataRole.UserRole)
            session.add(TickerHistory(ticker=ticker))
            
        session.commit()
        session.close()
    
    def load_history(self):
        session = SessionLocal()
        tickers = session.query(TickerHistory).all()
        for entry in tickers:
            self.add_history_entry(entry.ticker)
        session.close()
    
    def closeEvent(self, event):
        self.save_history()
        return super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/logo.png"))
    apply_stylesheet(app, 'light_cyan_500.xml', invert_secondary=True)
    with open("styles.qss", "r") as f:
        app.setStyleSheet(app.styleSheet() + f.read())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()