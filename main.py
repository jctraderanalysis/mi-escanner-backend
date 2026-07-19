import os
from flask import Flask, jsonify, request
import yfinance as yf
import pandas as pd

app = Flask(__name__)

# Mapeo de temporalidades estándar a formato de Yahoo Finance (intervalo, periodo de datos a pedir)
TEMPORALIDADES = {
    "M1": ("1m", "7d"),
    "M5": ("5m", "7d"),
    "M15": ("15m", "5d"),
    "M30": ("30m", "5d"),
    "H1": ("1h", "730d"),
    "H4": ("1h", "730d"),  # Yahoo no tiene 4h nativo directo, agrupamos o usamos 1h extendido
    "D1": ("1d", "max")
}

@app.route('/escanner/<simbolo>', methods=['GET'])
def obtener_escanner(simbolo):
    try:
        simbolo_upper = simbolo.upper().replace("-", "").replace("/", "")
        ticker_yahoo = ""

        # 1. CAPTURAR CONFIGURACIÓN DE LA APP
        tf_app = request.args.get('temporalidad', 'M15').upper()
        intervalo, periodo = TEMPORALIDADES.get(tf_app, ("15m", "5d"))

        # Capturar periodos de EMAs
        p_ema9 = int(request.args.get('ema9', 9))
        p_ema21 = int(request.args.get('ema21', 21))
        p_ema50 = int(request.args.get('ema50', 50))
        p_ema200 = int(request.args.get('ema200', 200))

        # Cuáles indicadores evaluar ("true" o "false")
        evaluar_ema9 = request.args.get('use_ema9', 'true').lower() == 'true'
        evaluar_ema21 = request.args.get('use_ema21', 'true').lower() == 'true'
        evaluar_ema50 = request.args.get('use_ema50', 'true').lower() == 'true'
        evaluar_ema200 = request.args.get('use_ema200', 'true').lower() == 'true'

        # 2. TRADUCIR SÍMBOLO
        if "XAU" in simbolo_upper or simbolo_upper == "GLD":
            ticker_yahoo = "GC=F"  
        elif any(crypto in simbolo_upper for crypto in ["BTC", "ETH", "SOL", "XRP", "ADA"]):
            base = simbolo_upper.replace("USD", "") if "USD" in simbolo_upper else simbolo_upper
            ticker_yahoo = f"{base}-USD"
        elif len(simbolo_upper) == 6:
            ticker_yahoo = f"{simbolo_upper}=X"
        else:
            ticker_yahoo = simbolo_upper

        # 3. DESCARGAR DATOS SEGÚN LA TEMPORALIDAD SELECCIONADA
        ticker = yf.Ticker(ticker_yahoo)
        df = ticker.history(interval=intervalo, period=periodo)

        if df.empty:
            return jsonify({"error": f"No se encontraron datos en temporalidad {tf_app} para: {ticker_yahoo}"}), 404

        # Resamplear a H4 si el usuario pide H4 usando los datos de 1h
        if tf_app == "H4":
            df = df.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()

        df.columns = [col.lower() for col in df.columns]

        # 4. CÁLCULO DE EMAs
        df['ema9'] = df['close'].ewm(span=p_ema9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=p_ema21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=p_ema50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=p_ema200, adjust=False).mean()

        ultima_vela = df.iloc[-1]
        precio_actual = float(ultima_vela['close'])
        
        ema9_val = float(ultima_vela['ema9'])
        ema21_val = float(ultima_vela['ema21'])
        ema50_val = float(ultima_vela['ema50'])
        ema200_val = float(ultima_vela['ema200'])

        # 5. ESTRATEGIA EXTREMA FILTRADA (Solo evalúa lo que está "prendido")
        # Definir condiciones base sólo si están activas
        c_alcista = True
        c_bajista = True

        if evaluar_ema9 and evaluar_ema21:
            if not (ema9_val > ema21_val): c_alcista = False
            if not (ema9_val < ema21_val): c_bajista = False
        if evaluar_ema21 and evaluar_ema50:
            if not (ema21_val > ema50_val): c_alcista = False
            if not (ema21_val < ema50_val): c_bajista = False
        if evaluar_ema50 and evaluar_ema200:
            if not (ema50_val > ema200_val): c_alcista = False
            if not (ema50_val < ema200_val): c_bajista = False

        # PULLBACK EN LA EMA 50 (Sólo si la EMA 50 está activa para evaluar)
        pullback_alcista = evaluar_ema50 and c_alcista and (ultima_vela['low'] <= ema50_val and precio_actual >= ema50_val)
        pullback_bajista = evaluar_ema50 and c_bajista and (ultima_vela['high'] >= ema50_val and precio_actual <= ema50_val)

        # Determinación del estado para los botones
        if pullback_alcista:
            estado = "PULLBACK ALCISTA"
        elif pullback_bajista:
            estado = "PULLBACK BAJISTA"
        elif c_alcista and (precio_actual > ema9_val if evaluar_ema9 else True):
            estado = "ALCISTA"
        elif c_bajista and (precio_actual < ema9_val if evaluar_ema9 else True):
            estado = "BAJISTA"
        else:
            estado = "NEUTRO"

        # 6. RESPUESTA JSON TOTALMENTE LIMPIA Y ACTUALIZADA
        return jsonify({
            "simbolo": simbolo_upper,
            "temporalidad_evaluada": tf_app,
            "precio": round(precio_actual, 5),
            "estado": estado,
            "valores_analisis": {
                "ema9": round(ema9_val, 5) if evaluar_ema9 else None,
                "ema21": round(ema21_val, 5) if evaluar_ema21 else None,
                "ema50": round(ema50_val, 5) if evaluar_ema50 else None,
                "ema200": round(ema200_val, 5) if evaluar_ema200 else None
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
