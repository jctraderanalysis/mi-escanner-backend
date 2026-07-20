import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import os

st.set_page_config(
    page_title="Analizador Personal",
    page_icon="📊",
    layout="wide"
)

# --- BARRA LATERAL ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.header("⚙️ Configuración del Sistema")
token_telegram = st.sidebar.text_input("Telegram Bot Token", value=st.secrets.get("TELEGRAM_TOKEN", ""), type="password")
chat_id_telegram = st.sidebar.text_input("Telegram Chat ID", value=st.secrets.get("TELEGRAM_CHAT_ID", ""), type="password")

acciones_input = st.sidebar.text_area("Acciones", "AAPL,MSFT,NVDA,TSLA,AMD,AMZN")
forex_input = st.sidebar.text_area("Forex", "EURUSD=X,GBPUSD=X,AUDUSD=X")
crypto_input = st.sidebar.text_area("Crypto", "BTC-USD,ETH-USD")

lista_acciones = [x.strip() for x in acciones_input.split(",") if x.strip()]
lista_forex = [x.strip() for x in forex_input.split(",") if x.strip()]
lista_crypto = [x.strip() for x in crypto_input.split(",") if x.strip()]

# --- PANTALLA PRINCIPAL ---
st.title("📊 Cuadro de Mando Multitemporal Avanzado")

