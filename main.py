import os

import pandas as pd
import requests
import yfinance as yf


def getenv_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def getenv_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def getenv_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


TOKEN = getenv_str("TELEGRAM_TOKEN", "")
CHAT_ID = getenv_str("TELEGRAM_CHAT_ID", "")

SYMBOL = getenv_str("WTI_SYMBOL", "CL=F")
INTERVAL = getenv_str("WTI_INTERVAL", "1h")
PERIOD = getenv_str("WTI_PERIOD", "60d")
FAST_EMA = getenv_int("FAST_EMA", 21)
SLOW_EMA = getenv_int("SLOW_EMA", 50)
TREND_EMA = getenv_int("TREND_EMA", 200)
RSI_PERIOD = getenv_int("RSI_PERIOD", 14)
ATR_PERIOD = getenv_int("ATR_PERIOD", 14)
ATR_STOP_MULT = getenv_float("ATR_STOP_MULT", 1.5)
RR_MULT = getenv_float("RR_MULT", 2.0)
ALERT_MODE = getenv_str("ALERT_MODE", "changes")
TREND_DAYS = getenv_int("TREND_DAYS", 15)
TARGET_ATR_MULT = getenv_float("TARGET_ATR_MULT", 2.5)


def send_telegram(message: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no configurados. Mensaje por consola:\n")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(f"Telegram error {response.status_code}: {response.text[:300]}")


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            (df["High"] - df["Low"]).abs(),
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def load_data() -> pd.DataFrame:
    df = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL, auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise RuntimeError("No se pudieron descargar datos de WTI")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    needed = ["Open", "High", "Low", "Close"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise RuntimeError(f"Faltan columnas en datos: {missing}")

    df = df.dropna(subset=needed).copy()
    df["ema_fast"] = df["Close"].ewm(span=FAST_EMA, adjust=False).mean()
    df["ema_slow"] = df["Close"].ewm(span=SLOW_EMA, adjust=False).mean()
    df["ema_trend"] = df["Close"].ewm(span=TREND_EMA, adjust=False).mean()
    df["rsi"] = compute_rsi(df["Close"], RSI_PERIOD)
    df["atr"] = compute_atr(df, ATR_PERIOD)
    df = df.dropna().copy()

    if len(df) < 3:
        raise RuntimeError("No hay suficientes velas para generar señal")

    return df


def analyze_recent_trend(df: pd.DataFrame) -> dict:
    bars = min(len(df), TREND_DAYS * 24 if INTERVAL == "1h" else TREND_DAYS)
    recent = df.tail(bars).copy()

    first_close = float(recent["Close"].iloc[0])
    last_close = float(recent["Close"].iloc[-1])
    change_pct = ((last_close / first_close) - 1) * 100 if first_close else 0.0
    recent_high = float(recent["High"].max())
    recent_low = float(recent["Low"].min())
    last_atr = float(df["atr"].iloc[-1])
    last_rsi = float(df["rsi"].iloc[-1])
    last_ema_fast = float(df["ema_fast"].iloc[-1])
    last_ema_slow = float(df["ema_slow"].iloc[-1])
    last_ema_trend = float(df["ema_trend"].iloc[-1])

    if last_close > last_ema_trend and last_ema_fast > last_ema_slow and change_pct > 1.0:
        trend = "ALCISTA"
        expected_target = max(recent_high, last_close + TARGET_ATR_MULT * last_atr)
    elif last_close < last_ema_trend and last_ema_fast < last_ema_slow and change_pct < -1.0:
        trend = "BAJISTA"
        expected_target = min(recent_low, last_close - TARGET_ATR_MULT * last_atr)
    else:
        trend = "LATERAL"
        expected_target = recent_high if last_rsi >= 50 else recent_low

    return {
        "trend": trend,
        "days": TREND_DAYS,
        "change_pct": round(change_pct, 2),
        "recent_high": round(recent_high, 2),
        "recent_low": round(recent_low, 2),
        "expected_target": round(expected_target, 2),
    }


def generate_signal(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    trend_info = analyze_recent_trend(df)

    cross_up = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]
    cross_down = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]
    trend_up = last["Close"] > last["ema_trend"] and last["ema_fast"] > last["ema_trend"]
    trend_down = last["Close"] < last["ema_trend"] and last["ema_fast"] < last["ema_trend"]
    rsi_bull = float(last["rsi"]) >= 52
    rsi_bear = float(last["rsi"]) <= 48

    action = "SIN_SEÑAL"
    direction = "NEUTRAL"
    reason = "Mercado sin confirmación clara"
    entry_price = float(last["Close"])
    atr = float(last["atr"])
    stop_loss = None
    take_profit = None
    exit_price = None

    if cross_up and trend_up and rsi_bull:
        action = "ENTRADA"
        direction = "LONG"
        reason = "Cruce alcista EMA rápida/lenta con tendencia y RSI a favor"
        stop_loss = entry_price - ATR_STOP_MULT * atr
        take_profit = max(entry_price + RR_MULT * (entry_price - stop_loss), trend_info["expected_target"])
        exit_price = take_profit
    elif cross_down and trend_down and rsi_bear:
        action = "ENTRADA"
        direction = "SHORT"
        reason = "Cruce bajista EMA rápida/lenta con tendencia y RSI a favor"
        stop_loss = entry_price + ATR_STOP_MULT * atr
        take_profit = min(entry_price - RR_MULT * (stop_loss - entry_price), trend_info["expected_target"])
        exit_price = take_profit
    elif float(last["Close"]) < float(last["ema_fast"]) and float(last["rsi"]) < 50 and trend_up:
        action = "SALIDA"
        direction = "LONG"
        reason = "Pérdida de EMA rápida y debilitamiento de momentum alcista"
        exit_price = entry_price
    elif float(last["Close"]) > float(last["ema_fast"]) and float(last["rsi"]) > 50 and trend_down:
        action = "SALIDA"
        direction = "SHORT"
        reason = "Recuperación sobre EMA rápida y debilitamiento bajista"
        exit_price = entry_price

    signal_time = pd.Timestamp(last.name)
    if signal_time.tzinfo is None:
        signal_time = signal_time.tz_localize("UTC")
    signal_time = signal_time.tz_convert("Europe/Madrid")

    return {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "action": action,
        "direction": direction,
        "reason": reason,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2) if exit_price is not None else None,
        "ema_fast": round(float(last["ema_fast"]), 2),
        "ema_slow": round(float(last["ema_slow"]), 2),
        "ema_trend": round(float(last["ema_trend"]), 2),
        "rsi": round(float(last["rsi"]), 2),
        "atr": round(atr, 2),
        "stop_loss": round(stop_loss, 2) if stop_loss is not None else None,
        "take_profit": round(take_profit, 2) if take_profit is not None else None,
        "time": signal_time.strftime("%d/%m/%Y %H:%M"),
        "trend_info": trend_info,
    }


