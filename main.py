import os
from flask import Flask, jsonify
import requests
import pandas as pd

app = Flask(__name__)

# Tu API Key de Alpha Vantage (puedes cambiarla por la tuya)
API_KEY = "TU_API_KEY_AQUI" 

@app.route('/escanner/<simbolo>', methods=['GET'])
def obtener_escanner(simbolo):
    try:
        # 1. Traer datos de Alpha Vantage
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={simbolo}&interval=15min&outputsize=full&apikey={API_KEY}"
        data = requests.get(url).json()
        
        time_series = data.get("Time Series (15min)", {})
        if not time_series:
            return jsonify({"error": "No se encontraron datos para este símbolo"}), 404
            
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
