import yfinance as yf
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

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
            

class NewsFetchSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class NewsFetchTask(QRunnable):
    """
    Fetches news of a given ticker
    """
    
    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker
        self.signals = NewsFetchSignals()

    def run(self):
        try:
            data = yf.Ticker(self.ticker).get_news(count=10)

            if not data:
                self.signals.error.emit(
                    f"No se encontraron noticias para {self.ticker}. "
                )
                return
            
            news = []

            for n in data:
                content = n.get("content", {})
                news.append({
                "title": content.get("title"),
                "link": content.get("canonicalUrl", {}).get("url"),
                "publisher": content.get("provider", {}).get("displayName"),
                "time": content.get("pubDate"),
                "summary": content.get("summary")
                })
            
            #mostrar news en la terminal

            self.signals.finished.emit(news)

        except Exception as e:
            self.signals.error.emit(str(e))