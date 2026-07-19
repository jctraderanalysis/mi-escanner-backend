import os
from flask import Flask, jsonify
import requests
import pandas as pd

app = Flask(__name__)

# Tu API Key de Alpha Vantage (puedes cambiarla por la tuya)
API_KEY = "BQ3V0609A135ESMI" 

@app.route('/escanner/<simbolo>', methods=['GET'])
def obtener_escanner(simbolo):
    try:
        simbolo_upper = simbolo.upper().replace("-", "")
        
        # 1. DETECTAR EL TIPO DE ACTIVO Y ARMAR LA URL CORRECTA
        
        # CASO A: CRIPTOMONEDAS (Si empieza con BTC, ETH, SOL, etc. y termina en USD)
        if any(crypto in simbolo_upper for crypto in ["BTC", "ETH", "SOL", "XRP", "ADA"]):
            # Para Crypto en minutos, Alpha Vantage usa CRYPTO_INTRADAY
            market = "USD"
            # Extraemos la moneda base (ej: BTC)
            coin = simbolo_upper.replace("USD", "") if "USD" in simbolo_upper else simbolo_upper
            url = f"https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol={coin}&market={market}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series Crypto (15min)"
            
        # CASO B: ORO (XAUUSD o si usas el ETF GLD)
        elif "XAU" in simbolo_upper or simbolo_upper == "GLD":
            # El oro físico spot como XAU/USD a veces requiere cuenta premium en intradía en Alpha Vantage.
            # Como alternativa infalible para cuentas gratis, usamos el ETF del Oro (GLD) que se mueve idéntico.
            ticker = "GLD" if simbolo_upper == "XAUUSD" else simbolo_upper
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series (15min)"
            
        # CASO C: FOREX (Si tiene 6 letras como EURUSD, GBPUSD, USDJPY)
        elif len(simbolo_upper) == 6:
            from_currency = simbolo_upper[:3]
            to_currency = simbolo_upper[3:]
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_currency}&to_symbol={to_currency}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series FX (15min)"
            
        # CASO D: ACCIONES (Por si acaso, ej: AAPL, TSLA)
        else:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={simbolo_upper}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series (15min)"

        # 2. PETICIÓN AL SERVIDOR
        data = requests.get(url).json()
        time_series = data.get(time_series_key, {})
        
        if not time_series:
            error_msg = data.get("Note") or data.get("Error Message") or f"No se encontraron datos intradía para {simbolo}. Nota: Las cuentas gratis de Alpha Vantage limitan las peticiones por minuto."
            return jsonify({"error": error_msg}), 404
        
        # 2. Calcular EMAs exactas de tu indicador
        df['EMA30'] = df['close'].ewm(span=30, adjust=False).mean()
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['EMA_Pullback'] = df['close'].ewm(span=50, adjust=False).mean()
        
        ultima_vela = df.iloc[-2]
        c1 = ultima_vela['close']
        h1 = ultima_vela['high']
        l1 = ultima_vela['low']
        
        m30 = ultima_vela['EMA30']
        m50 = ultima_vela['EMA50']
        m100 = ultima_vela['EMA100']
        m200 = ultima_vela['EMA200']
        mp = ultima_vela['EMA_Pullback']
        
        estado = "RANGO"
        
        # 3. Lógica analítica exacta de MQL4
        if m30 > m50 and m50 > m100 and m100 > m200:
            if c1 > m30:
                estado = "COMPRA"
            elif l1 <= mp:
                estado = "PULLBACK"
        elif m30 < m50 and m50 < m100 and m100 < m200:
            if c1 < m30:
                estado = "VENTA"
            elif h1 >= mp:
                estado = "PULLBACK"
                
        return jsonify({
            "simbolo": simbolo,
            "temporalidad": "M15",
            "estado": estado,
            "precio_actual": c1
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"mensaje": "Servidor del escáner activo y corriendo perfectamente"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
