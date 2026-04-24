# Bot Señales WTI

Bot en Python para generar señales de entrada y salida sobre petróleo WTI y enviarlas a Telegram, listo para subir a GitHub y ejecutar con GitHub Actions.

## Qué hace

- Descarga datos de WTI usando `yfinance` con el ticker `CL=F`
- Calcula EMA rápida, EMA lenta, EMA de tendencia, RSI y ATR
- Genera señales:
  - `ENTRADA_LONG`
  - `ENTRADA_SHORT`
  - `SALIDA_LONG`
  - `SALIDA_SHORT`
  - `SIN_SEÑAL`
- Envía aviso a Telegram cuando hay cambio operativo
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

## Subida a GitHub

1. Crea un repositorio nuevo
2. Sube estos archivos
3. Añade los secrets de Telegram
4. Activa GitHub Actions
5. Lanza el workflow manualmente

## Nota

Si en GitHub tienes variables definidas pero vacías, este bot ya no se caerá: cogerá automáticamente los valores por defecto.
