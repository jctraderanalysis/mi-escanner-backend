import os
from flask import Flask, jsonify
import yfinance as yf
import pandas as pd

app = Flask(__name__)

@app.route('/escanner/<simbolo>', methods=['GET'])
def obtener_escanner(simbolo):
    try:
        simbolo_upper = simbolo.upper().replace("-", "").replace("/", "")
        ticker_yahoo = ""

        # 1. TRADUCIR EL SÍMBOLO AL FORMATO DE YAHOO FINANCE
        
        # CASO A: ORO
        if "XAU" in simbolo_upper or simbolo_upper == "GLD":
            ticker_yahoo = "GC=F"  # Futuros del Oro en tiempo real
            
        # CASO B: CRIPTOMONEDAS
        elif any(crypto in simbolo_upper for crypto in ["BTC", "ETH", "SOL", "XRP", "ADA"]):
            # Si escribes BTCUSD lo transforma en BTC-USD
            base = simbolo_upper.replace("USD", "") if "USD" in simbolo_upper else simbolo_upper
            ticker_yahoo = f"{base}-USD"
            
        # CASO C: FOREX (6 letras como EURUSD)
        elif len(simbolo_upper) == 6:
            ticker_yahoo = f"{simbolo_upper}=X"
            
        # CASO D: ACCIONES (Ej: AAPL, TSLA)
        else:
            ticker_yahoo = simbolo_upper

        # 2. DESCARGAR DATOS INTRADÍA DE 15 MINUTOS
        # Pedimos el intervalo de 15m y los datos de los últimos 5 días
        ticker = yf.Ticker(ticker_yahoo)
        df = ticker.history(interval="15m", period="5d")

        if df.empty:
            return jsonify({"error": f"No se encontraron datos en Yahoo Finance para el ticker: {ticker_yahoo}"}), 404

        # Limpiamos los nombres de las columnas para asegurar compatibilidad
        df.columns = [col.lower() for col in df.columns]

        # 3. CÁLCULO DE LAS EMAs (Tu lógica de análisis)
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

        # Tomamos el último registro cerrado para el análisis
        ultima_vela = df.iloc[-1]
        
        precio_actual = float(ultima_vela['close'])
        ema9_val = float(ultima_vela['ema9'])
        ema21_val = float(ultima_vela['ema21'])
        ema50_val = float(ultima_vela['ema50'])
        ema200_val = float(ultima_vela['ema200'])

        # Lógica de Tendencia / Estado
        if precio_actual > ema9_val > ema21_val > ema50_val > ema200_val:
            estado = "COMPRA"
        elif precio_actual < ema9_val < ema21_val < ema50_val < ema200_val:
            estado = "VENTA"
        elif ema9_val > ema21_val and precio_actual < Sc := ema21_val:
            estado = "PULLBACK"
        else:
            estado = "RANGO"

        # 4. RESPUESTA LIMPIA PARA FLUTTERFLOW
        return jsonify({
            "simbolo": simbolo_upper,
            "ticker_usado": ticker_yahoo,
            "precio": round(precio_actual, 5),
            "estado": estado,
            "emas": {
                "ema9": round(ema9_val, 5),
                "ema21": round(ema21_val, 5),
                "ema50": round(ema50_val, 5),
                "ema200": round(ema200_val, 5)
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
