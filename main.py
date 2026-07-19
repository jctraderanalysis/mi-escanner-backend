import requests
import pandas as pd

def calcular_escanner(simbolo, api_key):
    # 1. Traer los datos de precios históricos de Alpha Vantage (Velas de 15 min, por ejemplo)
    url_precios = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={simbolo}&interval=15min&outputsize=full&apikey={api_key}"
    data_precios = requests.get(url_precios).json()
    
    # Transformar los datos a una tabla manejable (DataFrame)
    time_series = data_precios.get("Time Series (15min)", {})
    df = pd.DataFrame.from_dict(time_series, orient='index').astype(float)
    df = df.iloc[::-1] # Invertir para tener el orden cronológico correcto
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    
    # 2. Calcular las EMAs tal como en tu código MQL4
    df['EMA30'] = df['close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['EMA_Pullback'] = df['close'].ewm(span=50, adjust=False).mean() # MA_Pullback_Period = 50
    
    # Tomar los valores de la última vela cerrada (Vela 1 en MQL4)
    ultima_vela = df.iloc[-2] 
    c1 = ultima_vela['close']
    h1 = ultima_vela['high']
    l1 = ultima_vela['low']
    
    m30, m50, m100, m200 = ultima_vela['EMA30'], ultima_vela['EMA50'], ultima_vela['EMA100'], ultima_vela['EMA200']
    mp = ultima_vela['EMA_Pullback']
    
    estado = "RANGO"
    
    # 3. Aplicar TU lógica analítica exacta
    # Tendencia Alcista
    if m30 > m50 and m50 > m100 and m100 > m200:
        if c1 > m30:
            estado = "COMPRA"
        elif l1 <= mp:
            estado = "PULLBACK"
            
    # Tendencia Bajista
    elif m30 < m50 and m50 < m100 and m100 < m200:
        if c1 < m30:
            estado = "VENTA"
        elif h1 >= mp:
            estado = "PULLBACK"
            
    # Devolver el JSON limpio que va a leer tu App Móvil
    return {
        "simbolo": simbolo,
        "temporalidad": "M15",
        "estado": estado,
        "precio_actual": c1
    }

# Ejemplo de cómo lo vería tu servidor (Usa tu API Key de Alpha Vantage)
# resultado = calcular_escanner("EURUSD", "TU_API_KEY")
# print(resultado)