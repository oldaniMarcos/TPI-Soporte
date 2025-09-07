import sys
import math
import yfinance as yf
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import (
    Qt, QSize, QRectF, pyqtSignal, QObject, QThreadPool, QRunnable, QPointF  # <-- Añadido QPointF
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTextBrowser, QFrame, QMessageBox, QSizePolicy, QSplitter, QGroupBox,
    QScrollArea, QStackedWidget, QProgressBar
)
from qt_material import apply_stylesheet
import pyqtgraph as pg

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


# QRunnable doesn't support signals so they must be included here
class PriceHistoryFetchSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class PriceHistoryFetchTask(QRunnable):
    """
    Fetches 1 year price history in 1 day intervals
    """
    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker
        self.signals = PriceHistoryFetchSignals()

    def run(self):
        try:
            df = yf.download(self.ticker, period='1y', interval='1d', progress=False) # progress shows progress bar in console, not needed

            if df.empty:
                self.signals.error.emit(
                    f"No se encontraron datos para {self.ticker}. "
                )
                return
            
            self.signals.finished.emit(df)

        except Exception as e:
            self.signals.error.emit(str(e))


class DataFetchSignals(QObject):
    finished = pyqtSignal(object, str)  # StockData | None, error_message ("" si ok)

class DataFetchTask(QRunnable):
    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker
        self.signals = DataFetchSignals()

    def run(self):
        import datetime
        import random
        try:
            # ticker = yf.Ticker(self.ticker)
            # info = ticker.info

            # print(info)

            base_price = 100.0
            prices = []
            val = base_price
            for _ in range(252):
                val *= (1 + random.uniform(-0.01, 0.01))
                prices.append(val)

            today = datetime.date.today()
            dates = [today - datetime.timedelta(days=i) for i in range(252)]
            dates.reverse()

            news_items = [
                f"{self.ticker}: Noticia {i+1} sobre desempeño y estrategia."
                for i in range(5)
            ]

            change = (prices[-1] / prices[0]) - 1
            if change > 0.05:
                rating = "Buena"
            elif change < -0.05:
                rating = "Mala"
            else:
                rating = "Media"

            summary = (
                f"Resumen: La acción {self.ticker} muestra un cambio de "
                f"{change:.2%} en el último año. Sentimiento general '{rating}'."
            )

            data = StockData(
                ticker=self.ticker.upper(),
                dates=dates,
                prices=prices,
                rating=rating,
                news_items=news_items,
                summary=summary
            )
            self.signals.finished.emit(data, "")
        except Exception as e:
            self.signals.finished.emit(None, str(e))


