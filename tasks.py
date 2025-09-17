import yfinance as yf
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from google import genai
import os
from dotenv import load_dotenv

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
            

class GenerateSummarySignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class GenerateSummaryTask(QRunnable):
    """
    Uses Gemini API to generate a brief summary
    """
    
    def __init__(self, ticker: str):
        super().__init__()
        
        load_dotenv()
        
        self.ticker = ticker
        self.signals = GenerateSummarySignals()
        self.client = genai.Client( api_key=os.getenv('GEMINI_API_KEY') )

    def run(self):
        try:
            summary = self.client.models.generate_content(
            model="gemini-2.5-flash", contents=f"Quiero un resumen sobre {self.ticker}. Si se trata de un par de trading, solo incluye informacion sobre el activo. Ve al grano, solo quiero informacion lo menos verbosa posible. No uses negritas."
            )

            if not summary:
                self.signals.error.emit(
                    f"No se pudo generar un resumen para {self.ticker}. "
                )
                return

            self.signals.finished.emit(summary.text)

        except Exception as e:
            self.signals.error.emit(str(e))