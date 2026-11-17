import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date
import calendar
import pytz
import html

# --- 1. CONFIGURACIÓN Y METADATOS ---
VERSION_APP = "1.5.1"
AUTOR = "Richard Rocha"

st.set_page_config(
    page_title=f"Terminal Macro v{VERSION_APP}", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

FINNHUB_API_KEY = "dbtk2ehr01qtr41fbk30dbtk2ehr01qtr41fbk3g"

# --- ESTILOS CSS ---
st.markdown("""
    <style>
        .block-container { padding-top: 3.3rem !important; padding-bottom: 1rem; }
        h1 { font-size: 1.6rem !important; margin-bottom: 0rem !important; }
        
        /* Cinta horizontal */
        .ticker-wrap {
            width: 100%; overflow: hidden; background-color: #0F172A;
            border: 2px solid #3B82F6; border-radius: 8px; padding: 10px 0;
            margin-bottom: 14px; white-space: nowrap; box-sizing: border-box; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        }
        .ticker-move { display: inline-block; padding-left: 10%; animation: ticker-scroll 130s linear infinite; }
        .ticker-wrap:hover .ticker-move { animation-play-state: paused; }
        @keyframes ticker-scroll { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
        .ticker-item { display: inline-block; padding: 0 30px; font-size: 0.95rem; color: #F8FAFC; border-right: 1px solid #475569; }
        
        /* Badges */
        .badge-nas { background-color: #2563EB; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        .badge-xau { background-color: #D97706; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        .badge-brk { background-color: #DC2626; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        
        /* Calendario PC */
        .cal-header, .cal-header-wknd { text-align: center; font-weight: bold; padding: 6px; border-radius: 4px; margin-bottom: 4px; font-size: 0.85rem; }
        .cal-header { background-color: #1F2937; color: #F9FAFB; }
        .cal-header-wknd { background-color: #451A1A; color: #FCA5A5; }

        /* Tarjetas Móviles */
        .mob-card { background-color: #111827; border: 1px solid #374151; border-left: 4px solid #3B82F6; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
        .mob-card-high { border-left-color: #EF4444; }
        .mob-card-med  { border-left-color: #F59E0B; }
        .mob-card-low  { border-left-color: #10B981; }
        .mob-top { font-size: 0.92rem; font-weight: 600; color: #F9FAFB; margin-bottom: 5px; line-height: 1.3; }
        .mob-nums { font-size: 0.80rem; color: #9CA3AF; margin-bottom: 5px; }
        .mob-nums code { color: #E5E7EB; background-color: #1F2937; padding: 1px 5px; border-radius: 4px; }
        .mob-proy { font-size: 0.84rem; font-weight: bold; color: #E5E7EB; }

        /* Guía y pie de página */
        .footer-info { text-align: center; color: #6B7280; font-size: 0.85rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #374151; }

        /* RESPONSIVIDAD */
        @media (min-width: 769px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-movil) { display: none !important; }
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-pc) div[data-testid="column"] button { height: 68px !important; padding: 4px !important; line-height: 1.25 !important; font-size: 0.82rem !important; }
            /* Ocultar botón flotante en PC */
            div.flotante-btn { display: none !important; }
        }
        @media (max-width: 768px) {
            .block-container { padding-top: 2.8rem !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-pc) { display: none !important; }
            .ticker-wrap { padding: 7px 0; margin-bottom: 10px; }
            .ticker-item { font-size: 0.84rem; padding: 0 18px; }
            
            /* Botón Flotante Celular */
            div.flotante-btn {
                position: fixed; bottom: 80px; right: 20px; z-index: 99999;
            }
            div.flotante-btn button {
                width: 55px !important; height: 55px !important; border-radius: 50% !important;
                background-color: #3B82F6 !important; color: white !important;
                border: 2px solid #60A5FA !important; box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
                font-size: 24px !important; display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 !important;
            }
            div.flotante-btn button p { display: none !important; }
            div.flotante-btn button::after { content: "🔄"; }
        }
    </style>
""", unsafe_allow_html=True)


# --- 2. DICCIONARIO DE TRADUCCIÓN AMPLIADO ---
DICCIONARIO_TRADUCCION = {
    "Speaks": "Habla", "Member": "Miembro", "Balance of Trade": "Balanza Comercial",
    "Crude Oil Stock Change": "Cambio Inv. Crudo", "Unemployment Rate": "Tasa de Desempleo",
    "Initial Jobless Claims": "Peticiones de Desempleo", "Core CPI": "IPC Subyacente",
    " CPI": " IPC", "Retail Sales": "Ventas Minoristas", "Non Farm Payrolls": "Nóminas No Agrícolas",
    "Gross Domestic Product": "PIB", " GDP": " PIB", "Interest Rate Decision": "Decisión de Tasas",
    "Building Permits": "Permisos de Construcción", "Existing Home Sales": "Ventas Viviendas Usadas",
    "New Home Sales": "Ventas Viviendas Nuevas", "Services PMI": "PMI Servicios",
    "Manufacturing PMI": "PMI Manufacturero", "Fed Chair": "Pdte. Fed", "Testifies": "Testifica",
    "Statement": "Declaración", "Minutes": "Actas FOMC", "Press Conference": "Rueda de Prensa",
    "Product Imports": "Imp. Productos", "Gasoline Stocks": "Inv. Gasolina",
    "Distillate Stocks": "Inv. Destilados", "Heating Oil": "Aceite Calefacción",
    "Crude Imports": "Imp. Crudo", "Crude Runs": "Refinación Crudo",
    "Cushing Number": "Inv. Cushing", "Weekly Statistical Bulletin": "Boletín Semanal",
    "Consumer Confidence": "Confianza Consumidor", "Industrial Production": "Producción Industrial",
    "Durable Goods Orders": "Pedidos Bienes Duraderos", "Trade Balance": "Balanza Comercial",
    "Jobless Claims": "Subsidios Desempleo", "Wage Growth": "Crecimiento Salarial",
    "Inflation Rate": "Tasa Inflación", "Producer Price Index": "IPP",
    " PPI": " IPP", "Wholesale Inventories": "Inventarios Mayoristas",
    " Fed": " Reserva Federal", " ECB": " BCE", " BoE": " BdI", " BoJ": " BdJ",
    "YoY": "Interanual", "MoM": "Mensual", "QoQ": "Trimestral",
    "Core PCE Price Index": "PCE Subyacente", "PCE Price Index": "Índice PCE",
    "Export Prices": "Precios de Exportación", "Import Prices": "Precios de Importación",
    "Capacity Utilization": "Utilización de Capacidad", "Control Group": "Grupo de Control",
    "Ex Autos": "Excl. Autos", "Ex Gas/Autos": "Excl. Gas/Autos",
    "Employment Change": "Cambio de Empleo", "Manufacturing Production": "Prod. Manufacturera"
}

def traducir_texto(texto, activo=True):
    if not activo or not texto: return texto
    for ing, esp in DICCIONARIO_TRADUCCION.items():
        texto = texto.replace(ing, esp).replace(ing.upper(), esp.upper())
    return texto


# --- 3. DESCARGA DE DATOS ---
def obtener_discursos_ff():
    tz_utc = pytz.utc
    ahora = datetime.now(tz_utc)
    if 'ff_cache_df' in st.session_state and 'ff_cache_time' in st.session_state:
        if not st.session_state.ff_cache_df.empty and (ahora - st.session_state.ff_cache_time).total_seconds() < 1200:
            return st.session_state.ff_cache_df

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    eventos_ff = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            mapa_imp_ff = {"High": 1, "Medium": 0, "Low": -1, "Holiday": -1}
            mapa_pais_ff = {"USD": "US", "CAD": "CA", "CNY": "CN", "EUR": "EU", "JPY": "JP", "GBP": "GB"}
            for ev in res.json():
                divisa = ev.get("country", "")
                if divisa not in mapa_pais_ff: continue
                titulo = str(ev.get("title", "")).strip()
                es_discurso = any(k in titulo.lower() for k in ["speaks", "speech", "testifies", "statement", "press conference", "minutes", "fed chair", "fomc", "member", "gov", "president", "boc", "ecb", "boj", "boe"])
                prev_val, fore_val = str(ev.get("previous", "")).strip(), str(ev.get("forecast", "")).strip()
                if es_discurso or (prev_val == "" and fore_val == ""):
                    eventos_ff.append({
                        "date": pd.to_datetime(ev.get("date"), utc=True),
                        "country": mapa_pais_ff[divisa],
                        "title": f"🎙️ {titulo}" if es_discurso else titulo,
                        "importance": mapa_imp_ff.get(ev.get("impact"), -1),
                        "previous": prev_val if prev_val != "" else None,
                        "forecast": fore_val if fore_val != "" else None,
                        "actual": None, "unit": "", "es_discurso": es_discurso
                    })
    except Exception: pass
    df_resultado = pd.DataFrame(eventos_ff)
    if not df_resultado.empty:
        st.session_state.ff_cache_df = df_resultado
        st.session_state.ff_cache_time = ahora
        return df_resultado
    return st.session_state.get('ff_cache_df', pd.DataFrame())

@st.cache_data(ttl=10)
def obtener_datos_mes_rapido(anio, mes, bloque_tiempo):
    primer_dia = date(anio, mes, 1)
    ultimo_dia_num = calendar.monthrange(anio, mes)[1]
    inicio_utc = (datetime.combine(primer_dia, datetime.min.time()) - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
    fin_utc = (datetime.combine(date(anio, mes, ultimo_dia_num), datetime.max.time()) + timedelta(days=1)).strftime('%Y-%m-%dT23:59:59.000Z')
    
    url = "https://economic-calendar.tradingview.com/events"
    params = {"from": inicio_utc, "to": fin_utc, "countries": "US,CA,CN,EU,JP,GB"}
    headers = {"Origin": "https://www.tradingview.com", "User-Agent": "Mozilla/5.0"}
    
    df_tv = pd.DataFrame()
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200 and 'result' in res.json():
            df_tv = pd.DataFrame(res.json()['result'])
            if not df_tv.empty:
                df_tv['date'] = pd.to_datetime(df_tv['date'], utc=True)
                df_tv['es_discurso'] = df_tv['title'].str.lower().str.contains('speaks|speech|testifies|statement|press conference|minutes|fed chair|fomc', na=False)
    except Exception: pass
    return df_tv

def fusionar_calendario_y_discursos(df_tv, anio, mes):
    df_ff = obtener_discursos_ff()
    if df_ff.empty: return df_tv
    df_ff_mes = df_ff[(df_ff['date'].dt.year == anio) & (df_ff['date'].dt.month == mes)].copy()
    if df_ff_mes.empty: return df_tv
    if df_tv.empty: return df_ff_mes
    titulos_tv = set(df_tv['title'].str.lower().str.replace('🎙️ ', '', regex=False).str[:15])
    nuevos_ff = df_ff_mes[~df_ff_mes['title'].str.lower().str.replace('🎙️ ', '', regex=False).str[:15].isin(titulos_tv)]
    df_res = pd.concat([df_tv, nuevos_ff], ignore_index=True)
    df_res['date'] = pd.to_datetime(df_res['date'], utc=True)
    return df_res

@st.cache_data(ttl=120)
def obtener_breaking_news(api_key):
    url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
    tz_utc = pytz.utc
    excluir = ['bitcoin', 'btc', 'crypto', 'ethereum', 'solana', 'dogecoin', 'memecoin', 'nft']
    kw_xau = ['gold', 'xau', 'bullion', 'fed', 'powell', 'warsh', 'fomc', 'inflation', 'cpi', 'tariff', 'war', 'missile', 'iran', 'israel', 'china', 'central bank', 'treasury', 'yield', 'dollar', 'dxy', 'recession']
    kw_nas = ['nasdaq', 'tech', 'nvidia', 'apple', 'microsoft', 'semiconductor', 'fed', 'powell', 'warsh', 'fomc', 'interest rate', 'inflation', 'cpi', 'jobs', 'recession', 'treasury', 'yield', 'tariff']
    
    noticias_filtradas = []
    try:
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            for item in res.json()[:45]:
                titulo, resumen = item.get('headline', ''), item.get('summary', '')
                texto_busqueda = (titulo + " " + resumen).lower()
                if any(ex in texto_busqueda for ex in excluir): continue
                afecta_xau, afecta_nas = any(k in texto_busqueda for k in kw_xau), any(k in texto_busqueda for k in kw_nas)
                if afecta_xau or afecta_nas:
                    noticias_filtradas.append({
                        "fecha_dt": datetime.fromtimestamp(item.get('datetime', 0), tz=tz_utc),
                        "titulo": titulo, "resumen": resumen, "fuente": item.get('source', 'Mercado'), "url": item.get('url', '#'),
                        "nas": afecta_nas, "xau": afecta_xau
                    })
    except Exception: pass
    return noticias_filtradas

# --- 4. LÓGICA DE PROCESAMIENTO ---
def es_relevante_nas100(fila, filtro_estricto=False):
    if fila.get('country') != 'US': return False
    if not filtro_estricto: return True
    ruido_nas = ['3-month', '6-month', '4-week', '8-week', '52-week', 'bill auction', 'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado', 'crude', 'petróleo', 'oil', 'gasoline', 'gasolina', 'natural gas', 'gas natural', 'baker hughes', 'rig count', 'distillate', 'cushing', 'eia', 'api weekly']
    return not any(palabra in str(fila.get('title', '')).lower() for palabra in ruido_nas)

def es_relevante_xauusd(fila, filtro_estricto=False):
    pais = fila.get('country')
    if pais in ['CA', 'CN', 'EU', 'JP', 'GB']: return fila.get('importance', -1) == 1
    if pais == 'US':
        if not filtro_estricto: return True
        ruido_xau = ['3-month', '6-month', '4-week', '8-week', '52-week', 'bill auction', 'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado', 'cotton', 'algodón']
        return not any(palabra in str(fila.get('title', '')).lower() for palabra in ruido_xau)
    return False

def obtener_sesgo_compacto(fila, activo, ahora_utc):
    actual, pronostico, anterior = fila.get('actual'), fila.get('forecast'), fila.get('previous')
    es_discurso = fila.get('es_discurso', False)
    if es_discurso and pd.isna(actual):
        return "🎙️ Discurso realizado (Revisar tono Hawkish/Dovish)" if pd.notna(fila.get('date')) and fila.get('date') <= ahora_utc else "🎙️ Pendiente (Alta volatilidad en vivo)"

    es_extranjera = (fila.get('country', 'US') in ['CA', 'CN', 'EU', 'JP', 'GB'])
    tiene_actual, tiene_pron, tiene_ant = pd.notna(actual), pd.notna(pronostico), pd.notna(anterior)
    
    dir_esperada = None
    if tiene_pron and tiene_ant:
        try:
            p, a = float(pronostico), float(anterior)
            if p > a: dir_esperada = 1 if es_extranjera else -1
            elif p < a: dir_esperada = -1 if es_extranjera else 1
            else: dir_esperada = 0
        except: pass

    if not tiene_actual:
        if dir_esperada == 1: return "⏳ Pendiente (Se espera Subida 📈)"
        if dir_esperada == -1: return "⏳ Pendiente (Se espera Caída 📉)"
        if dir_esperada == 0: return "⏳ Pendiente (Se espera Neutral ➖)"
        return "⏳ Pendiente (Sin pronóstico)"

    referencia = pronostico if tiene_pron else anterior
    if pd.isna(referencia): return "ℹ️ Publicado"
    
    try:
        act, ref = float(actual), float(referencia)
        if act > ref: dir_real, base = (1, "🟢 ALCISTA") if es_extranjera else (-1, "🔴 BAJISTA")
        elif act < ref: dir_real, base = (-1, "🔴 BAJISTA") if es_extranjera else (1, "🟢 ALCISTA")
        else: dir_real, base = 0, "⚪ NEUTRAL"

        if tiene_pron and dir_esperada is not None:
            estado = "🎯 Exacto" if act == float(pronostico) else "✅ Cumplido" if dir_real == dir_esperada else "❌ Al contrario"
            return f"{base} | {estado}"
        return f"{base} (Vs. Anterior)"
    except: return "ℹ️ Publicado"

def formatear_num(val):
    return f"{val}" if pd.notna(val) and str(val).strip() != "" else "-"

def construir_tarjetas_movil(filas_lista, etiqueta_tz, bandera_tz):
    if not filas_lista: return "<p style='color:#9CA3AF; font-size:0.9rem;'>Sin eventos programados para esta fecha.</p>"
    html_cards = []
    for f in filas_lista:
        clase_borde = "mob-card-high" if f["Imp"] == "🔴" else "mob-card-med" if f["Imp"] == "🟠" else "mob-card-low"
        card = f"""
        <div class="mob-card {clase_borde}">
            <div class="mob-top">{f["Imp"]} 🗽 {f['NY']} | {bandera_tz} {f[etiqueta_tz]} — {html.escape(f["Noticia"])}</div>
            <div class="mob-nums">Ant: <code>{f['Ant']}</code> &nbsp;|&nbsp; Pron: <code>{f['Pron']}</code> &nbsp;|&nbsp; Real: <code>{f['Real']}</code></div>
            <div class="mob-proy">{html.escape(f["Proy"])}</div>
        </div>
        """
        html_cards.append(card)
    return "".join(html_cards)

# --- 5. ESTADO Y VARIABLES GLOBALES ---
ZONAS_HORARIAS = {
    "Bolivia": {"tz": "America/La_Paz", "bandera": "🇧🇴", "etiqueta": "BO"},
    "Argentina": {"tz": "America/Argentina/Buenos_Aires", "bandera": "🇦🇷", "etiqueta": "AR"},
    "Chile": {"tz": "America/Santiago", "bandera": "🇨🇱", "etiqueta": "CL"},
    "Colombia / Perú / Ecuador": {"tz": "America/Bogota", "bandera": "🇨🇴", "etiqueta": "CO"},
    "México (CDMX)": {"tz": "America/Mexico_City", "bandera": "🇲🇽", "etiqueta": "MX"},
    "España (Madrid)": {"tz": "Europe/Madrid", "bandera": "🇪🇸", "etiqueta": "ES"},
    "Reino Unido (Londres)": {"tz": "Europe/London", "bandera": "🇬🇧", "etiqueta": "UK"},
    "Japón (Tokio)": {"tz": "Asia/Tokyo", "bandera": "🇯🇵", "etiqueta": "JP"},
    "Australia (Sídney)": {"tz": "Australia/Sydney", "bandera": "🇦🇺", "etiqueta": "AU"}
}
OPCIONES_ZONAS = list(ZONAS_HORARIAS.keys())

ahora_utc = datetime.now(pytz.utc)
if 'zona_seleccionada' not in st.session_state: st.session_state.zona_seleccionada = "Bolivia"
if 'fecha_seleccionada' not in st.session_state: st.session_state.fecha_seleccionada = ahora_utc.astimezone(pytz.timezone(ZONAS_HORARIAS[st.session_state.zona_seleccionada]["tz"])).date()
if 'mes_vista' not in st.session_state: st.session_state.mes_vista = st.session_state.fecha_seleccionada.month
if 'anio_vista' not in st.session_state: st.session_state.anio_vista = st.session_state.fecha_seleccionada.year
if 'modo_francotirador' not in st.session_state: st.session_state.modo_francotirador = False
if 'activar_traductor' not in st.session_state: st.session_state.activar_traductor = True

def calcular_intervalo_refresco(df_hoy, ahora_utc):
    if df_hoy.empty: return 180, False
    for _, r in df_hoy.iterrows():
        diff_segundos = (r['date'] - ahora_utc).total_seconds()
        if not r.get('es_discurso', False) and pd.isna(r.get('actual')) and -300 <= diff_segundos <= 120: return 10, True
    return 180, False

# --- 6. RENDERIZADO PRINCIPAL ---
@st.fragment(run_every=10)
def renderizar_terminal():
    tz_ny = pytz.timezone('America/New_York')
    tz_sel = pytz.timezone(ZONAS_HORARIAS[st.session_state.zona_seleccionada]["tz"])
    bandera_sel, etiqueta_sel = ZONAS_HORARIAS[st.session_state.zona_seleccionada]["bandera"], ZONAS_HORARIAS[st.session_state.zona_seleccionada]["etiqueta"]
    
    ahora_utc = datetime.now(pytz.utc)
    ahora_ny, ahora_sel = ahora_utc.astimezone(tz_ny), ahora_utc.astimezone(tz_sel)
    hoy_sel_date = ahora_sel.date()
    
    bloque_tiempo = int(ahora_utc.timestamp() // (10 if st.session_state.modo_francotirador else 180))
    df_mes = fusionar_calendario_y_discursos(obtener_datos_mes_rapido(st.session_state.anio_vista, st.session_state.mes_vista, bloque_tiempo), st.session_state.anio_vista, st.session_state.mes_vista)
    df_actual = fusionar_calendario_y_discursos(obtener_datos_mes_rapido(hoy_sel_date.year, hoy_sel_date.month, bloque_tiempo), hoy_sel_date.year, hoy_sel_date.month)
    
    st.session_state.modo_francotirador = calcular_intervalo_refresco(df_actual[df_actual['date'].dt.tz_convert(tz_sel).dt.date == hoy_sel_date], ahora_utc)[1] if not df_actual.empty else False
    breaking_news = obtener_breaking_news(FINNHUB_API_KEY)
    traductor_on = st.session_state.activar_traductor
    
    # --- CINTA HORIZONTAL ---
    items_ticker = []
    for bn in breaking_news[:5]:
        if bn['fecha_dt'] >= (ahora_utc - timedelta(hours=6)):
            badges = '<span class="badge-brk">🚨 ÚLTIMA HORA</span> ' + ('<span class="badge-nas">NAS100</span> ' if bn['nas'] else '') + ('<span class="badge-xau">XAUUSD</span> ' if bn['xau'] else '')
            items_ticker.append(f'<div class="ticker-item">{badges} <b>[🗽 {bn["fecha_dt"].astimezone(tz_ny).strftime("%H:%M")}] {html.escape(traducir_texto(bn["titulo"], traductor_on))}</b> <i>({html.escape(bn["fuente"])})</i></div>')

    if not df_actual.empty:
        for _, r in df_actual[(df_actual['date'] >= ahora_utc - timedelta(minutes=30))].sort_values(by='date').head(10).iterrows():
            es_nas, es_xau = es_relevante_nas100(r, False), es_relevante_xauusd(r, False)
            if not (es_nas or es_xau): continue
            imp_ico = "🔴" if r.get('importance') == 1 else "🟠" if r.get('importance') == 0 else "🟡"
            activos_html = ('<span class="badge-nas">NAS100</span> ' if es_nas else '') + ('<span class="badge-xau">XAUUSD</span> ' if es_xau else '')
            items_ticker.append(f'<div class="ticker-item">{imp_ico} <b>🗽{r["date"].astimezone(tz_ny).strftime("%H:%M")} | {bandera_sel}{r["date"].astimezone(tz_sel).strftime("%H:%M")}</b> | {activos_html} <b>{html.escape(traducir_texto(str(r["title"]), traductor_on))}</b> — Ant: <code>{formatear_num(r.get("previous"))}</code> | Pron: <code>{formatear_num(r.get("forecast"))}</code> | Real: <code>{formatear_num(r.get("actual"))}</code> → <b>{html.escape(obtener_sesgo_compacto(r, "XAU" if es_xau else "NAS", ahora_utc))}</b></div>')

    st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{"".join(items_ticker) if items_ticker else "<div class=ticker-item>📡 Monitoreando mercados en vivo...</div>"}</div></div>', unsafe_allow_html=True)

    # --- ENCABEZADO DE FECHA Y FILTROS ---
    f_sel = st.session_state.fecha_seleccionada
    estado_radar = "⚡ EN VIVO (10s)" if st.session_state.modo_francotirador else "🟢 Normal (3m)"
    
    c_tit_dia, c_check_ruido, c_trad, c_filtro_imp, c_tz, c_btn_pc = st.columns([3.2, 1.4, 0.9, 1.2, 1.4, 1.0])
    with c_tit_dia: st.subheader(f"📋 {f_sel.strftime('%d/%m/%Y')} | 🗽 NY {ahora_ny.strftime('%H:%M')} • {bandera_sel} {etiqueta_sel} {ahora_sel.strftime('%H:%M')} | {estado_radar}")
    with c_check_ruido: st.write(""); filtro_estricto = st.checkbox("🛡️ Ocultar letras/agrícolas", value=False)
    with c_trad: 
        st.write("")
        if st.checkbox("🇪🇸 Traducir", value=st.session_state.activar_traductor) != st.session_state.activar_traductor:
            st.session_state.activar_traductor = not st.session_state.activar_traductor; st.rerun()
    with c_filtro_imp: filtro_imp = st.multiselect("Impacto:", options=["Alto", "Medio", "Bajo"], default=["Alto", "Medio", "Bajo"], label_visibility="collapsed")
    with c_tz:
        nueva_zona = st.selectbox("🌍 Zona:", options=OPCIONES_ZONAS, index=OPCIONES_ZONAS.index(st.session_state.zona_seleccionada), label_visibility="collapsed")
        if nueva_zona != st.session_state.zona_seleccionada: st.session_state.zona_seleccionada = nueva_zona; st.rerun()
    with c_btn_pc:
        st.markdown('<div class="solo-pc">', unsafe_allow_html=True)
        if st.button("🔄 Actualizar", key="pc_sync_btn", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TABLAS DE NOTICIAS ---
    if not df_mes.empty:
        df_dia = df_mes[df_mes['date'].dt.tz_convert(tz_sel).dt.date == f_sel].copy()
        df_dia['imp_texto'] = df_dia['importance'].map({1: "Alto", 0: "Medio", -1: "Bajo"})
        df_dia['Imp'] = df_dia['importance'].map({1: "🔴", 0: "🟠", -1: "🟡"})
        df_dia = df_dia[df_dia['imp_texto'].isin(filtro_imp)].sort_values(by='date', ascending=False)

        filas_nas, filas_xau, filas_nas_mob, filas_xau_mob = [], [], [], []
        banderas = {"US": "🇺🇸", "CA": "🇨🇦", "CN": "🇨🇳", "EU": "🇪🇺", "JP": "🇯🇵", "GB": "🇬🇧"}
        
        for _, r in df_dia.iterrows():
            ny_str, sel_str = r['date'].astimezone(tz_ny).strftime('%H:%M'), r['date'].astimezone(tz_sel).strftime('%H:%M')
            ant, pron, act = formatear_num(r.get('previous')), formatear_num(r.get('forecast')), formatear_num(r.get('actual'))

            if es_relevante_nas100(r, filtro_estricto):
                tit = traducir_texto(r['title'], traductor_on)
                proy = obtener_sesgo_compacto(r, "NAS", ahora_utc)
                filas_nas.append({"Imp": r['Imp'], "🗽 NY": ny_str, f"{bandera_sel} {etiqueta_sel}": sel_str, "Noticia (EE.UU.)": tit, "Ant": ant, "Pron": pron, "Real": act, "Proyección": proy})
                filas_nas_mob.append({"Imp": r['Imp'], "NY": ny_str, etiqueta_sel: sel_str, "Noticia": tit, "Ant": ant, "Pron": pron, "Real": act, "Proy": proy})

            if es_relevante_xauusd(r, filtro_estricto):
                tit_x = f"{banderas.get(r.get('country'), '🌐')} {traducir_texto(r['title'], traductor_on)}"
                proy_x = obtener_sesgo_compacto(r, "XAU", ahora_utc)
                filas_xau.append({"Imp": r['Imp'], "🗽 NY": ny_str, f"{bandera_sel} {etiqueta_sel}": sel_str, "Noticia (Global)": tit_x, "Ant": ant, "Pron": pron, "Real": act, "Proyección": proy_x})
                filas_xau_mob.append({"Imp": r['Imp'], "NY": ny_str, etiqueta_sel: sel_str, "Noticia": tit_x, "Ant": ant, "Pron": pron, "Real": act, "Proy": proy_x})

        # PC
        with st.container():
            st.markdown('<span class="marker-pc"></span>', unsafe_allow_html=True)
            col_n, col_x = st.columns(2, gap="medium")
            with col_n: 
                st.markdown("#### 🇺🇸 NAS100")
                if filas_nas: st.dataframe(pd.DataFrame(filas_nas), use_container_width=True, hide_index=True)
                else: st.info("Sin eventos programados.")
            with col_x: 
                st.markdown("#### 🪙 XAUUSD")
                if filas_xau: st.dataframe(pd.DataFrame(filas_xau), use_container_width=True, hide_index=True)
                else: st.info("Sin eventos programados.")
        
        # MÓVIL
        with st.container():
            st.markdown('<span class="marker-movil"></span>', unsafe_allow_html=True)
            tab_n, tab_x = st.tabs([f"🇺🇸 NAS100 ({len(filas_nas_mob)})", f"🪙 XAUUSD ({len(filas_xau_mob)})"])
            with tab_n: st.markdown(construir_tarjetas_movil(filas_nas_mob, etiqueta_sel, bandera_sel), unsafe_allow_html=True)
            with tab_x: st.markdown(construir_tarjetas_movil(filas_xau_mob, etiqueta_sel, bandera_sel), unsafe_allow_html=True)
    else:
        st.warning("No se encontraron datos para el mes seleccionado.")

    # --- CALENDARIO MÓVIL (Nativo) ---
    st.markdown('<div class="solo-celular">', unsafe_allow_html=True)
    nueva_f = st.date_input("📅 Cambiar fecha:", value=f_sel, format="DD/MM/YYYY", key="mob_date")
    if nueva_f != f_sel: st.session_state.fecha_seleccionada = nueva_f; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CALENDARIO PC (Botones) ---
    st.markdown('<div class="solo-pc">', unsafe_allow_html=True)
    st.markdown("---")
    meses_es = ["", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
    c_p, c_m, c_n, c_h = st.columns([1, 4, 1, 1.5])
    with c_p:
        if st.button("◀ Mes Ant.", use_container_width=True): st.session_state.mes_vista = 12 if st.session_state.mes_vista == 1 else st.session_state.mes_vista - 1; st.rerun()
    with c_m: st.markdown(f"<h3 style='text-align:center; margin:0;'>📅 {meses_es[st.session_state.mes_vista]} {st.session_state.anio_vista}</h3>", unsafe_allow_html=True)
    with c_n:
        if st.button("Mes Sig. ▶", use_container_width=True): st.session_state.mes_vista = 1 if st.session_state.mes_vista == 12 else st.session_state.mes_vista + 1; st.rerun()
    with c_h:
        if st.button("📍 Ir a Hoy", use_container_width=True): st.session_state.fecha_seleccionada, st.session_state.mes_vista = hoy_sel_date, hoy_sel_date.month; st.rerun()

    resumen_dias = {f: {"nas": len(df_mes[(df_mes['date'].dt.tz_convert(tz_sel).dt.date == f) & df_mes.apply(lambda r: es_relevante_nas100(r), axis=1)]) > 0, "xau": len(df_mes[(df_mes['date'].dt.tz_convert(tz_sel).dt.date == f) & df_mes.apply(lambda r: es_relevante_xauusd(r), axis=1)]) > 0, "imp": df_mes[df_mes['date'].dt.tz_convert(tz_sel).dt.date == f]['importance'].max()} for f in df_mes['date'].dt.tz_convert(tz_sel).dt.date.unique()} if not df_mes.empty else {}
    
    cols_h = st.columns(7)
    for i, d in enumerate(["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]): cols_h[i].markdown(f"<div class='{'cal-header-wknd' if i>=5 else 'cal-header'}'>{d}</div>", unsafe_allow_html=True)
    for sem in calendar.monthcalendar(st.session_state.anio_vista, st.session_state.mes_vista):
        cols_s = st.columns(7)
        for i, d in enumerate(sem):
            with cols_s[i]:
                if d != 0:
                    fc = date(st.session_state.anio_vista, st.session_state.mes_vista, d)
                    info = resumen_dias.get(fc, {"nas": False, "xau": False, "imp": -1})
                    mrc = " ".join([m for cond, m in [(info["nas"], "🇺🇸"), (info["xau"], "🪙")] if cond])
                    if st.button(f"{'📍' if fc == hoy_sel_date else ''}{d} {'🔴' if info['imp']==1 else '🟠' if info['imp']==0 else ''}\n{mrc}", key=f"pc_dia_{fc}", type="primary" if fc == f_sel else "secondary", use_container_width=True):
                        st.session_state.fecha_seleccionada = fc; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- RADAR BREAKING NEWS ---
    st.markdown("---")
    st.subheader("🚨 Radar de Noticias Imprevistas (Última Hora)")
    if breaking_news:
        cols_bn = st.columns(2)
        for idx, bn in enumerate(breaking_news[:6]):
            tag = " | ".join([t for t, c in [("🇺🇸 NAS100", bn['nas']), ("🪙 XAUUSD", bn['xau'])] if c])
            with cols_bn[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"**`🗽{bn['fecha_dt'].astimezone(tz_ny).strftime('%H:%M')} | {bandera_sel}{bn['fecha_dt'].astimezone(tz_sel).strftime('%H:%M')}` | {tag} | _{bn['fuente']}_**")
                    st.markdown(f"**[{traducir_texto(bn['titulo'], traductor_on)}]({bn['url']})**")
    else: st.info("Sin titulares imprevistos recientes.")

    # --- BOTÓN FLOTANTE CELULAR ---
    st.markdown('<div class="flotante-btn">', unsafe_allow_html=True)
    if st.button("🔄", key="btn_flotante_sync"):
        st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- GUÍA, VERSIÓN Y CONTADOR ---
    st.markdown("---")
    with st.expander("📖 Guía de Uso del Terminal Macro"):
        st.markdown(f"""
        **Terminal Macro v{VERSION_APP}** - Creado por **{AUTOR}**
        
        *   **Radar Normal (3m) / EN VIVO (10s):** El panel consulta el calendario económico automáticamente cada 3 minutos. Si detecta que faltan 2 minutos para una noticia, entra en "Modo Francotirador" y se actualiza cada 10 segundos para traerte el dato real al instante.
        *   **Botón Traducir:** Actívalo para convertir automáticamente los términos financieros del inglés al español.
        *   **Filtros Inteligentes:** El panel izquierdo (NAS100) limpia el ruido mundial y solo muestra datos de EE.UU. que muevan tecnología. El panel derecho (XAUUSD) muestra datos de EE.UU. más los países del G7 que impactan la liquidez global (China, Europa, Reino Unido, Canadá y Japón).
        *   **Auditoría de Proyección:** Compara el dato Real con el Pronóstico y el Anterior, dictando instantáneamente si el resultado es `ALCISTA` o `BAJISTA` para el activo correspondiente.
        """)
        
    st.markdown(
        f'<div class="footer-info">'
        f'v{VERSION_APP} • {AUTOR} <br><br>'
        f'<img src="https://visitor-badge.laobi.icu/badge?page_id=RiRo92.terminal-macro-trading&left_text=Vistas" alt="Vistas">'
        f'</div>', 
        unsafe_allow_html=True
    )

renderizar_terminal()