def format_message(signal: dict) -> str:
    trend = signal["trend_info"]
    lines = [
        "<b>🛢️ Bot Señales WTI</b>",
        "",
        f"⏱️ Marco: {signal['interval']}",
        f"📍 Tipo: <b>{signal['action']}</b>",
        f"🔄 Dirección: <b>{signal['direction']}</b>",
        f"💵 Precio actual WTI: {signal['entry_price']}$",
        f"📅 Vela: {signal['time']}",
        "",
        f"📆 Tendencia últimos {trend['days']} días: <b>{trend['trend']}</b>",
        f"📊 Cambio {trend['days']} días: {trend['change_pct']}%",
        f"⬆️ Máximo reciente: {trend['recent_high']}$",
        f"⬇️ Mínimo reciente: {trend['recent_low']}$",
        f"🎯 Precio esperado/objetivo: {trend['expected_target']}$",
        "",
        f"⚡ EMA rápida: {signal['ema_fast']}",
        f"📊 EMA lenta: {signal['ema_slow']}",
        f"🧭 EMA tendencia: {signal['ema_trend']}",
        f"📈 RSI: {signal['rsi']}",
        f"📏 ATR: {signal['atr']}",
    ]

    if signal["action"] == "ENTRADA":
        lines.append(f"🟢 Precio de compra/entrada: {signal['entry_price']}$")
    if signal["action"] == "SALIDA" and signal["exit_price"] is not None:
        lines.append(f"🔴 Precio de venta/salida: {signal['exit_price']}$")
    if signal["take_profit"] is not None:
        lines.append(f"🎯 Precio objetivo de venta/salida: {signal['take_profit']}$")
    if signal["stop_loss"] is not None:
        lines.append(f"🛑 Stop loss: {signal['stop_loss']}$")

    lines.extend([
        "",
        f"📝 Motivo: {signal['reason']}",
    ])
    return "\n".join(lines)


def should_send(signal: dict) -> bool:
    if ALERT_MODE == "all":
        return True
    return signal["action"] != "SIN_SEÑAL"


def main() -> None:
    df = load_data()
    signal = generate_signal(df)
    message = format_message(signal)
    print(message)
    if should_send(signal):
        send_telegram(message)
    else:
        print("Sin envío a Telegram porque ALERT_MODE=changes y no hay señal operativa.")


if __name__ == "__main__":
    main()
