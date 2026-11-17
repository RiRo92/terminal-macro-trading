import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date
import calendar
import pytz
import html

# 1. Configuración de pantalla completa y compacta
st.set_page_config(page_title="Terminal Macro & Breaking News: NAS100 & XAUUSD", layout="wide", initial_sidebar_state="collapsed")

# API Key gratuita de Finnhub
FINNHUB_API_KEY = "dbtk2ehr01qtr41fbk30dbtk2ehr01qtr41fbk3g"

# Estilos CSS Responsivos
st.markdown("""
    <style>
        .block-container { padding-top: 3.3rem !important; padding-bottom: 1rem; }
        h1 { font-size: 1.6rem !important; margin-bottom: 0rem !important; }
        
        /* Cinta horizontal tipo noticiero */
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            background-color: #0F172A;
            border: 2px solid #3B82F6;
            border-radius: 8px;
            padding: 10px 0;
            margin-bottom: 14px;
            white-space: nowrap;
            box-sizing: border-box;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        }
        .ticker-move {
            display: inline-block;
            padding-left: 10%;
            animation: ticker-scroll 130s linear infinite;
        }
        .ticker-wrap:hover .ticker-move {
            animation-play-state: paused;
        }
        @keyframes ticker-scroll {
            0%   { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-100%, 0, 0); }
        }
        .ticker-item {
            display: inline-block;
            padding: 0 30px;
            font-size: 0.95rem;
            color: #F8FAFC;
            border-right: 1px solid #475569;
        }
        .badge-nas { background-color: #2563EB; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        .badge-xau { background-color: #D97706; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        .badge-brk { background-color: #DC2626; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 0.78rem; }
        
        /* Encabezados de días de la semana en el calendario PC */
        .cal-header, .cal-header-wknd {
            text-align: center;
            font-weight: bold;
            padding: 6px;
            border-radius: 4px;
            margin-bottom: 4px;
            font-size: 0.85rem;
        }
        .cal-header { background-color: #1F2937; color: #F9FAFB; }
        .cal-header-wknd { background-color: #451A1A; color: #FCA5A5; }

        /* Tarjetas móviles limpias */
        .mob-card {
            background-color: #111827;
            border: 1px solid #374151;
            border-left: 4px solid #3B82F6;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
        }
        .mob-card-high { border-left-color: #EF4444; }
        .mob-card-med  { border-left-color: #F59E0B; }
        .mob-card-low  { border-left-color: #10B981; }
        .mob-top { font-size: 0.92rem; font-weight: 600; color: #F9FAFB; margin-bottom: 5px; line-height: 1.3; }
        .mob-nums { font-size: 0.80rem; color: #9CA3AF; margin-bottom: 5px; }
        .mob-nums code { color: #E5E7EB; background-color: #1F2937; padding: 1px 5px; border-radius: 4px; }
        .mob-proy { font-size: 0.84rem; font-weight: bold; color: #E5E7EB; }

        /* --- DETECCIÓN AUTOMÁTICA DE PANTALLA EN STREAMLIT --- */
        @media (min-width: 769px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-movil) { display: none !important; }
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-pc) div[data-testid="column"] button {
                height: 68px !important; padding: 4px !important; line-height: 1.25 !important; font-size: 0.82rem !important;
            }
        }
        @media (max-width: 768px) {
            .block-container { padding-top: 2.8rem !important; padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
            div[data-testid="stVerticalBlock"]:has(> div.element-container .marker-pc) { display: none !important; }
            .ticker-wrap { padding: 7px 0; margin-bottom: 10px; }
            .ticker-item { font-size: 0.84rem; padding: 0 18px; }
        }
    </style>
""", unsafe_allow_html=True)

