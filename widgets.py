import math
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QSize, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont,QDesktopServices
from PyQt6.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox
from PyQt6.QtCore import QUrl



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

class NewsDetailPopup(QWidget):
    """
    Un widget emergente para mostrar los detalles de una noticia sin usar QDialog.
    """
    def __init__(self, news_item: dict, parent=None):
        super().__init__(parent)
        self.news_item = news_item

        # Configurar como una ventana de herramientas flotante que aparece sobre la principal
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Detalle de la Noticia")
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Título
        title_label = QLabel(self.news_item.get('title', 'Sin título'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Publicador y fecha
        meta_text = f"<i>{self.news_item.get('publisher', '')} - {self.news_item.get('time', '')}</i>"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: #555;")
        layout.addWidget(meta_label)

        # Resumen
        summary_label = QLabel(self.news_item.get('summary', 'No hay resumen disponible.'))
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label, stretch=1) # Ocupa el espacio disponible

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Empuja los botones a la derecha

        open_button = QPushButton("Abrir Noticia")
        open_button.clicked.connect(self.open_link)
        
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)

        button_layout.addWidget(open_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def open_link(self):
        """Abre el enlace de la noticia en el navegador y cierra el popup."""
        link = self.news_item.get('link')
        if link:
            QDesktopServices.openUrl(QUrl(link))
        self.close()