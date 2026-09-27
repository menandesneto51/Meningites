# Nowcast operacional + gestão — Meningites V24

**Gerado:** 27/09/2026 10:11

## Método

- Evento de início: sintomas (fallback `data_ref`).
- Evento de reporte: **notificação** (DT_DIGITA ainda não disponível no VW).
- Nowcast: `observado / P(atraso_SE ≤ lag)` com banda bootstrap P10–P90.
- Estratos: ESTADUAL, DM, regionais com série suficiente.

## Semana CIEVS (gestão)

- SE ref: **35**
- Nowcast estadual: **2.0767894371091034** (obs 2.0; Δ -3.0616218421206076)
- Nowcast DM: **0.0** (obs 0.0)
- Status sazonal: **rotina** — Nowcast SE35=2.1 ≤ P75 histórico 6.0
- Fila CIEVS: 280 (críticos 220)
- Atraso notif P50/P90 (dias): 3.0 / 13.0
- Ação sugerida: Manter rotina: acompanhar fila CIEVS e indicadores MS em vermelho.

## Resumo por estrato

```
                        estrato  observado_se_atual  nowcast_se_atual  forecast_se1  backtest_mape_pct qualidade_forecast alerta_nowcast
                       ESTADUAL                 2.0          2.076789      1.975475          83.560764            cautela         rotina
                             DM                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
             REGIONAL::AGUA BOA                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
        REGIONAL::ALTA FLORESTA                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
      REGIONAL::BARRA DO GARCAS                 0.0          0.000000      0.250000                NaN     nao_publicavel         rotina
              REGIONAL::CACERES                 1.0          1.068047      0.033376          96.875000            cautela         rotina
              REGIONAL::COLIDER                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
               REGIONAL::CUIABA                 1.0          1.034653      0.626083          72.638889            cautela         rotina
           REGIONAL::DIAMANTINO                 0.0          0.000000      0.031250         100.000000            cautela         rotina
                REGIONAL::JUARA                 0.0          0.000000      0.250000                NaN     nao_publicavel         rotina
                REGIONAL::JUINA                 0.0          0.000000      0.031250          84.375000            cautela         rotina
   REGIONAL::PEIXOTO DE AZEVEDO                 0.0          0.000000      0.062500          74.479167            cautela         rotina
     REGIONAL::PONTES E LACERDA                 1.0          1.044025      0.095126          64.722222            cautela         rotina
REGIONAL::PORTO ALEGRE DO NORTE                 0.0          0.000000      0.031250          96.875000            cautela         rotina
         REGIONAL::RONDONOPOLIS                 2.0          2.029579      0.188424          38.368056         publicavel         rotina
                REGIONAL::SINOP                 1.0          1.024213      0.376436          62.239583            cautela         rotina
     REGIONAL::TANGARA DA SERRA                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
```