# 2A. Descarga protegida del feed semanal de Forex Factory
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
            datos = res.json()
            mapa_imp_ff = {"High": 1, "Medium": 0, "Low": -1, "Holiday": -1}
            mapa_pais_ff = {"USD": "US", "CAD": "CA", "CNY": "CN", "EUR": "EU", "JPY": "JP", "GBP": "GB"}
            
            for ev in datos:
                divisa = ev.get("country", "")
                if divisa not in mapa_pais_ff: continue
                
                titulo = str(ev.get("title", "")).strip()
                palabras_discurso = ["speaks", "speech", "testifies", "statement", "press conference", "minutes", "fed chair", "fomc", "member", "gov", "president", "boc", "ecb", "boj", "boe"]
                es_discurso = any(k in titulo.lower() for k in palabras_discurso)
                
                prev_val = str(ev.get("previous", "")).strip()
                fore_val = str(ev.get("forecast", "")).strip()
                
                if es_discurso or (prev_val == "" and fore_val == ""):
                    dt_parsed = pd.to_datetime(ev.get("date"), utc=True)
                    eventos_ff.append({
                        "date": dt_parsed,
                        "country": mapa_pais_ff[divisa],
                        "title": f"🎙️ {titulo}" if es_discurso else titulo,
                        "importance": mapa_imp_ff.get(ev.get("impact"), -1),
                        "previous": prev_val if prev_val != "" else None,
                        "forecast": fore_val if fore_val != "" else None,
                        "actual": None,
                        "unit": "",
                        "es_discurso": es_discurso
                    })
    except Exception:
        pass

    df_resultado = pd.DataFrame(eventos_ff)
    if not df_resultado.empty:
        st.session_state.ff_cache_df = df_resultado
        st.session_state.ff_cache_time = ahora
        return df_resultado
    elif 'ff_cache_df' in st.session_state:
        return st.session_state.ff_cache_df
    return pd.DataFrame()

