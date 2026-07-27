# Nowcast operacional + gestão — Meningites V24

**Gerado:** 27/07/2026 14:21

## Método

- Evento de início: sintomas (fallback `data_ref`).
- Evento de reporte: **notificação** (DT_DIGITA ainda não disponível no VW).
- Nowcast: `observado / P(atraso_SE ≤ lag)` com banda bootstrap P10–P90.
- Estratos: ESTADUAL, DM, regionais com série suficiente.

## Semana CIEVS (gestão)

- SE ref: **28**
- Nowcast estadual: **1.0777777777777777** (obs 1.0; Δ -2.0773946360153257)
- Nowcast DM: **0.0** (obs 0.0)
- Status sazonal: **rotina** — Nowcast SE28=1.1 ≤ P75 histórico 8.0
- Fila CIEVS: 257 (críticos 220)
- Atraso notif P50/P90 (dias): 3.0 / 13.0
- Ação sugerida: Manter rotina: acompanhar fila CIEVS e indicadores MS em vermelho.

## Resumo por estrato

```
                        estrato  observado_se_atual  nowcast_se_atual  forecast_se1  backtest_mape_pct qualidade_forecast alerta_nowcast
                       ESTADUAL                 1.0          1.077778      3.050631         120.850347     nao_publicavel         rotina
                             DM                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
             REGIONAL::AGUA BOA                 0.0          0.000000      0.250000                NaN     nao_publicavel         rotina
        REGIONAL::ALTA FLORESTA                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
      REGIONAL::BARRA DO GARCAS                 3.0          3.060484      0.126890          81.076389            cautela         rotina
              REGIONAL::CACERES                 1.0          1.135647      0.171100          45.902778         publicavel         rotina
              REGIONAL::COLIDER                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
               REGIONAL::CUIABA                 1.0          1.047685      1.157740         115.885417     nao_publicavel         rotina
           REGIONAL::DIAMANTINO                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
                REGIONAL::JUARA                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
                REGIONAL::JUINA                 2.0          2.186047      0.068314          95.312500            cautela         rotina
   REGIONAL::PEIXOTO DE AZEVEDO                 0.0          0.000000      0.250000                NaN     nao_publicavel         rotina
     REGIONAL::PONTES E LACERDA                 1.0          1.058824      0.064338          39.479167         publicavel         rotina
REGIONAL::PORTO ALEGRE DO NORTE                 0.0          0.000000      0.000000                NaN     nao_publicavel         rotina
         REGIONAL::RONDONOPOLIS                 0.0          0.000000      0.062500          44.895833         publicavel         rotina
                REGIONAL::SINOP                 1.0          1.028571      0.375893          32.118056         publicavel         rotina
     REGIONAL::TANGARA DA SERRA                 0.0          0.000000      0.531250          46.875000         publicavel         rotina
```