# Bot Señales WTI

Bot en Python para generar señales de entrada y salida sobre petróleo WTI y enviarlas a Telegram, listo para subir a GitHub y ejecutar con GitHub Actions.

## Qué hace

- Descarga datos de WTI usando `yfinance` con el ticker `CL=F`
- Calcula EMA rápida, EMA lenta, EMA de tendencia, RSI y ATR
- Indica si la señal es LONG o SHORT
- Muestra precio de entrada/compra y precio de salida/venta
- Calcula stop loss y precio objetivo
- Tolera variables vacías en GitHub Actions y usa valores por defecto

## Secrets necesarios

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

## Variables opcionales

- `WTI_SYMBOL` → `CL=F`
- `WTI_INTERVAL` → `1h`
- `WTI_PERIOD` → `60d`
- `FAST_EMA` → `21`
- `SLOW_EMA` → `50`
- `TREND_EMA` → `200`
- `RSI_PERIOD` → `14`
- `ATR_PERIOD` → `14`
- `ATR_STOP_MULT` → `1.5`
- `RR_MULT` → `2.0`
- `ALERT_MODE` → `changes` o `all`

## Señales

- `ENTRADA LONG`: precio de compra/entrada y objetivo de salida
- `ENTRADA SHORT`: precio de entrada short y objetivo de salida
- `SALIDA LONG`: precio de venta/salida
- `SALIDA SHORT`: precio de cierre/salida
- `SIN_SEÑAL`: sin operación