# 2B. Descarga de datos del calendario económico
@st.cache_data(ttl=10)
def obtener_datos_mes_rapido(anio, mes, bloque_tiempo):
    primer_dia = date(anio, mes, 1)
    ultimo_dia_num = calendar.monthrange(anio, mes)[1]
    ultimo_dia = date(anio, mes, ultimo_dia_num)
    
    inicio_utc = (datetime.combine(primer_dia, datetime.min.time()) - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
    fin_utc = (datetime.combine(ultimo_dia, datetime.max.time()) + timedelta(days=1)).strftime('%Y-%m-%dT23:59:59.000Z')
    
    url = "https://economic-calendar.tradingview.com/events"
    params = {"from": inicio_utc, "to": fin_utc, "countries": "US,CA,CN,EU,JP,GB"}
    headers = {"Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/", "User-Agent": "Mozilla/5.0"}
    
    df_tv = pd.DataFrame()
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        datos = res.json()
        if 'result' in datos and datos['result']:
            df_tv = pd.DataFrame(datos['result'])
            df_tv['date'] = pd.to_datetime(df_tv['date'], utc=True)
            df_tv['es_discurso'] = df_tv['title'].str.lower().str.contains('speaks|speech|testifies|statement|press conference|minutes|fed chair|fomc', na=False)
    except Exception:
        pass
    return df_tv

def fusionar_calendario_y_discursos(df_tv, anio, mes):
    df_ff = obtener_discursos_ff()
    if df_ff.empty: 
        return df_tv
    df_ff_mes = df_ff[(df_ff['date'].dt.year == anio) & (df_ff['date'].dt.month == mes)].copy()
    if df_ff_mes.empty: 
        return df_tv
    if df_tv.empty: 
        return df_ff_mes
        
    titulos_tv = set(df_tv['title'].str.lower().str.replace('🎙️ ', '', regex=False).str[:15])
    nuevos_ff = df_ff_mes[~df_ff_mes['title'].str.lower().str.replace('🎙️ ', '', regex=False).str[:15].isin(titulos_tv)]
    
    df_res = pd.concat([df_tv, nuevos_ff], ignore_index=True)
    df_res['date'] = pd.to_datetime(df_res['date'], utc=True)
    return df_res

# 3. Descarga de Noticias Imprevistas / Breaking News
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
            datos = res.json()
            for item in datos[:45]:
                titulo = item.get('headline', '')
                resumen = item.get('summary', '')
                texto_busqueda = (titulo + " " + resumen).lower()
                
                if any(ex in texto_busqueda for ex in excluir): continue
                afecta_xau = any(k in texto_busqueda for k in kw_xau)
                afecta_nas = any(k in texto_busqueda for k in kw_nas)
                
                if afecta_xau or afecta_nas:
                    dt_utc = datetime.fromtimestamp(item.get('datetime', 0), tz=tz_utc)
                    noticias_filtradas.append({
                        "fecha_dt": dt_utc,
                        "titulo": titulo,
                        "resumen": resumen,
                        "fuente": item.get('source', 'Mercado'),
                        "url": item.get('url', '#'),
                        "nas": afecta_nas,
                        "xau": afecta_xau
                    })
    except Exception:
        pass
    return noticias_filtradas

# 4. Filtros por Activo
def es_relevante_nas100(fila, filtro_estricto=False):
    if fila.get('country') != 'US': return False
    if not filtro_estricto: return True
    titulo = str(fila.get('title', '')).lower()
    ruido_nas = ['3-month', '6-month', '4-week', '8-week', '52-week', 'bill auction', 'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado', 'crude', 'petróleo', 'oil', 'gasoline', 'gasolina', 'natural gas', 'gas natural', 'baker hughes', 'rig count', 'distillate', 'cushing', 'eia', 'api weekly']
    return not any(palabra in titulo for palabra in ruido_nas)

def es_relevante_xauusd(fila, filtro_estricto=False):
    pais = fila.get('country')
    imp = fila.get('importance', -1)
    titulo = str(fila.get('title', '')).lower()
    if pais in ['CA', 'CN', 'EU', 'JP', 'GB']: return imp == 1
    if pais == 'US':
        if not filtro_estricto: return True
        ruido_xau = ['3-month', '6-month', '4-week', '8-week', '52-week', 'bill auction', 'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado', 'cotton', 'algodón']
        return not any(palabra in titulo for palabra in ruido_xau)
    return False

# 5. Lógica de Proyección + Auditoría + Discursos
def obtener_sesgo_compacto(fila, activo, ahora_utc):
    actual = fila.get('actual')
    pronostico = fila.get('forecast')
    anterior = fila.get('previous')
    pais = fila.get('country', 'US')
    es_discurso = fila.get('es_discurso', False)
    fecha_ev = fila.get('date')

    if es_discurso and (pd.isna(actual) or actual is None):
        if pd.notna(fecha_ev) and fecha_ev <= ahora_utc: return "🎙️ Discurso realizado (Revisar tono Hawkish/Dovish)"
        return "🎙️ Pendiente (Alta volatilidad en vivo)"

    es_extranjera = (pais in ['CA', 'CN', 'EU', 'JP', 'GB'])
    tiene_actual = pd.notna(actual) and actual is not None
    tiene_pron = pd.notna(pronostico) and pronostico is not None
    tiene_ant = pd.notna(anterior) and anterior is not None
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
        elif dir_esperada == -1: return "⏳ Pendiente (Se espera Caída 📉)"
        elif dir_esperada == 0: return "⏳ Pendiente (Se espera Neutral ➖)"
        return "⏳ Pendiente (Sin pronóstico)"

    referencia = pronostico if tiene_pron else anterior
    if pd.isna(referencia) or referencia is None: return "ℹ️ Publicado"
    try:
        act, ref = float(actual), float(referencia)
        if act > ref:
            dir_real = 1 if es_extranjera else -1
            etiqueta_base = "🟢 ALCISTA" if es_extranjera else "🔴 BAJISTA"
        elif act < ref:
            dir_real = -1 if es_extranjera else 1
            etiqueta_base = "🔴 BAJISTA" if es_extranjera else "🟢 ALCISTA"
        else:
            dir_real = 0
            etiqueta_base = "⚪ NEUTRAL"

        if tiene_pron and dir_esperada is not None:
            if act == float(pronostico): estado = "🎯 Exacto"
            elif dir_real == dir_esperada: estado = "✅ Cumplido"
            else: estado = "❌ Al contrario"
            return f"{etiqueta_base} | {estado}"
        else: return f"{etiqueta_base} (Vs. Anterior)"
    except: return "ℹ️ Publicado"

def formatear_num(val, unidad):
    if pd.notna(val) and val is not None and str(val).strip() != "":
        u = unidad if pd.notna(unidad) else ''
        return f"{val}{u}"
    return "-"

def construir_tarjetas_movil(filas_lista, etiqueta_tz, bandera_tz):
    if not filas_lista: return "<p style='color:#9CA3AF; font-size:0.9rem;'>Sin eventos programados para esta fecha.</p>"
    html_cards = []
    for f in filas_lista:
        imp_ico = f["Imp"]
        clase_borde = "mob-card-high" if imp_ico == "🔴" else "mob-card-med" if imp_ico == "🟠" else "mob-card-low"
        titulo_limpio = html.escape(str(f["Noticia"]))
        proy_limpia = html.escape(str(f["Proy"]))
        card = f"""
        <div class="mob-card {clase_borde}">
            <div class="mob-top">{imp_ico} 🗽 {f['NY']} | {bandera_tz} {f[etiqueta_tz]} — {titulo_limpio}</div>
            <div class="mob-nums">Ant: <code>{f['Ant']}</code> &nbsp;|&nbsp; Pron: <code>{f['Pron']}</code> &nbsp;|&nbsp; Real: <code>{f['Real']}</code></div>
            <div class="mob-proy">{proy_limpia}</div>
        </div>
        """
        html_cards.append(card)
    return "".join(html_cards)

# 6. Estado de sesión para zonas horarias
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

tz_utc = pytz.utc
ahora_utc = datetime.now(tz_utc)

if 'zona_seleccionada' not in st.session_state: 
    st.session_state.zona_seleccionada = "Bolivia"
    
if 'fecha_seleccionada' not in st.session_state:
    st.session_state.fecha_seleccionada = ahora_utc.astimezone(pytz.timezone(ZONAS_HORARIAS[st.session_state.zona_seleccionada]["tz"])).date()
if 'mes_vista' not in st.session_state: st.session_state.mes_vista = st.session_state.fecha_seleccionada.month
if 'anio_vista' not in st.session_state: st.session_state.anio_vista = st.session_state.fecha_seleccionada.year
if 'modo_francotirador' not in st.session_state: st.session_state.modo_francotirador = False

def calcular_intervalo_refresco(df_hoy, ahora_utc):
    if df_hoy.empty: return 180, False
    for _, r in df_hoy.iterrows():
        fecha_ev = r['date']
        diff_segundos = (fecha_ev - ahora_utc).total_seconds()
        tiene_real = pd.notna(r.get('actual')) and r.get('actual') is not None
        es_discurso = r.get('es_discurso', False)
        if not es_discurso and not tiene_real and (-300 <= diff_segundos <= 120): return 10, True
    return 180, False

# 7. Panel Principal
@st.fragment(run_every=10)
def renderizar_terminal():
    tz_ny = pytz.timezone('America/New_York')
    tz_sel = pytz.timezone(ZONAS_HORARIAS[st.session_state.zona_seleccionada]["tz"])
    bandera_sel = ZONAS_HORARIAS[st.session_state.zona_seleccionada]["bandera"]
    etiqueta_sel = ZONAS_HORARIAS[st.session_state.zona_seleccionada]["etiqueta"]
    
    ahora_utc = datetime.now(pytz.utc)
    ahora_ny = ahora_utc.astimezone(tz_ny)
    ahora_sel = ahora_utc.astimezone(tz_sel)
    hoy_sel_date = ahora_sel.date()
    
    divisor_cache = 10 if st.session_state.modo_francotirador else 180
    bloque_tiempo = int(ahora_utc.timestamp() // divisor_cache)
    
    df_tv_mes = obtener_datos_mes_rapido(st.session_state.anio_vista, st.session_state.mes_vista, bloque_tiempo)
    df_mes = fusionar_calendario_y_discursos(df_tv_mes, st.session_state.anio_vista, st.session_state.mes_vista)
    
    df_tv_actual = obtener_datos_mes_rapido(hoy_sel_date.year, hoy_sel_date.month, bloque_tiempo)
    df_actual = fusionar_calendario_y_discursos(df_tv_actual, hoy_sel_date.year, hoy_sel_date.month)
    
    if not df_actual.empty:
        df_hoy_solo = df_actual[df_actual['date'].dt.tz_convert(tz_sel).dt.date == hoy_sel_date]
        _, activar_sniper = calcular_intervalo_refresco(df_hoy_solo, ahora_utc)
        st.session_state.modo_francotirador = activar_sniper
    else:
        st.session_state.modo_francotirador = False

    breaking_news = obtener_breaking_news(FINNHUB_API_KEY)
    
    # --- A. CINTA HORIZONTAL ---
    items_ticker = []
    for bn in breaking_news[:5]:
        if bn['fecha_dt'] >= (ahora_utc - timedelta(hours=6)):
            badges = '<span class="badge-brk">🚨 ÚLTIMA HORA</span> '
            if bn['nas']: badges += '<span class="badge-nas">NAS100</span> '
            if bn['xau']: badges += '<span class="badge-xau">XAUUSD</span> '
            hora_bn_ny = bn['fecha_dt'].astimezone(tz_ny).strftime('%H:%M')
            items_ticker.append(f'<div class="ticker-item">{badges} <b>[🗽 {hora_bn_ny}] {html.escape(bn["titulo"])}</b> <i>({html.escape(bn["fuente"])})</i></div>')

    if not df_actual.empty:
        df_futuras = df_actual[(df_actual['date'] >= ahora_utc - timedelta(minutes=30))].sort_values(by='date', ascending=True)
        for _, r in df_futuras.head(10).iterrows():
            es_nas = es_relevante_nas100(r, False)
            es_xau = es_relevante_xauusd(r, False)
            if not (es_nas or es_xau): continue
                
            imp_ico = "🔴" if r.get('importance') == 1 else "🟠" if r.get('importance') == 0 else "🟡"
            hora_ny_t = r['date'].astimezone(tz_ny).strftime('%H:%M')
            hora_sel_t = r['date'].astimezone(tz_sel).strftime('%H:%M')
            ant_t, pron_t, real_t = formatear_num(r.get('previous'), r.get('unit')), formatear_num(r.get('forecast'), r.get('unit')), formatear_num(r.get('actual'), r.get('unit'))
            activos_html = ('<span class="badge-nas">NAS100</span> ' if es_nas else '') + ('<span class="badge-xau">XAUUSD</span> ' if es_xau else '')
            proy_t = obtener_sesgo_compacto(r, "XAU" if es_xau else "NAS", ahora_utc)
            
            items_ticker.append(
                f'<div class="ticker-item">{imp_ico} <b>🗽{hora_ny_t} | {bandera_sel}{hora_sel_t}</b> | {activos_html} <b>{html.escape(str(r["title"]))}</b> — '
                f'Ant: <code>{ant_t}</code> | Pron: <code>{pron_t}</code> | Real: <code>{real_t}</code> → <b>{html.escape(proy_t)}</b></div>'
            )

    if items_ticker: st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{"".join(items_ticker)}</div></div>', unsafe_allow_html=True)
    else: st.markdown('<div class="ticker-wrap"><div class="ticker-move"><div class="ticker-item">📡 Monitoreando mercados en vivo... Sin eventos próximos.</div></div></div>', unsafe_allow_html=True)

    resumen_dias = {}
    if not df_mes.empty:
        df_mes['fecha_corta'] = df_mes['date'].dt.tz_convert(tz_sel).dt.date
        for f, grupo in df_mes.groupby('fecha_corta'):
            filas_nas_dia = [r for _, r in grupo.iterrows() if es_relevante_nas100(r, False)]
            filas_xau_dia = [r for _, r in grupo.iterrows() if es_relevante_xauusd(r, False)]
            imp_relevantes = [r.get('importance', -1) for r in (filas_nas_dia + filas_xau_dia) if pd.notna(r.get('importance'))]
            resumen_dias[f] = {"nas": len(filas_nas_dia) > 0, "xau": len(filas_xau_dia) > 0, "imp": max(imp_relevantes) if imp_relevantes else -1}

    meses_es = ["", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

    # --- B1. SELECTOR NATIVO COMPACTO (CELULAR) ---
    with st.container():
        st.markdown('<span class="marker-movil"></span>', unsafe_allow_html=True)
        col_m_fecha, col_m_btn = st.columns([3, 1])
        with col_m_fecha:
            nueva_fecha_mob = st.date_input("📅 Fecha:", value=st.session_state.fecha_seleccionada, format="DD/MM/YYYY", key="mob_native_date")
            if nueva_fecha_mob != st.session_state.fecha_seleccionada:
                st.session_state.fecha_seleccionada = nueva_fecha_mob
                st.session_state.mes_vista = nueva_fecha_mob.month
                st.session_state.anio_vista = nueva_fecha_mob.year
                st.rerun()
        with col_m_btn:
            st.write("")
            if st.button("🔄 Sync", key="mob_sync_btn", use_container_width=True):
                if 'ff_cache_time' in st.session_state: del st.session_state['ff_cache_time']
                st.cache_data.clear()
                st.rerun()

    # --- B2. CALENDARIO MENSUAL COMPLETO (PC) ---
    with st.container():
        st.markdown('<span class="marker-pc"></span>', unsafe_allow_html=True)
        c_prev, c_mes, c_next, c_hoy, c_act = st.columns([1, 4, 1, 1.5, 1.5])
        with c_prev:
            if st.button("◀ Mes Ant.", key="pc_prev_m", use_container_width=True):
                st.session_state.mes_vista = 12 if st.session_state.mes_vista == 1 else st.session_state.mes_vista - 1
                if st.session_state.mes_vista == 12: st.session_state.anio_vista -= 1
                st.rerun()
        with c_mes: st.markdown(f"<h2 style='text-align:center; margin:0; color:#EF4444;'>📅 {meses_es[st.session_state.mes_vista]} {st.session_state.anio_vista}</h2>", unsafe_allow_html=True)
        with c_next:
            if st.button("Mes Sig. ▶", key="pc_next_m", use_container_width=True):
                st.session_state.mes_vista = 1 if st.session_state.mes_vista == 12 else st.session_state.mes_vista + 1
                if st.session_state.mes_vista == 1: st.session_state.anio_vista += 1
                st.rerun()
        with c_hoy:
            if st.button("📍 Ir a Hoy", key="pc_hoy", use_container_width=True):
                st.session_state.fecha_seleccionada = hoy_sel_date
                st.session_state.mes_vista = hoy_sel_date.month
                st.session_state.anio_vista = hoy_sel_date.year
                st.rerun()
        with c_act:
            if st.button("🔄 Actualizar", key="pc_sync", use_container_width=True):
                if 'ff_cache_time' in st.session_state: del st.session_state['ff_cache_time']
                st.cache_data.clear()
                st.rerun()

        cols_header = st.columns(7)
        for i, nombre_dia in enumerate(["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]):
            cols_header[i].markdown(f"<div class='{'cal-header-wknd' if i>=5 else 'cal-header'}'>{nombre_dia}</div>", unsafe_allow_html=True)

        for semana in calendar.monthcalendar(st.session_state.anio_vista, st.session_state.mes_vista):
            cols_sem = st.columns(7)
            for i, num_dia in enumerate(semana):
                with cols_sem[i]:
                    if num_dia == 0: st.write("")
                    else:
                        fecha_celda = date(st.session_state.anio_vista, st.session_state.mes_vista, num_dia)
                        info = resumen_dias.get(fecha_celda, {"nas": False, "xau": False, "imp": -1})
                        marcas = []
                        if info["nas"]: marcas.append("🇺🇸NAS")
                        if info["xau"]: marcas.append("🪙XAU")
                        imp_dot = "🔴" if info["imp"] == 1 else "🟠" if info["imp"] == 0 else ""
                        if st.button(f"{'📍' if fecha_celda == hoy_sel_date else ''}{num_dia} {imp_dot}\n{' '.join(marcas) if marcas else 'Sin eventos'}", key=f"pc_dia_{fecha_celda}", type="primary" if fecha_celda == st.session_state.fecha_seleccionada else "secondary", use_container_width=True):
                            st.session_state.fecha_seleccionada = fecha_celda
                            st.rerun()

    st.markdown("---")

    # --- D. DETALLE DEL DÍA SELECCIONADO ---
    f_sel = st.session_state.fecha_seleccionada
    estado_radar = "⚡ EN VIVO (10s)" if st.session_state.modo_francotirador else "🟢 Normal (3m)"
    
    # 3 Columnas principales (Con selector de Zona Horaria incluido)
    c_tit_dia, c_check_ruido, c_filtro_imp, c_tz = st.columns([4.0, 1.8, 1.7, 1.5])
    with c_tit_dia:
        st.subheader(f"📋 {f_sel.strftime('%d/%m/%Y')} | 🗽 NY {ahora_ny.strftime('%H:%M')} • {bandera_sel} {etiqueta_sel} {ahora_sel.strftime('%H:%M')} | {estado_radar}")
    with c_check_ruido:
        st.write("")
        filtro_estricto = st.checkbox("🛡️ Ocultar letras y agrícolas", value=False)
    with c_filtro_imp:
        filtro_imp = st.multiselect("Impacto:", options=["Alto", "Medio", "Bajo"], default=["Alto", "Medio", "Bajo"], label_visibility="collapsed")
    with c_tz:
        nueva_zona = st.selectbox("🌍 Zona Horaria:", options=OPCIONES_ZONAS, index=OPCIONES_ZONAS.index(st.session_state.zona_seleccionada), label_visibility="collapsed")
        if nueva_zona != st.session_state.zona_seleccionada:
            st.session_state.zona_seleccionada = nueva_zona
            st.rerun()

    if not df_mes.empty:
        df_dia = df_mes[df_mes['fecha_corta'] == f_sel].copy()
        mapa_imp = {1: "Alto", 0: "Medio", -1: "Bajo"}
        mapa_icono = {1: "🔴", 0: "🟠", -1: "🟡"}
        df_dia['imp_texto'] = df_dia['importance'].map(lambda x: mapa_imp.get(x, "Bajo"))
        df_dia['Imp'] = df_dia['importance'].map(lambda x: mapa_icono.get(x, "🟡"))
        df_dia = df_dia[df_dia['imp_texto'].isin(filtro_imp)].sort_values(by='date', ascending=False)

        filas_nas, filas_xau = [], []
        filas_nas_mob, filas_xau_mob = [], []
        banderas = {"US": "🇺🇸", "CA": "🇨🇦", "CN": "🇨🇳", "EU": "🇪🇺", "JP": "🇯🇵", "GB": "🇬🇧"}
        
        for _, row in df_dia.iterrows():
            hora_ny_str = row['date'].astimezone(tz_ny).strftime('%H:%M')
            hora_sel_str = row['date'].astimezone(tz_sel).strftime('%H:%M')
            ant, pron, act, pais = formatear_num(row.get('previous'), row.get('unit')), formatear_num(row.get('forecast'), row.get('unit')), formatear_num(row.get('actual'), row.get('unit')), row.get('country', 'US')

            if es_relevante_nas100(row, filtro_estricto):
                sesgo_n = obtener_sesgo_compacto(row, "NAS", ahora_utc)
                datos_fila = {"Imp": row['Imp'], "🗽 NY": hora_ny_str, f"{bandera_sel} {etiqueta_sel}": hora_sel_str, "Noticia (EE.UU. & Fed)": row['title'], "Ant": ant, "Pron": pron, "Real": act, "Proyección y Auditoría": sesgo_n}
                filas_nas.append(datos_fila)
                filas_nas_mob.append({"Imp": row['Imp'], "NY": hora_ny_str, etiqueta_sel: hora_sel_str, "Noticia": row['title'], "Ant": ant, "Pron": pron, "Real": act, "Proy": sesgo_n})

            if es_relevante_xauusd(row, filtro_estricto):
                titulo_x = f"{banderas.get(pais, '🌐')} {row['title']}"
                sesgo_x = obtener_sesgo_compacto(row, "XAU", ahora_utc)
                datos_fila_x = {"Imp": row['Imp'], "🗽 NY": hora_ny_str, f"{bandera_sel} {etiqueta_sel}": hora_sel_str, "Noticia (USD, CAD, CNY, EUR, JPY, GBP)": titulo_x, "Ant": ant, "Pron": pron, "Real": act, "Proyección y Auditoría": sesgo_x}
                filas_xau.append(datos_fila_x)
                filas_xau_mob.append({"Imp": row['Imp'], "NY": hora_ny_str, etiqueta_sel: hora_sel_str, "Noticia": titulo_x, "Ant": ant, "Pron": pron, "Real": act, "Proy": sesgo_x})

        # 1. BLOQUE SOLO PARA COMPUTADORA
        with st.container():
            st.markdown('<span class="marker-pc"></span>', unsafe_allow_html=True)
            col_nas, col_xau = st.columns(2, gap="medium")
            with col_nas:
                st.markdown("#### 🇺🇸 NAS100 (Índice Nasdaq)")
                if filas_nas: st.dataframe(pd.DataFrame(filas_nas), use_container_width=True, hide_index=True)
                else: st.info("Sin eventos programados para NAS100 con los filtros actuales.")
            with col_xau:
                st.markdown("#### 🪙 XAUUSD (Oro / Dólar)")
                if filas_xau: st.dataframe(pd.DataFrame(filas_xau), use_container_width=True, hide_index=True)
                else: st.info("Sin eventos programados para XAUUSD con los filtros actuales.")

        # 2. BLOQUE SOLO PARA CELULAR
        with st.container():
            st.markdown('<span class="marker-movil"></span>', unsafe_allow_html=True)
            tab_nas, tab_xau = st.tabs([f"🇺🇸 NAS100 ({len(filas_nas_mob)})", f"🪙 XAUUSD ({len(filas_xau_mob)})"])
            with tab_nas: st.markdown(construir_tarjetas_movil(filas_nas_mob, etiqueta_sel, bandera_sel), unsafe_allow_html=True)
            with tab_xau: st.markdown(construir_tarjetas_movil(filas_xau_mob, etiqueta_sel, bandera_sel), unsafe_allow_html=True)

    else:
        st.warning("No se encontraron datos para el mes seleccionado.")

    # --- E. RADAR DE NOTICIAS IMPREVISTAS EN TIEMPO REAL ---
    st.markdown("---")
    st.subheader("🚨 Radar de Noticias Imprevistas (Última Hora)")
    if breaking_news:
        cols_bn = st.columns(2)
        for idx, bn in enumerate(breaking_news[:6]):
            tag_str = " | ".join([t for t, cond in [("🇺🇸 NAS100", bn['nas']), ("🪙 XAUUSD", bn['xau'])] if cond])
            hora_bn_ny = bn['fecha_dt'].astimezone(tz_ny).strftime('%H:%M')
            hora_bn_sel = bn['fecha_dt'].astimezone(tz_sel).strftime('%H:%M')
            with cols_bn[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"**`🗽{hora_bn_ny} | {bandera_sel}{hora_bn_sel}` | {tag_str} | _{bn['fuente']}_**")
                    st.markdown(f"**[{bn['titulo']}]({bn['url']})**")
                    if bn['resumen']: st.caption(bn['resumen'][:160] + "..." if len(bn['resumen']) > 160 else bn['resumen'])
    else:
        st.info("No se detectaron titulares imprevistos de alto impacto en las últimas horas.")

renderizar_terminal()