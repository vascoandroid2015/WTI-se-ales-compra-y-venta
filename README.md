# Bot Señales WTI

Bot en Python para generar señales de entrada y salida sobre petróleo WTI y enviarlas a Telegram, listo para subir a GitHub y ejecutar con GitHub Actions.

## Qué hace

- Descarga datos de WTI usando `yfinance` con el ticker `CL=F`
- Calcula EMA rápida, EMA lenta, EMA de tendencia, RSI y ATR
- Indica si la señal es LONG o SHORT
- Muestra precio de entrada/compra y precio de salida/venta
- Analiza la tendencia de los últimos 15 días
- Estima hacia dónde se espera que llegue el precio con un objetivo técnico
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
- `TREND_DAYS` → `15`
- `TARGET_ATR_MULT` → `2.5`
- `ALERT_MODE` → `changes` o `all`
