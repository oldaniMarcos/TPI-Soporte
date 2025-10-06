import yfinance as yf
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from google import genai
import os
from dotenv import load_dotenv
import pandas as pd
import indicadores

# QRunnable doesn't support signals so they must be included here
class PriceHistoryFetchSignals(QObject):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)

class PriceHistoryFetchTask(QRunnable):
    """
    Fetches price history.
    Period: 1 day, 1 month, 1 year, year to date, max.
    Intervals vary.
    """
    def __init__(self, ticker: str, period: str):
        super().__init__()
        self.ticker = ticker
        self.signals = PriceHistoryFetchSignals()
        self.period = period

    def run(self):
        
        try:
            
            if(self.period == '1d'):
                df = yf.download(self.ticker, period='1d', interval='5m', progress=False)
            elif(self.period == '1mo'):
                df = yf.download(self.ticker, period='1mo', interval='1h', progress=False)
            elif(self.period == '1y'):
                df = yf.download(self.ticker, period='1y', interval='1d', progress=False)
            elif(self.period == 'ytd'):
                df = yf.download(self.ticker, period='ytd', interval='1d', progress=False)
            elif(self.period == 'max'):
                df = yf.download(self.ticker, period='max', interval='1mo', progress=False)

            if df.empty:
                self.signals.error.emit(
                    f"No se encontraron datos para {self.ticker}. "
                )
                return
            
            self.signals.finished.emit(self.period, df)

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

            self.signals.finished.emit(news)

        except Exception as e:
            self.signals.error.emit(str(e))
            

class GenerateSummarySignals(QObject):
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)

class GenerateSummaryTask(QRunnable):
    """
    Uses Gemini API to generate a brief summary
    """
    
    def __init__(self, ticker: str, news, indicators_data):
        super().__init__()
        
        self.news = news
        self.indicadores = indicators_data
        #load_dotenv()
        self.ticker = ticker
        self.signals = GenerateSummarySignals()
        #self.client = genai.Client( api_key=os.getenv('GEMINI_API_KEY') )

    def run(self):
        try:
            
            load_dotenv()
            client = genai.Client( api_key=os.getenv('GEMINI_API_KEY') )
            
            news_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in self.news])
            
            indicators_text = "\n".join([f"- {name}: {data[1]}" for name, data in self.indicadores.items()])

            prompt = (
                f"Analiza la siguiente información relacionada con {self.ticker} y genera un texto estructurado en tres partes separadas por saltos de línea:\n\n"
                "1. Resumen general: Describe brevemente el activo, y la situación actual del activo.\n"
                "2. Análisis de noticias: Explica qué tendencia o sentimiento reflejan las noticias recientes (positivo, negativo, neutro) y qué temas predominan.\n"
                "3. Análisis de indicadores: Interpreta brevemente los indicadores técnicos y sugiere qué podrían implicar para el comportamiento futuro del activo. No hagas referencia al estado de los indicadores como 'good' 'bad' 'neutro' o 'ninguno'.\n\n"
                "Evita redundancias, no uses negritas, sé directo y mantén cada parte en uno o dos párrafos como máximo.\n\n"
                "--- NOTICIAS ---\n"
                f"{news_text}"
                "\n\n--- INDICADORES ---\n"
                f"{indicators_text}"
            )

            summary = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    
            if not summary:
                self.signals.error.emit(
                    f"No se pudo generar un resumen para {self.ticker}. "
                )
                return

            self.signals.finished.emit(self.ticker, summary.text)

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))

class GenerateDatosIndicadoresSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class GenerateDatosIndicadoresTask(QRunnable):

    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker
        self.signals = GenerateDatosIndicadoresSignals()
        
    def fetch_data(self):

        df = yf.download(self.ticker, period='1y', interval='1d', progress=False)
        if df.empty:
            self.signals.error.emit(f"No se encontraron datos para {self.ticker}. ")
            return None
        return df

    def run(self):
        try:
            df = self.fetch_data()
            if df is None:
                return
            SMA10, estado_SMA10, info_SMA10 = indicadores.promedio_movil(df['Close'], 10)
            SMA50, estado_SMA50, info_SMA50 = indicadores.promedio_movil(df['Close'], 50)
            SMA200, estado_SMA200, info_SMA200 = indicadores.promedio_movil(df['Close'], 200)
            MACD_line, Signal_line, Histograma, estado_MACD, info_MACD = indicadores.macd(df['Close'])
            K_percent, D_percent, estado_Estocastico, info_Estocastico = indicadores.oscilador_estocastico(df) 
            RSI_value, estado_RSI, info_RSI = indicadores.rsi(df['Close'])
            Volatilidad_value, estado_Volatilidad, info_Volatilidad = indicadores.volatilidad(df['Close'])

            datos_indicadores = {
                'SMA10': (SMA10, estado_SMA10, info_SMA10),
                'SMA50': (SMA50, estado_SMA50, info_SMA50),
                'SMA200': (SMA200, estado_SMA200, info_SMA200),
                'MACD': (MACD_line, Signal_line, Histograma, estado_MACD, info_MACD),
                'Estocastico': (K_percent, D_percent, estado_Estocastico, info_Estocastico),
                'RSI': (RSI_value, estado_RSI, info_RSI),
                'Volatilidad': (Volatilidad_value, estado_Volatilidad, info_Volatilidad),
            }
            self.signals.finished.emit(datos_indicadores)
            
        except Exception as e:
            self.signals.error.emit(str(e))        