# NUEVO: CAMPOS DE CORREO VISIBLES TODO EL TIEMPO
st.markdown("### ✉️ Despachar Informe por Correo Electrónico")
c1, c2 = st.columns(2)
destinatario = c1.text_input("📬 Correo Electrónico Destinatario", value=st.secrets.get("EMAIL = "tu-correo-jctraderanalysis@gmail.com"), placeholder="ejemplo@correo.com")
asunto_correo = c2.text_input("✍️ Asunto del Mensaje", value="Reporte de Mercado - JC Trader Analysis")

# Inicializamos el estado del texto del correo si no existe
if 'texto_puro_correo' not in st.session_state:
    st.session_state['texto_puro_correo'] = "No se ha realizado ningún escaneo todavía. Los datos están vacíos."

# Formulario HTML invisible para procesar el envío mediante FormSubmit
url_formulario = f"https://formsubmit.co/{destinatario}" if destinatario else "#"

html_boton_correo = f"""
<form action="{url_formulario}" method="POST" target="_blank">
    <input type="hidden" name="_subject" value="{asunto_correo}">
    <input type="hidden" name="Informe de Mercado" value="{st.session_state['texto_puro_correo']}">
    <input type="hidden" name="_captcha" value="false">
    <button type="submit" style="
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 10px 24px;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
        width: 100%;
        font-weight: bold;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    ">📧 ENVIAR INFORME POR CORREO</button>
</form>
"""

if destinatario:
    st.markdown(html_boton_correo, unsafe_allow_html=True)
else:
    st.warning("Introduce un correo electrónico en el campo de arriba para activar el botón de envío.")

st.markdown("---")

def calcular_indicadores(df):
    if df.empty or len(df) < 30:
        return None
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def evaluar_direccion(last_row):
    if pd.isna(last_row['EMA30']) or pd.isna(last_row['EMA200']):
        return "🟡 NEUTRO"
    alcista = last_row['EMA30'] > last_row['EMA50'] > last_row['EMA100'] > last_row['EMA200']
    bajista = last_row['EMA30'] < last_row['EMA50'] < last_row['EMA100'] < last_row['EMA200']
    if alcista: return "🟢 ALCISTA"
    if bajista: return "🔴 BAJISTA"
    return "🟡 NEUTRO"

def calcular_soporte_resistencia(df):
    if df.empty or len(df) < 2:
        return 0, 0
    high = df['High'].iloc[-2]
    low = df['Low'].iloc[-2]
    close = df['Close'].iloc[-2]
    
    pivot = (high + low + close) / 3
    resistencia = (2 * pivot) - low
    soporte = (2 * pivot) - high
    return soporte, resistencia

if st.sidebar.button("🚀 INICIAR ESCANEO MULTITEMPORAL", use_container_width=True):
    datos_h4 = []
    datos_h1 = []
    datos_m5 = []
    resumen_alertas = []
    texto_puro_correo = ""
    
    todos_los_activos = [("Acciones", x) for x in lista_acciones] + [("Forex", x) for x in lista_forex] + [("Crypto", x) for x in lista_crypto]
    
    progreso = st.progress(0)
    total = len(todos_los_activos)
    
    for idx, (cat, activo) in enumerate(todos_los_activos):
        progreso.progress((idx + 1) / total)
        try:
            ticker = yf.Ticker(activo)
            
            df_h4 = calcular_indicadores(ticker.history(period="60d", interval="4h"))
            df_h1 = calcular_indicadores(ticker.history(period="15d", interval="1h"))
            df_m5 = calcular_indicadores(ticker.history(period="5d", interval="5m"))
            
            if df_h4 is None or df_h1 is None or df_m5 is None:
                continue
                
            lh4 = df_h4.iloc[-1]
            lh1 = df_h1.iloc[-1]
            lm5 = df_m5.iloc[-1]
            
            dec = 4 if cat == "Forex" else 2
            soporte_m5, res_m5 = calcular_soporte_resistencia(df_m5)
            
            tendencia_h4 = evaluar_direccion(lh4)
            datos_h4.append({
                "Activo": activo, "C/C H4": round(lh4['Close'], dec),
                "Tendencia H4": tendencia_h4, "EMA 30": round(lh4['EMA30'], dec),
                "EMA 50": round(lh4['EMA50'], dec), "EMA 100": round(lh4['EMA100'], dec),
                "EMA 200": round(lh4['EMA200'], dec), "RSI H4": round(lh4['RSI'], 1),
                "MACD H4": round(lh4['MACD'], dec)
            })
            
            tendencia_h1 = evaluar_direccion(lh1)
            datos_h1.append({
                "Activo": activo, "C/C H1": round(lh1['Close'], dec),
                "Tendencia H1": tendencia_h1, "EMA 30": round(lh1['EMA30'], dec),
                "EMA 50": round(lh1['EMA50'], dec), "EMA 100": round(lh1['EMA100'], dec),
                "EMA 200": round(lh1['EMA200'], dec), "RSI H1": round(lh1['RSI'], 1),
                "MACD H1": round(lh1['MACD'], dec)
            })
            
            tendencia_m5 = evaluar_direccion(lm5)
            t_h4_pura = tendencia_h4.split(" ")[1]
            t_h1_pura = tendencia_h1.split(" ")[1]
            t_m5_pura = tendencia_m5.split(" ")[1]
            
            if t_h4_pura == "ALCISTA" and t_h1_pura == "ALCISTA" and t_m5_pura == "ALCISTA" and lm5['RSI'] < 70:
                recom = "🟢 COMPRA CONFIRMADA"
                txt = f"🟢 **{activo}** | **COMPRA FUERTE**: Tendencia e indicadores 100% alineados al alza. Precio actual: `{round(lm5['Close'], dec)}`. Próxima Resistencia en M5: `{round(res_m5, dec)}` | Soporte de protección: `{round(soporte_m5, dec)}`."
                txt_puro = f"COMPRA FUERTE en {activo}. Precio: {round(lm5['Close'], dec)}. Resistencia: {round(res_m5, dec)} | Soporte: {round(soporte_m5, dec)}."
            elif t_h4_pura == "BAJISTA" and t_h1_pura == "BAJISTA" and t_m5_pura == "BAJISTA" and lm5['RSI'] > 30:
                recom = "🔴 VENTA CONFIRMADA"
                txt = f"🔴 **{activo}** | **VENTA FUERTE**: Estructura bajista e institucional confirmada. Precio actual: `{round(lm5['Close'], dec)}`. Soporte objetivo: `{round(soporte_m5, dec)}` | Resistencia de parada: `{round(res_m5, dec)}`."
                txt_puro = f"VENTA FUERTE en {activo}. Precio: {round(lm5['Close'], dec)}. Soporte: {round(soporte_m5, dec)} | Resistencia: {round(res_m5, dec)}."
            elif t_h1_pura == "ALCISTA" and t_m5_pura == "ALCISTA":
                recom = "🟡 COMPRA RIESGO"
                txt = f"🟡 **{activo}** | **REBOTE EN CORTO**: Fuerza compradora en M5 y H1, pero la tendencia macro H4 está en {tendencia_h4}. Soporte: `{round(soporte_m5, dec)}`."
                txt_puro = f"REBOTE EN CORTO en {activo}. Precio: {round(lm5['Close'], dec)}. Soporte: {round(soporte_m5, dec)}."
            elif t_h1_pura == "BAJISTA" and t_m5_pura == "BAJISTA":
                recom = "🟡 VENTA RIESGO"
                txt = f"🟡 **{activo}** | **CORRECCIÓN EN CORTO**: Presión bajista local (M5/H1), pero H4 sigue en {tendencia_h4}. Resistencia: `{round(res_m5, dec)}`."
                txt_puro = f"CORRECCIÓN EN CORTO en {activo}. Precio: {round(lm5['Close'], dec)}. Resistencia: {round(res_m5, dec)}."
            else:
                recom = "⚪ NEUTRO"
                txt = f"⚪ **{activo}** | **RANGO / COMPRESIÓN**: Las temporalidades están cruzadas (H4: {t_h4_pura} | H1: {t_h1_pura}). Esperar ruptura. Soporte: `{round(soporte_m5, dec)}` | Resistencia: `{round(res_m5, dec)}`."
                txt_puro = f"RANGO / COMPRESIÓN en {activo}. Temporalidades cruzadas. Soporte: {round(soporte_m5, dec)} | Resistencia: {round(res_m5, dec)}."
                
            resumen_alertas.append(txt)
            texto_puro_correo += f"- {txt_puro}\n"
            
            datos_m5.append({
                "Activo": activo, "C/C M5": round(lm5['Close'], dec),
                "Gatillo M5": tendencia_m5, 
                "RSI M5": round(lm5['RSI'], 1), "MACD M5": round(lm5['MACD'], dec),
                "Soporte (S1)": round(soporte_m5, dec), "Resistencia (R1)": round(res_m5, dec),
                "RECOMENDACIÓN OPE": recom
            })
        except Exception:
            pass

    # Guardamos todo en el estado de la sesión para que persista al refrescar la interfaz
    st.session_state['resumen_alertas'] = resumen_alertas
    st.session_state['texto_puro_correo'] = texto_puro_correo
    st.session_state['datos_h4'] = datos_h4
    st.session_state['datos_h1'] = datos_h1
    st.session_state['datos_m5'] = datos_m5

# --- MOSTRAR LOS RESULTADOS DEBAJO DEL BLOQUE DE CORREO ---
if 'resumen_alertas' in st.session_state:
    st.subheader("📢 Resumen Ejecutivo e Informe de Mercado")
    col1, col2 = st.columns(2)
    for i, alerta in enumerate(st.session_state['resumen_alertas']):
        if i % 2 == 0:
            col1.markdown(alerta)
        else:
            col2.markdown(alerta)

    st.markdown("---")

    # --- LÓGICA DE ESTILOS ---
    def color_general(val):
        if "🟢" in str(val): return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if "🔴" in str(val): return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        if "🟡" in str(val): return 'background-color: #fff3cd; color: #856404;'
        return ''

    def color_rsi(val):
        try:
            v = float(val)
            if v > 55: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            if v < 45: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            return 'background-color: #f2f2f2; color: #595959;'
        except: return ''

    def color_macd(val):
        try:
            v = float(val)
            if v > 0: return 'background-color: #e2f0d9; color: #385723; font-weight: bold;'
            if v < 0: return 'background-color: #fce4d6; color: #c65911; font-weight: bold;'
            return ''
        except: return ''

    def color_precio_vs_emas(row, col_precio, df_origen):
        styles = [''] * len(row)
        idx_precio = row.index.get_loc(col_precio)
        try:
            p = float(row[col_precio])
            e30 = float(row['EMA 30']) if 'EMA 30' in row else p
            e50 = float(row['EMA 50']) if 'EMA 50' in row else p
            e100 = float(row['EMA 100']) if 'EMA 100' in row else p
            e200 = float(row['EMA 200']) if 'EMA 200' in row else p
            medias = [e30, e50, e100, e200]
            if max(medias) == min(medias): return styles
            if p > max(medias): styles[idx_precio] = 'background-color: #c6efce; color: #006100; font-weight: bold;'
            elif p < min(medias): styles[idx_precio] = 'background-color: #ffc7ce; color: #9c0006; font-weight: bold;'
            else: styles[idx_precio] = 'background-color: #ffeb9c; color: #9c6500; font-weight: bold;'
        except: pass
        return styles

    # --- MOSTRAR TABLAS ---
    st.markdown("### 🏛️ 1. Matriz de Tendencia Macro (H4)")
    if st.session_state['datos_h4']:
        df_h4 = pd.DataFrame(st.session_state['datos_h4'])
        st.dataframe(df_h4.style.map(color_general, subset=['Tendencia H4']).map(color_rsi, subset=['RSI H4']).map(color_macd, subset=['MACD H4']).apply(color_precio_vs_emas, axis=1, col_precio='C/C H4', df_origen=df_h4), use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.markdown("### 📈 2. Matriz de Estructura Intermedia (H1)")
    if st.session_state['datos_h1']:
        df_h1 = pd.DataFrame(st.session_state['datos_h1'])
        st.dataframe(df_h1.style.map(color_general, subset=['Tendencia H1']).map(color_rsi, subset=['RSI H1']).map(color_macd, subset=['MACD H1']).apply(color_precio_vs_emas, axis=1, col_precio='C/C H1', df_origen=df_h1), use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.markdown("### ⚡ 3. Matriz de Gatillo y Ejecución Operativa (M5)")
    if st.session_state['datos_m5']:
        df_m5 = pd.DataFrame(st.session_state['datos_m5'])
        st.dataframe(df_m5.style.map(color_general, subset=['Gatillo M5', 'RECOMENDACIÓN OPE']).map(color_rsi, subset=['RSI M5']).map(color_macd, subset=['MACD M5']), use_container_width=True, hide_index=True)

    st.caption(f"Última actualización de mercado: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.info("Presiona el botón en la barra lateral para procesar el análisis multitemporal.")
