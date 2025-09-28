import pandas as pd
import numpy as np
import yfinance as yf

def promedio_movil(data, periodo):
    promedio = data.rolling(window=periodo).mean()

    #si el precio de cierrre es aproximadamente igual al promedio movil
    if abs(data.iloc[-1].item() - promedio.iloc[-1].item()) < 0.01 * promedio.iloc[-1].item():
        estado = "neutral"
    elif data.iloc[-1].item() > promedio.iloc[-1].item():
        estado = "good"
    else:
        estado = "bad"

    return promedio.iloc[-1].item(), estado

def macd(data, periodo_corto=12, periodo_largo=26, periodo_signal=9):
    ema_corto = data.ewm(span=periodo_corto, adjust=False).mean()
    ema_largo = data.ewm(span=periodo_largo, adjust=False).mean()
    macd_line = ema_corto - ema_largo
    signal_line = macd_line.ewm(span=periodo_signal, adjust=False).mean()
    histograma = macd_line - signal_line

    #Histograma aproximada a cero
    if abs(histograma.iloc[-1].item()) < 0.01 * abs(macd_line.iloc[-1].item()):
        estado = "neutral"
    #linea MACD por encima de la linea de señal
    elif macd_line.iloc[-1].item() > signal_line.iloc[-1].item():
        estado = "good"
    else:
        estado = "bad"   

    return macd_line.iloc[-1].item(), signal_line.iloc[-1].item(), histograma.iloc[-1].item(), estado

def oscilador_estocastico(data, periodo=14):
    low_min = data['Low'].rolling(window=periodo).min()
    high_max = data['High'].rolling(window=periodo).max()
    k_percent = 100 * ((data['Close'] - low_min) / (high_max - low_min))
    d_percent = k_percent.rolling(window=3).mean()
    
    K_val = k_percent.iloc[-1].item()
    D_val = d_percent.iloc[-1].item()
    
    K_prev = k_percent.iloc[-2].item()
    D_prev = d_percent.iloc[-2].item()

    if K_val > D_val and K_prev <= D_prev:
        if K_val > 80:
            estado = "bad"
        else:
            estado = "good"
    elif K_val < D_val and K_prev >= D_prev:
        if K_val < 20:
            estado = "neutral"
        else:
            estado = "bad"
    elif K_val > 80:
        estado = "bad"
    elif K_val < 20:
        estado = "good"
    else:
        estado = "ninguno"

    return k_percent.iloc[-1].item(), d_percent.iloc[-1].item(), estado

def rsi(data, periodo=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    #rsi < 30 sobreventa
    if rsi.iloc[-1].item() < 30:
        estado = "good"     
    #rsi > 70 sobrecompra
    elif rsi.iloc[-1].item() > 70:
        estado = "bad"
    else:
        estado = "ninguno"

    return rsi.iloc[-1].item(), estado

def volatilidad(data, periodo=30):
    log_returns = np.log(data / data.shift(1))
    volatilidad = log_returns.rolling(window=periodo).std() * np.sqrt(252)
    
    #volatibilidad baja
    if volatilidad.iloc[-1].item() < 0.15:
        estado = "ninguno"
    #volatibilidad alta
    elif volatilidad.iloc[-1].item() > 0.30:
        estado = "bad"
    else:
        estado = "neutral"

    return volatilidad.iloc[-1].item(), estado

def test():
    data = yf.download("AAPL", period="1y", interval="1d", progress=False)
    print(data['Close'])
    PM10, estado_PM10 = promedio_movil(data['Close'], 10)
    PM50, estado_PM50 = promedio_movil(data['Close'], 50)
    PM200, estado_PM200 = promedio_movil(data['Close'], 200)
    MACD_line, Signal_line, Histograma, estado_MACD = macd(data['Close'])
    K_percent, D_percent, estado_Estocastico = oscilador_estocastico(data) # Pasamos el DataFrame completo
    RSI_value, estado_RSI = rsi(data['Close'])
    Volatilidad_value, estado_Volatilidad = volatilidad(data['Close'])

    print(f"Promedio Móvil 10 días: {PM10} -> Estado: {estado_PM10}")
    print(f"Promedio Móvil 50 días: {PM50} -> Estado: {estado_PM50}")
    print(f"Promedio Móvil 200 días: {PM200} -> Estado: {estado_PM200}")
    print(f"MACD: Line={MACD_line:.2f}, Signal={Signal_line:.2f}, Hist={Histograma:.2f} -> Estado: {estado_MACD}")
    print(f"Oscilador Estocástico: %K={K_percent:.2f}, %D={D_percent:.2f} -> Estado: {estado_Estocastico}")
    print(f"RSI: {RSI_value:.2f} -> Estado: {estado_RSI}")
    print(f"Volatilidad Anualizada: {Volatilidad_value:.2f} -> Estado: {estado_Volatilidad}")

if __name__ == "__main__":
    test()