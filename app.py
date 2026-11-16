import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz

# 1. Configuración de pantalla completa y compacta
st.set_page_config(page_title="Terminal Macro: NAS100 & XAUUSD", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        h1 { font-size: 1.8rem !important; margin-bottom: 0rem !important; }
        h3 { font-size: 1.2rem !important; margin-top: 0.5rem !important; }
    </style>
""", unsafe_allow_html=True)

# 2. Descarga de datos (EE.UU. para ambos, más China y Eurozona para el Oro)
@st.cache_data(ttl=180)
def obtener_datos():
    tz_bolivia = pytz.timezone('America/La_Paz')
    ahora = datetime.now(tz_bolivia)
    
    inicio = (ahora - timedelta(days=4)).astimezone(pytz.utc).strftime('%Y-%m-%dT00:00:00.000Z')
    fin = (ahora + timedelta(days=4)).astimezone(pytz.utc).strftime('%Y-%m-%dT23:59:59.000Z')
    
    url = "https://economic-calendar.tradingview.com/events"
    params = {
        "from": inicio,
        "to": fin,
        "countries": "US,CN,EU"
    }
    headers = {
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        res = requests.get(url, params=params, headers=headers)
        datos = res.json()
        
        if 'result' in datos and datos['result']:
            df = pd.DataFrame(datos['result'])
            df['date'] = pd.to_datetime(df['date']).dt.tz_convert('America/La_Paz')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# 3. Filtros Inteligentes por Activo
def es_relevante_nas100(fila):
    if fila.get('country') != 'US':
        return False
    
    titulo = str(fila.get('title', '')).lower()
    ruido_nas = [
        'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado',
        'crude', 'petróleo', 'oil', 'gasoline', 'gasolina', 'natural gas', 'gas natural',
        'baker hughes', 'rig count', 'distillate', 'cushing', 'eia', 'api weekly'
    ]
    return not any(palabra in titulo for palabra in ruido_nas)

def es_relevante_xauusd(fila):
    pais = fila.get('country')
    imp = fila.get('importance', -1)
    titulo = str(fila.get('title', '')).lower()
    
    if pais in ['CN', 'EU']:
        return imp == 1
        
    if pais == 'US':
        ruido_agricola = [
            'nopa', 'soybean', 'soja', 'wheat', 'trigo', 'corn', 'maíz', 'cattle', 'ganado', 'cotton', 'algodón'
        ]
        return not any(palabra in titulo for palabra in ruido_agricola)
        
    return False

# 4. Lógica de Proyección + Auditoría de Cumplimiento
def obtener_sesgo_compacto(actual, pronostico, anterior, activo, pais):
    es_extranjera = (pais in ['CN', 'EU'])
    tiene_actual = pd.notna(actual) and actual is not None
    tiene_pron = pd.notna(pronostico) and pronostico is not None
    tiene_ant = pd.notna(anterior) and anterior is not None

    # Evaluar dirección esperada (Pronóstico vs Anterior)
    dir_esperada = None # 1 = Subida precio, -1 = Caída precio, 0 = Neutral
    if tiene_pron and tiene_ant:
        try:
            p, a = float(pronostico), float(anterior)
            if p > a:
                dir_esperada = 1 if es_extranjera else -1
            elif p < a:
                dir_esperada = -1 if es_extranjera else 1
            else:
                dir_esperada = 0
        except:
            pass

    # CASO A: Noticia aún NO sale (Pendiente)
    if not tiene_actual:
        if dir_esperada == 1:
            return "⏳ Pendiente (Se espera Subida 📈)"
        elif dir_esperada == -1:
            return "⏳ Pendiente (Se espera Caída 📉)"
        elif dir_esperada == 0:
            return "⏳ Pendiente (Se espera Neutral ➖)"
        return "⏳ Pendiente (Sin pronóstico)"

    # CASO B: Noticia YA salió -> Evaluar impacto real y comparar con lo que se esperaba
    referencia = pronostico if tiene_pron else anterior
    if pd.isna(referencia) or referencia is None:
        return "ℹ️ Publicado"

    try:
        act = float(actual)
        ref = float(referencia)
        
        # Determinar dirección real respecto a la referencia
        if act > ref:
            dir_real = 1 if es_extranjera else -1
            etiqueta_base = "🟢 ALCISTA" if es_extranjera else "🔴 BAJISTA"
        elif act < ref:
            dir_real = -1 if es_extranjera else 1
            etiqueta_base = "🔴 BAJISTA" if es_extranjera else "🟢 ALCISTA"
        else:
            dir_real = 0
            etiqueta_base = "⚪ NEUTRAL"

        # Verificar si se cumplió el pronóstico previo
        if tiene_pron and dir_esperada is not None:
            if act == float(pronostico):
                estado = "🎯 Exacto al pronóstico"
            elif dir_real == dir_esperada:
                estado = "✅ Cumplido"
            else:
                estado = "❌ Al contrario"
            return f"{etiqueta_base} | {estado}"
        else:
            return f"{etiqueta_base} (Vs. Anterior)"

    except:
        return "ℹ️ Publicado"

def formatear_num(val, unidad):
    if pd.notna(val) and val is not None:
        u = unidad if pd.notna(unidad) else ''
        return f"{val}{u}"
    return "-"

# 5. Encabezado Ultra-Compacto
col_t, col_b = st.columns([8, 1])
with col_t:
    st.title("📊 Terminal Macro Filtrada: NAS100 & XAUUSD")
with col_b:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 6. Panel Auto-Actualizable cada 3 minutos
@st.fragment(run_every=180)
def mostrar_dashboard_compacto():
    tz_bolivia = pytz.timezone('America/La_Paz')
    ahora = datetime.now(tz_bolivia)
    hoy = ahora.date()
    dia_semana = hoy.weekday()
    
    if dia_semana == 0:   ayer_op = hoy - timedelta(days=3)
    elif dia_semana == 6: ayer_op = hoy - timedelta(days=2)
    else:                 ayer_op = hoy - timedelta(days=1)
        
    if dia_semana == 4:   manana_op = hoy + timedelta(days=3)
    elif dia_semana == 5: manana_op = hoy + timedelta(days=2)
    else:                 manana_op = hoy + timedelta(days=1)

    df = obtener_datos()

    if not df.empty:
        df['fecha_corta'] = df['date'].dt.date
        df_filtrado = df[df['fecha_corta'].isin([ayer_op, hoy, manana_op])].copy()

        c_filtros, c_dias, c_reloj = st.columns([3, 4, 2])
        with c_filtros:
            filtro_imp = st.multiselect(
                "Impacto:", options=["Alto", "Medio", "Bajo"], default=["Alto", "Medio", "Bajo"], label_visibility="collapsed"
            )
        with c_dias:
            filtro_dia = st.multiselect(
                "Días:", 
                options=[f"Ayer ({ayer_op.strftime('%d/%m')})", f"Hoy ({hoy.strftime('%d/%m')})", f"Mañana ({manana_op.strftime('%d/%m')})"],
                default=[f"Ayer ({ayer_op.strftime('%d/%m')})", f"Hoy ({hoy.strftime('%d/%m')})", f"Mañana ({manana_op.strftime('%d/%m')})"],
                label_visibility="collapsed"
            )
        with c_reloj:
            st.caption(f"🕒 Sync: `{ahora.strftime('%H:%M:%S')}` (Auto 3m)")

        if not df_filtrado.empty:
            mapa_imp = {1: "Alto", 0: "Medio", -1: "Bajo"}
            mapa_icono = {1: "🔴", 0: "🟠", -1: "🟡"}
            
            df_filtrado['imp_texto'] = df_filtrado['importance'].map(lambda x: mapa_imp.get(x, "Bajo"))
            df_filtrado['Imp'] = df_filtrado['importance'].map(lambda x: mapa_icono.get(x, "🟡"))
            
            def etiquetar_dia(f):
                if f == hoy: return f"Hoy ({hoy.strftime('%d/%m')})"
                elif f == ayer_op: return f"Ayer ({ayer_op.strftime('%d/%m')})"
                else: return f"Mañana ({manana_op.strftime('%d/%m')})"
                
            df_filtrado['Etiqueta_Dia'] = df_filtrado['fecha_corta'].apply(etiquetar_dia)
            
            df_filtrado = df_filtrado[
                (df_filtrado['imp_texto'].isin(filtro_imp)) & 
                (df_filtrado['Etiqueta_Dia'].isin(filtro_dia))
            ]

            df_filtrado = df_filtrado.sort_values(by='date', ascending=False)

            filas_nas = []
            filas_xau = []

            for _, row in df_filtrado.iterrows():
                fecha_hora = row['date'].strftime('%d/%m %H:%M')
                ant = formatear_num(row.get('previous'), row.get('unit'))
                pron = formatear_num(row.get('forecast'), row.get('unit'))
                act = formatear_num(row.get('actual'), row.get('unit'))
                pais = row.get('country', 'US')
                
                if es_relevante_nas100(row):
                    sesgo_nas = obtener_sesgo_compacto(row.get('actual'), row.get('forecast'), row.get('previous'), "NAS", pais)
                    filas_nas.append({
                        "Imp": row['Imp'],
                        "Fecha/Hora": fecha_hora,
                        "Noticia (Solo Tech/Tasas)": row['title'],
                        "Ant": ant,
                        "Pron": pron,
                        "Real": act,
                        "Proyección y Resultado": sesgo_nas
                    })

                if es_relevante_xauusd(row):
                    bandera = "🇺🇸" if pais == "US" else "🇨🇳" if pais == "CN" else "🇪🇺"
                    sesgo_xau = obtener_sesgo_compacto(row.get('actual'), row.get('forecast'), row.get('previous'), "XAU", pais)
                    filas_xau.append({
                        "Imp": row['Imp'],
                        "Fecha/Hora": fecha_hora,
                        "Noticia (Macro/Oro)": f"{bandera} {row['title']}",
                        "Ant": ant,
                        "Pron": pron,
                        "Real": act,
                        "Proyección y Resultado": sesgo_xau
                    })

            col_nas, col_xau = st.columns(2, gap="medium")

            with col_nas:
                st.subheader("🇺🇸 NAS100 (Filtro Tecnológico/Tasas)")
                st.dataframe(
                    pd.DataFrame(filas_nas),
                    use_container_width=True,
                    hide_index=True,
                    height=620
                )

            with col_xau:
                st.subheader("🪙 XAUUSD (Filtro Macro/Refugio/Energía)")
                st.dataframe(
                    pd.DataFrame(filas_xau),
                    use_container_width=True,
                    hide_index=True,
                    height=620
                )
        else:
            st.info("No hay noticias para los filtros seleccionados.")
    else:
        st.error("No se pudieron cargar los datos. Presiona Actualizar.")

mostrar_dashboard_compacto()