# --------- Widget Ruleta (3 opciones) ---------
class WheelRatingSelector(QWidget):
    ratingChanged = pyqtSignal(str)

    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        self.options = options or ["Buena", "Media", "Mala"]
        self.current_index = 0
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hover = False

    def sizeHint(self):
        return QSize(200, 140)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.current_index = (self.current_index - 1) % len(self.options)
        else:
            self.current_index = (self.current_index + 1) % len(self.options)
        self.ratingChanged.emit(self.current())
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.current_index = (self.current_index + 1) % len(self.options)
            self.ratingChanged.emit(self.current())
            self.update()

    def enterEvent(self, _):
        self._hover = True
        self.update()

    def leaveEvent(self, _):
        self._hover = False
        self.update()

    def setCurrent(self, value: str):
        if value in self.options:
            self.current_index = self.options.index(value)
            self.ratingChanged.emit(self.current())
            self.update()

    def current(self):
        return self.options[self.current_index]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(10, 10, -10, -10)
        size = min(rect.width(), rect.height())
        circle_rect = QRectF(
            rect.center().x() - size / 2,
            rect.center().y() - size / 2,
            size, size
        )

        colors = {
            "Buena": QColor("#16a34a"),
            "Media": QColor("#f59e0b"),
            "Mala": QColor("#dc2626")
        }
        start_angle = -90
        angle_per = 360 / len(self.options)

        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)

        for i, opt in enumerate(self.options):
            angle = start_angle + i * angle_per
            painter.setPen(Qt.PenStyle.NoPen)
            base_color = colors.get(opt, QColor("#6366f1"))
            color = base_color.lighter(120) if i == self.current_index else base_color.darker(110)
            painter.setBrush(QBrush(color))
            painter.drawPie(circle_rect, int(angle * 16), int(angle_per * 16))

            mid_angle_rad = math.radians(angle + angle_per / 2)
            text_r = size * 0.33
            tx = circle_rect.center().x() + text_r * math.cos(mid_angle_rad)
            ty = circle_rect.center().y() + text_r * math.sin(mid_angle_rad)
            painter.setPen(QPen(QColor("white") if i == self.current_index else QColor(255, 255, 255, 200)))
            painter.drawText(
                QRectF(tx - 40, ty - 15, 80, 30),
                Qt.AlignmentFlag.AlignCenter,
                opt
            )

        painter.setPen(QPen(QColor("#334155"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(circle_rect)

        if self._hover:
            painter.setPen(QPen(QColor("#6366f1"), 3))
            painter.drawEllipse(circle_rect.adjusted(3, 3, -3, -3))

        # Marcador superior (triángulo)
        marker_width = 14
        marker_height = 18
        mx = circle_rect.center().x()
        my = circle_rect.top() - 4
        tri_points = [
            QPointF(mx, my),
            QPointF(mx - marker_width / 2, my - marker_height),
            QPointF(mx + marker_width / 2, my - marker_height)
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0f172a"))
        painter.drawPolygon(*tri_points)


# --------- Chart Widget---------
class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # PyQtGraph Widget
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setBackground("w")
        #self.plot.setTitle("Evolución anual", color="#333", size="14pt")
        self.plot.setLabel('left', 'Precio')
        self.plot.setLabel('bottom', 'Días')
        self.plot.getAxis('bottom').setTicks([])
        self.plot.getAxis('left').setTicks([])
        layout.addWidget(self.plot)

    def update_data(self, dates, prices, ticker: str):
        """
        Actualiza la gráfica con datos nuevos.
        dates: lista de pd.Timestamp
        prices: lista de floats
        ticker: string del ticker
        """
        self.plot.clear()

        x = list(range(len(dates)))

        self.plot.plot(
            x, prices,
            pen=pg.mkPen("#2563eb", width=3),
            symbol='o', symbolSize=5, symbolBrush="#2563eb"
        )

        self.plot.setTitle(f"Evolución anual {ticker}", color="#333", size="14pt")

        tick_labels = [(i, dates[i].strftime("%d/%m")) for i in range(0, len(dates), max(1, len(dates)//20))]
        self.plot.getAxis('bottom').setTicks([tick_labels])

        min_price, max_price = min(prices), max(prices)
        step = (max_price - min_price) / 6 if max_price > min_price else 1
        yticks = [(round(min_price + i * step, 2), str(round(min_price + i * step, 2)))
            for i in range(7)]
        self.plot.getAxis('left').setTicks([yticks])

    def reset(self):
        self.plot.clear()
        self.plot.setTitle("")
        self.plot.setLabel('left', 'Precio')
        self.plot.setLabel('bottom', 'Días')
        self.plot.getAxis('bottom').setTicks([])
        self.plot.getAxis('left').setTicks([])

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
        self.history_list.itemClicked.connect(self.on_history_clicked)
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
        self.chart.reset()
        self.central_stack.setCurrentIndex(1)
        self.start_fetch(ticker)

    def start_fetch(self, ticker: str):
        self.current_ticker = ticker
        self.statusBar().showMessage(f"Buscando datos para {ticker} ...")
        task = PriceHistoryFetchTask(ticker)
        task.signals.finished.connect(self.on_price_history_fetched)
        task.signals.error.connect(self.on_price_history_error)
        self.thread_pool.start(task)

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