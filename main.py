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
        # 1. Detectar si es Forex o Acción y armar la URL correcta
        simbolo_upper = simbolo.upper()
        
        # Si tiene 6 letras (como EURUSD) o un guion, asumimos que es Forex
        if len(simbolo_upper) == 6 or "-" in simbolo_upper:
            # Limpiamos el guion si existe (transforma EUR-USD en EURUSD)
            fx_sym = simbolo_upper.replace("-", "")
            from_currency = fx_sym[:3]
            to_currency = fx_sym[3:]
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_currency}&to_symbol={to_currency}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series FX (15min)"
        else:
            # Si es una acción (como AAPL)
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={simbolo_upper}&interval=15min&outputsize=compact&apikey={API_KEY}"
            time_series_key = "Time Series (15min)"

        data = requests.get(url).json()
        time_series = data.get(time_series_key, {})
        
        if not time_series:
            # Si Alpha Vantage nos da un mensaje de error o límite, lo mostramos para saber qué pasa
            error_msg = data.get("Note") or data.get("Error Message") or "No se encontraron datos para este símbolo"
            return jsonify({"error": error_msg}), 404
            
        df = pd.DataFrame.from_dict(time_series, orient='index').astype(float)
        df = df.iloc[::-1]
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        
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
