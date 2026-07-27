# Robô de Análise Avançada de Meningites — v1.0

Pipeline modular para vigilância epidemiológica, análise estatística, séries temporais, risco, qualidade da informação, record linkage, geoespacial e dashboard.

## Base inicial testada
Arquivo de referência: `meningite.csv`  
Estrutura detectada: 5.912 registros, 116 variáveis, período de notificação de 2007-01-01 a 2026-04-03.

## Instalação sugerida

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Dependências opcionais: `prophet`, `xgboost`, `tensorflow`, `pymc3`, `geopandas`, `libpysal`, `esda`, `lifelines`, `recordlinkage`.

## Execução básica

Coloque `meningite.csv` em `data/raw/` e rode:

```bash
python run_pipeline.py --input data/raw/meningite.csv --outdir outputs
```

Com população municipal:

```bash
python run_pipeline.py --input data/raw/meningite.csv --population data/external/populacao_municipal.csv --outdir outputs
```

Com shapefile:

```bash
python run_pipeline.py --input data/raw/meningite.csv --shapefile data/external/MT_Municipios.shp --outdir outputs
```

## Dashboard Streamlit

```bash
streamlit run dashboard_streamlit.py
```

## Saídas principais

- `outputs/quality_report.csv`
- `outputs/logical_consistency.csv`
- `outputs/indicators.csv`
- `outputs/statistical_tests.csv`
- `outputs/logistic_or_death.csv`
- `outputs/logistic_or_hospitalization.csv`
- `outputs/timeseries_forecasts.csv`
- `outputs/endemic_channel.csv`
- `outputs/spatial_indicators.gpkg` quando shapefile estiver disponível
- `outputs/summary_executive.md`

## Observação técnica
O pipeline é desenhado para funcionar mesmo sem todas as dependências opcionais. Quando bibliotecas como Prophet, XGBoost, TensorFlow, GeoPandas, PyMC3 ou PySAL não estiverem instaladas, os módulos correspondentes serão ignorados com registro no relatório.


## Correção para erro "can't open file"

Esse erro ocorre quando `robo_meningites_pipeline_v1.py` não está na pasta em que o comando foi executado.

A estrutura mínima deve ficar assim:

```text
C:\Users\Menandesneto\OneDrive\CIEVS MT\Meningites\
│
├── robo_meningites_pipeline_v1.py
├── run_pipeline.py
├── dashboard_streamlit.py
├── requirements.txt
├── config.yml
├── meningite.csv
└── src\
    └── meningite_robot\
        ├── __init__.py
        ├── io.py
        ├── cleaning.py
        ├── quality.py
        ├── indicators.py
        ├── analytics.py
        ├── timeseries.py
        ├── survival.py
        ├── linkage.py
        ├── spatial.py
        ├── environmental.py
        ├── bayesian.py
        └── reporting.py
```

Também é possível deixar o CSV dentro de `data\raw\meningite.csv`.

## Comando compatível

```bash
python robo_meningites_pipeline_v1.py --input meningite.csv --outdir saida_meningites --make-dashboard
```

## Execução por duplo clique

Use:

```text
rodar_pipeline_meningites.bat
```

Para abrir o painel:

```text
abrir_dashboard_meningites.bat
```
