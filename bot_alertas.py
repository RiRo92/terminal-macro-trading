import os
import time
import json
import calendar
import requests
import pandas as pd
import pytz
import yfinance as yf
from datetime import datetime, timedelta, date

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EVENTO_GITHUB = os.environ.get("GITHUB_EVENT_NAME", "")
ARCHIVO_ESTADO = "estado_alertas.json"

TZ_NY = pytz.timezone("America/New_York")
TZ_BO = pytz.timezone("America/La_Paz")

BANDERAS = {"US": "🇺🇸", "CA": "🇨🇦", "CN": "🇨🇳", "EU": "🇪🇺", "JP": "🇯🇵", "GB": "🇬🇧"}

RUIDO = [
    "3-month", "6-month", "4-week", "8-week", "52-week", "bill auction",
    "bond auction", "tips auction", "note auction", "usda", "pork",
    "nopa", "soybean", "soja", "wheat", "trigo", "corn", "maíz",
    "cattle", "ganado", "cotton", "algodón", "crude", "petróleo",
    "oil", "gasoline", "gasolina", "natural gas", "gas natural",
    "baker hughes", "rig count", "distillate", "cushing", "eia", "api weekly"
]


def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID:
        print("ERROR: Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en GitHub Secrets.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
        if r.status_code != 200:
            print(f"Aviso Markdown ({r.status_code}): {r.text} -> Reintentando sin formato...")
            texto_limpio = mensaje.replace("*", "").replace("`", "")
            r2 = requests.post(url, data={"chat_id": CHAT_ID, "text": texto_limpio}, timeout=10)
            if r2.status_code != 200:
                print(f"Error Telegram definitivo ({r2.status_code}): {r2.text}")
    except Exception as e:
        print(f"Excepción enviando Telegram: {e}")


def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_estado(estado):
    hoy_str = datetime.now(pytz.utc).strftime("%Y-%m-%d")
    ayer_str = (datetime.now(pytz.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    limpio = {k: v for k, v in estado.items() if k.startswith(hoy_str) or k.startswith(ayer_str)}
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(limpio, f, indent=2)


def es_relevante(fila):
    pais = fila.get("country", "")
    imp = fila.get("importance", -1)
    titulo = str(fila.get("title", "")).lower()

    if imp not in [1, 0]:
        return False
    if any(p in titulo for p in RUIDO):
        return False
    if pais == "US":
        return True
    if pais in ["CA", "CN", "EU", "JP", "GB"]:
        return imp == 1
    return False


def obtener_activos(fila):
    pais = fila.get("country", "")
    if pais == "US":
        return True, True, "🇺🇸 NAS100 | 🥇 XAUUSD"
    return False, True, "🥇 XAUUSD"


def obtener_datos():
    ahora_utc = datetime.now(pytz.utc)
    anio, mes = ahora_utc.year, ahora_utc.month
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
    inicio_utc = (datetime.combine(date(anio, mes, 1), datetime.min.time()) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
    fin_utc = (datetime.combine(ultimo_dia, datetime.max.time()) + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59.000Z")

    headers_tv = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0"
    }
    eventos = []

    try:
        res = requests.get(
            "https://economic-calendar.tradingview.com/events",
            params={"from": inicio_utc, "to": fin_utc, "countries": "US,CA,CN,EU,JP,GB"},
            headers=headers_tv,
            timeout=12
        )
        if res.status_code == 200:
            for ev in res.json().get("result", []):
                titulo = str(ev.get("title", "")).strip()
                es_disc = any(k in titulo.lower() for k in [
                    "speaks", "speech", "testifies", "statement",
                    "press conference", "minutes", "fed chair", "fomc"
                ])
                eventos.append({
                    "title": titulo,
                    "date": pd.to_datetime(ev.get("date"), utc=True),
                    "importance": ev.get("importance", -1),
                    "country": ev.get("country", ""),
                    "previous": ev.get("previous"),
                    "forecast": ev.get("forecast"),
                    "actual": ev.get("actual"),
                    "es_discurso": es_disc
                })
    except Exception as e:
        print(f"Error TradingView: {e}")

    try:
        res_ff = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12
        )
        if res_ff.status_code == 200:
            mapa_imp = {"High": 1, "Medium": 0, "Low": -1}
            mapa_pais = {"USD": "US", "CAD": "CA", "CNY": "CN", "EUR": "EU", "JPY": "JP", "GBP": "GB"}
            for ev in res_ff.json():
                divisa = ev.get("country", "")
                if divisa in mapa_pais:
                    titulo = str(ev.get("title", "")).strip()
                    es_disc = any(k in titulo.lower() for k in [
                        "speaks", "speech", "testifies", "statement",
                        "press conference", "minutes", "fed chair", "fomc", "member"
                    ])
                    prev_v = str(ev.get("previous", "")).strip()
                    fore_v = str(ev.get("forecast", "")).strip()
                    if es_disc or (prev_v == "" and fore_v == ""):
                        eventos.append({
                            "title": f"🎙️ {titulo}" if es_disc else titulo,
                            "date": pd.to_datetime(ev.get("date"), utc=True),
                            "importance": mapa_imp.get(ev.get("impact"), -1),
                            "country": mapa_pais[divisa],
                            "previous": prev_v if prev_v else None,
                            "forecast": fore_v if fore_v else None,
                            "actual": None,
                            "es_discurso": es_disc
                        })
    except Exception as e:
        print(f"Error ForexFactory: {e}")

    if not eventos:
        return pd.DataFrame()

    df = pd.DataFrame(eventos)
    df["title_key"] = df["title"].str.lower().str.replace("🎙️ ", "", regex=False).str[:20]
    df = df.drop_duplicates(subset=["date", "title_key"]).copy()
    return df


def calcular_sesgo(fila, ignorar_actual=False):
    actual = None if ignorar_actual else fila.get("actual")
    pron, ant = fila.get("forecast"), fila.get("previous")
    es_ext = fila.get("country", "US") in ["CA", "CN", "EU", "JP", "GB"]

    if fila.get("es_discurso") and pd.isna(actual):
        return "🎙️ Discurso (Revisar tono Hawkish/Dovish)"

    tiene_act = pd.notna(actual) and str(actual).strip() != ""
    tiene_pron = pd.notna(pron) and str(pron).strip() != ""
    tiene_ant = pd.notna(ant) and str(ant).strip() != ""

    dir_esp = None
    if tiene_pron and tiene_ant:
        try:
            p, a = float(pron), float(ant)
            if p > a:
                dir_esp = 1 if es_ext else -1
            elif p < a:
                dir_esp = -1 if es_ext else 1
            else:
                dir_esp = 0
        except Exception:
            pass

    if not tiene_act:
        if dir_esp == 1:
            return "⏳ Pendiente (Se espera Subida 📈)"
        if dir_esp == -1:
            return "⏳ Pendiente (Se espera Caída 📉)"
        if dir_esp == 0:
            return "⏳ Pendiente (Se espera Neutral ➖)"
        return "⏳ Pendiente (Sin pronóstico)"

    ref = pron if tiene_pron else ant
    if pd.isna(ref) or str(ref).strip() == "":
        return "ℹ️ Publicado"

    try:
        act_f, ref_f = float(actual), float(ref)
        if act_f > ref_f:
            dir_real, base = (1, "🟢 ALCISTA") if es_ext else (-1, "🔴 BAJISTA")
        elif act_f < ref_f:
            dir_real, base = (-1, "🔴 BAJISTA") if es_ext else (1, "🟢 ALCISTA")
        else:
            dir_real, base = 0, "⚪ NEUTRAL"

        if tiene_pron and dir_esp is not None:
            est = "🎯 Exacto" if act_f == float(pron) else ("✅ Cumplido" if dir_real == dir_esp else "❌ Al contrario")
            return f"{base} | {est}"
        return f"{base} (Vs. Anterior)"
    except Exception:
        return "ℹ️ Publicado"


def formatear_analisis_vela(nombre, o, h, l, c, es_oro=False):
    puntos = c - o
    rango_total = h - l
    pct = (puntos / o) * 100 if o else 0
    mecha_sup = h - max(o, c)
    mecha_inf = min(o, c) - l

    if puntos > 0:
        direccion = f"🟢 *SUBIÓ +{puntos:.2f} pts*"
    elif puntos < 0:
        direccion = f"🔴 *BAJÓ {puntos:.2f} pts*"
    else:
        direccion = "⚪ *CERRÓ PLANA (0.00 pts)*"

    extra_pips = f" ({puntos * 10:+.0f} pips)" if es_oro else ""

    cuerpo = abs(puntos)
    nota_mecha = ""
    if mecha_sup > cuerpo * 1.8 and mecha_sup > mecha_inf:
        nota_mecha = " | ⚠️ Rechazo arriba (mecha sup.)"
    elif mecha_inf > cuerpo * 1.8 and mecha_inf > mecha_sup:
        nota_mecha = " | ⚠️ Rechazo abajo (mecha inf.)"

    return (
        f"• *{nombre}:* {direccion}{extra_pips} (`{pct:+.2f}%`)\n"
        f"  📏 Rango M5: `{rango_total:.2f} pts`{nota_mecha}\n"
        f"  `O:{o:.2f} | H:{h:.2f} | L:{l:.2f} | C:{c:.2f}`"
    )


def leer_vela_exacta_m5(fecha_ev, es_oro=True, permitir_ultima_si_futura=False):
    vela_inicio_utc = fecha_ev.floor("5min")
    hora_vela_bo = vela_inicio_utc.astimezone(TZ_BO).strftime("%H:%M")

    simbolo = "GC=F" if es_oro else "NQ=F"
    nombre = f"XAUUSD Futuro (Vela {hora_vela_bo} BO)" if es_oro else f"NAS100 Futuro (Vela {hora_vela_bo} BO)"
    try:
        df = yf.download(simbolo, period="1d", interval="5m", progress=False)
        if df.empty:
            return f"• *{nombre}:* Sin datos M5 disponibles"

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        vela = None
        if vela_inicio_utc in df.index:
            vela = df.loc[vela_inicio_utc]
        elif permitir_ultima_si_futura:
            vela = df.iloc[-1]
            hora_ult_bo = df.index[-1].astimezone(TZ_BO).strftime("%H:%M")
            nombre = f"XAUUSD Futuro (Última vela {hora_ult_bo} BO)" if es_oro else f"NAS100 Futuro (Última vela {hora_ult_bo} BO)"

        if vela is not None:
            if isinstance(vela, pd.DataFrame):
                vela = vela.iloc[0]
            o = float(vela["Open"].iloc[0]) if hasattr(vela["Open"], "iloc") else float(vela["Open"])
            h = float(vela["High"].iloc[0]) if hasattr(vela["High"], "iloc") else float(vela["High"])
            l = float(vela["Low"].iloc[0]) if hasattr(vela["Low"], "iloc") else float(vela["Low"])
            c = float(vela["Close"].iloc[0]) if hasattr(vela["Close"], "iloc") else float(vela["Close"])
            return formatear_analisis_vela(nombre, o, h, l, c, es_oro=es_oro)

        return f"• *{nombre}:* ⏳ Vela aún pendiente por retraso de Yahoo Finance"
    except Exception as e:
        return f"• *{nombre}:* Error leyendo vela M5 ({e})"


def fmt(v):
    return str(v) if pd.notna(v) and str(v).strip() != "" else "-"


def construir_alerta_1(r):
    imp_txt = "🔴 ALTO IMPACTO" if r["importance"] == 1 else "🟠 MEDIO IMPACTO"
    band = BANDERAS.get(r["country"], "🌐")
    _, _, activos_txt = obtener_activos(r)
    h_ny = r["date"].astimezone(TZ_NY).strftime("%H:%M")
    h_bo = r["date"].astimezone(TZ_BO).strftime("%H:%M")
    sesgo_previo = calcular_sesgo(r, ignorar_actual=True)
    return (
        f"🚨 *ALERTA 1/3 — NOTICIA PRÓXIMA* 🚨\n\n"
        f"*{imp_txt}*\n"
        f"🎯 *Activos:* {activos_txt}\n"
        f"📌 {band} {r['title']}\n"
        f"🕒 *NY:* {h_ny} | *BO:* {h_bo}\n"
        f"📊 Ant: `{fmt(r['previous'])}` | Pron: `{fmt(r['forecast'])}` | Real: `-`\n"
        f"🧭 *Proyección:* {sesgo_previo}"
    )


def construir_alerta_2(r):
    band = BANDERAS.get(r["country"], "🌐")
    _, _, activos_txt = obtener_activos(r)
    sesgo_real = calcular_sesgo(r, ignorar_actual=False)
    return (
        f"⚡ *ALERTA 2/3 — DATO CONFIRMADO* ⚡\n\n"
        f"🎯 *Activos:* {activos_txt}\n"
        f"📌 {band} {r['title']}\n"
        f"📊 Ant: `{fmt(r['previous'])}` | Pron: `{fmt(r['forecast'])}` | *Real:* `{fmt(r['actual'])}`\n"
        f"🧭 *Resultado:* {sesgo_real}"
    )


def construir_alerta_3(r, permitir_ultima_si_futura=False):
    band = BANDERAS.get(r["country"], "🌐")
    es_nas, es_xau, activos_txt = obtener_activos(r)
    sesgo_real = calcular_sesgo(r, ignorar_actual=False)
    velas = []
    if es_xau:
        velas.append(leer_vela_exacta_m5(r["date"], es_oro=True, permitir_ultima_si_futura=permitir_ultima_si_futura))
    if es_nas:
        velas.append(leer_vela_exacta_m5(r["date"], es_oro=False, permitir_ultima_si_futura=permitir_ultima_si_futura))
    return (
        f"🕯️ *ALERTA 3/3 — CIERRE VELA M5 (+5 MIN)* 🕯️\n\n"
        f"🎯 *Activos:* {activos_txt}\n"
        f"📌 {band} {r['title']}\n"
        f"📊 Ant: `{fmt(r['previous'])}` | Pron: `{fmt(r['forecast'])}` | *Real:* `{fmt(r['actual'])}`\n"
        f"🧭 *Dato:* {sesgo_real}\n\n"
        f"📉 *Movimiento de la Vela M5:*\n"
        + "\n".join(velas)
    )


def ejecutar_prueba_manual(df):
    hoy_bo = datetime.now(TZ_BO).date()
    df_hoy = df[df["date"].dt.tz_convert(TZ_BO).dt.date == hoy_bo].sort_values(by="date")
    df_hoy = df_hoy[df_hoy.apply(es_relevante, axis=1)]

    if df_hoy.empty:
        enviar_telegram("📋 *PRUEBA OK:* No hay noticias de Medio/Alto impacto relevantes hoy.")
        return

    lineas = [f"📋 *NOTICIAS DE HOY ({hoy_bo.strftime('%d/%m/%Y')})* — Medio y Alto Impacto\n"]
    for _, r in df_hoy.iterrows():
        ico = "🔴" if r["importance"] == 1 else "🟠"
        band = BANDERAS.get(r["country"], "🌐")
        _, _, activos_txt = obtener_activos(r)
        h_ny = r["date"].astimezone(TZ_NY).strftime("%H:%M")
        h_bo = r["date"].astimezone(TZ_BO).strftime("%H:%M")
        sesgo = calcular_sesgo(r)
        lineas.append(
            f"{ico} `{h_ny} NY | {h_bo} BO` — {band} *{r['title']}*\n"
            f"   🎯 *Activos:* {activos_txt}\n"
            f"   📊 Ant: `{fmt(r['previous'])}` | Pron: `{fmt(r['forecast'])}` | Real: `{fmt(r['actual'])}`\n"
            f"   🧭 {sesgo}\n"
        )
    enviar_telegram("\n".join(lineas))
    time.sleep(1)

    con_real = df_hoy[df_hoy["actual"].notna() & (df_hoy["actual"].astype(str).str.strip() != "")]
    ejemplo = con_real.iloc[-1] if not con_real.empty else df_hoy.iloc[0]

    enviar_telegram(construir_alerta_1(ejemplo))
    time.sleep(1)
    enviar_telegram(construir_alerta_2(ejemplo))
    time.sleep(1)
    enviar_telegram(construir_alerta_3(ejemplo, permitir_ultima_si_futura=True))


def ejecutar():
    df = obtener_datos()
    if df.empty:
        print("No se obtuvieron eventos.")
        return

    if EVENTO_GITHUB == "workflow_dispatch":
        ejecutar_prueba_manual(df)

    estado = cargar_estado()
    ahora_utc = datetime.now(pytz.utc)

    for _, r in df.iterrows():
        if not es_relevante(r):
            continue

        fecha_ev = r["date"]
        diff_min = (fecha_ev - ahora_utc).total_seconds() / 60.0
        ev_id = f"{fecha_ev.strftime('%Y-%m-%d_%H:%M')}_{r['title_key']}"
        fases = estado.get(ev_id, [])

        if "1" not in fases and (0.5 <= diff_min <= 12):
            enviar_telegram(construir_alerta_1(r))
            fases.append("1")

        tiene_real = pd.notna(r["actual"]) and str(r["actual"]).strip() != ""
        if "2" not in fases and (-15 <= diff_min <= 0) and (tiene_real or r["es_discurso"]):
            enviar_telegram(construir_alerta_2(r))
            fases.append("2")

        if "3" not in fases and (-25 <= diff_min <= -5.5):
            enviar_telegram(construir_alerta_3(r, permitir_ultima_si_futura=False))
            fases.append("3")

        if fases:
            estado[ev_id] = fases

    guardar_estado(estado)


if __name__ == "__main__":
    ejecutar()
