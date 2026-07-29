# Nowcast / Forecast refinados — Meningites V23

**Gerado:** 29/07/2026 12:37

## Nowcast (correção por atraso de notificação)

- Observado SE atual: **1.0**
- Nowcast corrigido: **1.1** (+0.1 estimados em atraso)
- Status vs sazonalidade: **rotina** — Nowcast SE28=1.1 ≤ P75 histórico 8.0

## Forecast (próximas SE)

- SE+1: **4.3** · SE+4: **4.6**

## Backtest (8 SE)

- MAE: **2.37** casos/SE · MAPE: **85.7%**

Método: CDF empírica de `lt_sintomas_notificacao`; ensemble MA4/MA8/sazonal-52/tendência.
Complementa (não substitui) o forecasting diário V17 nem os indicadores oficiais do MS.