# Nowcast / Forecast refinados — Meningites V23

**Gerado:** 27/09/2026 10:11

## Nowcast (correção por atraso de notificação)

- Observado SE atual: **2.0**
- Nowcast corrigido: **2.1** (+0.1 estimados em atraso)
- Status vs sazonalidade: **rotina** — Nowcast SE35=2.1 ≤ P75 histórico 6.0

## Forecast (próximas SE)

- SE+1: **5.3** · SE+4: **4.1**

## Backtest (8 SE)

- MAE: **2.22** casos/SE · MAPE: **54.1%**

Método: CDF empírica de `lt_sintomas_notificacao`; ensemble MA4/MA8/sazonal-52/tendência.
Complementa (não substitui) o forecasting diário V17 nem os indicadores oficiais do MS.