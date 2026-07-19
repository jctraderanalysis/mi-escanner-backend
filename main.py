import os
from flask import Flask, jsonify, request
import yfinance as yf
import pandas as pd

app = Flask(__name__)

@app.route('/escanner/<simbolo>', methods=['GET'])
def obtener_escanner(simbolo):
    try:
        simbolo_upper = simbolo.upper().replace("-", "").replace("/", "")
        ticker_yahoo = ""

        # 1. CAPTURAR EMAs DINÁMICAS DESDE LA APP (Con valores por defecto si no se envían)
        periodo_ema9 = int(request.args.get('ema9', 9))
        periodo_ema21 = int(request.args.get('ema21', 21))
        periodo_ema50 = int(request.args.get('ema50', 50))
        periodo_ema200 = int(request.args.get('ema200', 200))

        # 2. TRADUCIR EL SÍMBOLO AL FORMATO DE YAHOO FINANCE
        if "XAU" in simbolo_upper or simbolo_upper == "GLD":
            ticker_yahoo = "GC=F"  
        elif any(crypto in simbolo_upper for crypto in ["BTC", "ETH", "SOL", "XRP", "ADA"]):
            base = simbolo_upper.replace("USD", "") if "USD" in simbolo_upper else simbolo_upper
            ticker_yahoo = f"{base}-USD"
        elif len(simbolo_upper) == 6:
            ticker_yahoo = f"{simbolo_upper}=X"
        else:
            ticker_yahoo = simbolo_upper

        # 3. DESCARGAR DATOS
        ticker = yf.Ticker(ticker_yahoo)
        df = ticker.history(interval="15m", period="5d")

        if df.empty:
            return jsonify({"error": f"No se encontraron datos en Yahoo Finance para el ticker: {ticker_yahoo}"}), 404

        df.columns = [col.lower() for col in df.columns]

        # 4. CÁLCULO DE LAS EMAs CONFIGURABLES
        df['ema9'] = df['close'].ewm(span=periodo_ema9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=periodo_ema21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=periodo_ema50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=periodo_ema200, adjust=False).mean()

        ultima_vela = df.iloc[-1]
        vela_anterior = df.iloc[-2]  # Necesaria para detectar el cruce/toque del pullback
        
        precio_actual = float(ultima_vela['close'])
        ema9_val = float(ultima_vela['ema9'])
        ema21_val = float(ultima_vela['ema21'])
        ema50_val = float(ultima_vela['ema50'])
        ema200_val = float(ultima_vela['ema200'])

        # 5. ESTRATEGIA EXTREMA: TENDENCIA Y PULLBACK EN EMA 50
        # Tendencias Estructurales de las Medias
        estructura_alcista = ema9_val > ema21_val > ema50_val > ema200_val
        estructura_bajista = ema9_val < ema21_val < ema50_val < ema200_val

        # DETECCIÓN DE PULLBACK EN LA EMA 50:
        # Pullback Alcista: Tendencia mayor es alcista, pero el precio baja a testear o tocar la EMA 50
        pullback_alcista = estructura_alcista and (ultima_vela['low'] <= ema50_val and precio_actual >= ema50_val)
        
        # Pullback Bajista: Tendencia mayor es bajista, pero el precio sube a testear o tocar la EMA 50
        pullback_bajista = estructura_bajista and (ultima_vela['high'] >= ema50_val and precio_actual <= ema50_val)

        # Asignación del Estado final para tus botones
        if pullback_alcista:
            estado = "PULLBACK ALCISTA"
        elif pullback_bajista:
            estado = "PULLBACK BAJISTA"
        elif estructura_alcista and precio_actual > ema9_val:
            estado = "ALCISTA"
        elif estructura_bajista and precio_actual < ema9_val:
            estado = "BAJISTA"
        else:
            estado = "NEUTRO"

        # 6. RESPUESTA DINÁMICA
        return jsonify({
            "simbolo": simbolo_upper,
            "ticker_usado": ticker_yahoo,
            "precio": round(precio_actual, 5),
            "estado": estado,
            "emas_configuradas": {
                f"ema{periodo_ema9}": round(ema9_val, 5),
                f"ema{periodo_ema21}": round(ema21_val, 5),
                f"ema{periodo_ema50}": round(ema50_val, 5),
                f"ema{periodo_ema200}": round(ema200_val, 5)
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
