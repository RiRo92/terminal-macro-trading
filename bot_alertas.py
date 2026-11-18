import os
import requests
import pandas as pd
from datetime import datetime, timedelta, date
import pytz
import calendar

# Obtener claves seguras desde GitHub Secrets
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=datos, timeout=5)
    except:
        pass

def obtener_datos():
    ahora_utc = datetime.now(pytz.utc)
    anio, mes = ahora_utc.year, ahora_utc.month
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
    inicio_utc = (datetime.combine(date(anio, mes, 1), datetime.min.time()) - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
    fin_utc = (datetime.combine(ultimo_dia, datetime.max.time()) + timedelta(days=1)).strftime('%Y-%m-%dT23:59:59.000Z')
    
    headers = {"User-Agent": "Mozilla/5.0"}
    eventos = []
    
    # 1. TradingView
    try:
        res_tv = requests.get("https://economic-calendar.tradingview.com/events", params={"from": inicio_utc, "to": fin_utc, "countries": "US,CA,CN,EU,JP,GB"}, headers=headers, timeout=10)
        if res_tv.status_code == 200:
            for ev in res_tv.json().get('result', []):
                eventos.append({
                    "title": ev.get('title'),
                    "date": pd.to_datetime(ev.get('date'), utc=True),
                    "importance": ev.get('importance', -1),
                    "country": ev.get('country')
                })
    except: pass

    # 2. Forex Factory (Discursos)
    try:
        res_ff = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", headers=headers, timeout=10)
        if res_ff.status_code == 200:
            mapa_imp = {"High": 1, "Medium": 0, "Low": -1}
            mapa_pais = {"USD": "US", "CAD": "CA", "CNY": "CN", "EUR": "EU", "JPY": "JP", "GBP": "GB"}
            for ev in res_ff.json():
                divisa = ev.get("country", "")
                if divisa in mapa_pais:
                    titulo = str(ev.get("title", "")).strip()
                    es_discurso = any(k in titulo.lower() for k in ["speaks", "speech", "testifies", "statement", "press conference", "minutes", "fed chair", "fomc", "member"])
                    if es_discurso or (not str(ev.get("previous")).strip() and not str(ev.get("forecast")).strip()):
                        eventos.append({
                            "title": f"🎙️ {titulo}" if es_discurso else titulo,
                            "date": pd.to_datetime(ev.get("date"), utc=True),
                            "importance": mapa_imp.get(ev.get("impact"), -1),
                            "country": mapa_pais[divisa]
                        })
    except: pass
    
    return pd.DataFrame(eventos)

def revisar_y_alertar():
    df = obtener_datos()
    if df.empty: return
    
    # Limpiar duplicados
    df['title_lower'] = df['title'].str.lower().str.replace('🎙️ ', '')
    df = df.drop_duplicates(subset=['date', 'title_lower']).copy()
    
    ahora_utc = datetime.now(pytz.utc)
    # Rango de alerta: Todo lo que vaya a ocurrir entre AHORA y los próximos 5 minutos y 30 segundos
    limite_superior = ahora_utc + timedelta(minutes=5, seconds=30)
    
    for _, r in df.iterrows():
        fecha_ev = r['date']
        imp = r['importance']
        
        # Filtro: Solo alertar Alto (1) y Medio (0) impacto
        if imp in [1, 0] and (ahora_utc < fecha_ev <= limite_superior):
            imp_icono = "🔴 ALTO IMPACTO" if imp == 1 else "🟠 MEDIO IMPACTO"
            banderas = {"US": "🇺🇸", "CA": "🇨🇦", "CN": "🇨🇳", "EU": "🇪🇺", "JP": "🇯🇵", "GB": "🇬🇧"}
            bandera = banderas.get(r['country'], "🌐")
            hora_ny = fecha_ev.astimezone(pytz.timezone('America/New_York')).strftime('%H:%M')
            hora_bo = fecha_ev.astimezone(pytz.timezone('America/La_Paz')).strftime('%H:%M')
            
            mensaje = f"🚨 *ATENCIÓN: NOTICIA EN 5 MINUTOS* 🚨\n\n"
            mensaje += f"*{imp_icono}*\n"
            mensaje += f"📌 {bandera} {r['title']}\n"
            mensaje += f"🕒 *NY:* {hora_ny} | *BO:* {hora_bo}\n\n"
            mensaje += f"💻 _Terminal Macro automatizada_"
            
            enviar_mensaje_telegram(mensaje)

if __name__ == "__main__":
    revisar_y_alertar()