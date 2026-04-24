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
    return df.dropna().copy()


def generate_signal(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2]

    cross_up = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]
    cross_down = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]
    trend_up = last["Close"] > last["ema_trend"] and last["ema_fast"] > last["ema_trend"]
    trend_down = last["Close"] < last["ema_trend"] and last["ema_fast"] < last["ema_trend"]
    rsi_bull = last["rsi"] >= 52
    rsi_bear = last["rsi"] <= 48

    action = "SIN_SEÑAL"
    reason = "Mercado sin confirmación clara"
    entry = float(last["Close"])
    atr = float(last["atr"])
    stop_loss = None
    take_profit = None

    if cross_up and trend_up and rsi_bull:
        action = "ENTRADA_LONG"
        reason = "Cruce alcista EMA rápida/lenta con tendencia y RSI a favor"
        stop_loss = entry - ATR_STOP_MULT * atr
        take_profit = entry + RR_MULT * (entry - stop_loss)
    elif cross_down and trend_down and rsi_bear:
        action = "ENTRADA_SHORT"
        reason = "Cruce bajista EMA rápida/lenta con tendencia y RSI a favor"
        stop_loss = entry + ATR_STOP_MULT * atr
        take_profit = entry - RR_MULT * (stop_loss - entry)
    elif last["Close"] < last["ema_fast"] and last["rsi"] < 50 and trend_up:
        action = "SALIDA_LONG"
        reason = "Pérdida de EMA rápida y debilitamiento de momentum"
    elif last["Close"] > last["ema_fast"] and last["rsi"] > 50 and trend_down:
        action = "SALIDA_SHORT"
        reason = "Recuperación sobre EMA rápida y debilitamiento bajista"

    signal_time = pd.Timestamp(last.name)
    if signal_time.tzinfo is None:
        signal_time = signal_time.tz_localize("UTC")
    signal_time = signal_time.tz_convert("Europe/Madrid")

    return {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "action": action,
        "reason": reason,
        "price": round(entry, 2),
        "ema_fast": round(float(last["ema_fast"]), 2),
        "ema_slow": round(float(last["ema_slow"]), 2),
        "ema_trend": round(float(last["ema_trend"]), 2),
        "rsi": round(float(last["rsi"]), 2),
        "atr": round(atr, 2),
        "stop_loss": round(stop_loss, 2) if stop_loss is not None else None,
        "take_profit": round(take_profit, 2) if take_profit is not None else None,
        "time": signal_time.strftime("%d/%m/%Y %H:%M"),
    }


def format_message(signal: dict) -> str:
    lines = [
        "🛢️ <b>Bot Señales WTI</b>",
        "",
        f"⏱️ Marco: {signal['interval']}",
        f"📍 Señal: <b>{signal['action']}</b>",
        f"💵 Precio WTI: {signal['price']}$",
        f"📅 Vela: {signal['time']}",
        "",
        f"⚡ EMA rápida: {signal['ema_fast']}",
        f"📊 EMA lenta: {signal['ema_slow']}",
        f"🧭 EMA tendencia: {signal['ema_trend']}",
        f"📈 RSI: {signal['rsi']}",
        f"📏 ATR: {signal['atr']}",
    ]

    if signal["stop_loss"] is not None:
        lines.append(f"🛑 Stop loss: {signal['stop_loss']}$")
    if signal["take_profit"] is not None:
        lines.append(f"🎯 Take profit: {signal['take_profit']}$")

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
