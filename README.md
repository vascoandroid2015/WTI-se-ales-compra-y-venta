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

## Variables de entorno / Secrets

Añade estos secrets en GitHub:

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

Opcionales:

- `WTI_SYMBOL` → por defecto `CL=F`
- `WTI_INTERVAL` → por defecto `1h`
- `WTI_PERIOD` → por defecto `60d`
- `FAST_EMA` → por defecto `21`
- `SLOW_EMA` → por defecto `50`
- `TREND_EMA` → por defecto `200`
- `RSI_PERIOD` → por defecto `14`
- `ATR_PERIOD` → por defecto `14`
- `ATR_STOP_MULT` → por defecto `1.5`
- `RR_MULT` → por defecto `2.0`
- `ALERT_MODE` → `changes` o `all`, por defecto `changes`

## Cómo funciona la señal

### Entrada long

- EMA rápida cruza por encima de EMA lenta
- Precio y EMA rápida por encima de EMA de tendencia
- RSI mayor o igual a 52

### Entrada short

- EMA rápida cruza por debajo de EMA lenta
- Precio y EMA rápida por debajo de EMA de tendencia
- RSI menor o igual a 48

### Salida

- Para long: pérdida de EMA rápida y RSI por debajo de 50
- Para short: recuperación sobre EMA rápida y RSI por encima de 50

## Subida a GitHub

1. Crea un repositorio nuevo
2. Sube estos archivos
3. Añade los secrets de Telegram
4. Activa GitHub Actions
5. Lanza manualmente el workflow para probar

## Programación

El workflow está configurado para ejecutarse cada hora y también manualmente.

## Nota

Esto es un bot de señales, no de ejecución automática. Revísalo siempre antes de operar, especialmente si usas productos apalancados o inversos sobre WTI.
