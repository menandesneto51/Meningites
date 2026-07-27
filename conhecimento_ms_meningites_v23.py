# -*- coding: utf-8 -*-
"""
conhecimento_ms_meningites_v23.py
Base de conhecimento local (trechos normativos) para o assistente CIEVS.
Fontes públicas: Informe Meningites 2024, NT 97/2024-DPNI/SVSA/MS,
Caderno de Análises SINAN (Meningites), Guia de Vigilância em Saúde.
"""

from __future__ import annotations

DOCS = [
    {
        "id": "notif_24h",
        "titulo": "Notificação compulsória imediata",
        "tema": "notificacao",
        "tags": "notificacao compulsoria 24h imediata surto obito cluster sinan",
        "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS; Lista nacional de notificação compulsória",
        "texto": (
            "Meningite é doença de notificação compulsória em até 24 horas. "
            "Surtos, aglomerados de casos (clusters) e óbitos são de notificação imediata. "
            "Casos suspeitos ou confirmados devem ser notificados às autoridades competentes "
            "por profissionais da assistência e vigilância e por laboratórios públicos e privados. "
            "O registro deve ser feito no SINAN, com ficha de investigação de meningite e, "
            "quando aplicável, ficha de investigação de surtos. Meningite tuberculosa confirmada "
            "também deve preencher a ficha de tuberculose."
        ),
    },
    {
        "id": "caso_suspeita_nt97",
        "titulo": "Definição de caso suspeito (NT 97/2024)",
        "tema": "definicao_caso",
        "tags": "caso suspeito febre rigidez nuca cefaleia vomito petequia fontanela kernig brudzinski",
        "fonte": "NT nº 97/2024-DPNI/SVSA/MS",
        "texto": (
            "Caso suspeito de meningite: indivíduo com febre acompanhada de um ou mais dos seguintes: "
            "rigidez de nuca, confusão ou alteração mental, cefaleia intensa, vômitos, sinais de "
            "irritação meníngea (Kernig e Brudzinski), convulsão, sufusões hemorrágicas/petéquias e torpor. "
            "Em bebês, observar também irritabilidade, choro persistente, sonolência e abaulamento de fontanela."
        ),
    },
    {
        "id": "contato_proximo_nt97",
        "titulo": "Contato próximo (NT 97/2024)",
        "tema": "contatos",
        "tags": "contato proximo exposicao goticulas domicilio creche escola 4 horas 10 dias",
        "fonte": "NT nº 97/2024-DPNI/SVSA/MS",
        "texto": (
            "Contato próximo: indivíduo com contato direto e prolongado com caso suspeito ou confirmado "
            "de doença meningocócica (DM) ou doença invasiva por Hib, com exposição a gotículas de "
            "secreções respiratórias. Janela retrospectiva: do início dos sintomas até 10 dias anteriores. "
            "Janela prospectiva: do início dos sintomas até 24 horas após início de tratamento com "
            "cefalosporina de 3ª geração (ceftriaxona/cefotaxima) ou rifampicina. "
            "Situações típicas: mesmo domicílio/dormitório; beijo com troca salivar; exposição ≥4 horas "
            "e ≤1 metro em ambiente fechado; creche/ensino infantil (≥5 dias); procedimentos geradores "
            "de gotícula/aerossol sem EPI. Contato transitório isolado não configura contato próximo."
        ),
    },
    {
        "id": "quimio_nt97",
        "titulo": "Quimioprofilaxia — indicação e prazo",
        "tema": "quimioprofilaxia",
        "tags": "quimioprofilaxia rifampicina ceftriaxona ciprofloxacino 24h 48h 10 dias dm hib",
        "fonte": "NT nº 97/2024-DPNI/SVSA/MS; Informe Meningites 2024",
        "texto": (
            "Quimioprofilaxia deve ser feita o mais rápido possível nos contatos próximos de caso "
            "suspeito ou confirmado de DM ou doença invasiva por Hib, idealmente nas primeiras 24h "
            "após início dos sintomas. O indicador nacional monitora realização em até 48h da notificação "
            "para DM. Se administrada após 10 dias da exposição, o valor é limitado ou nulo; "
            "excepcionalmente pode ser feita em até 30 dias em populações vulneráveis. "
            "Primeira escolha: rifampicina (simultânea a todos os contatos). Alternativas: ceftriaxona, "
            "ciprofloxacino, azitromicina. Gestantes: preferir ceftriaxona. "
            "Indicação rotineira apenas para DM e Hib — não para demais etiologias. "
            "O paciente recebe quimio somente se o tratamento não for com cefalosporina de 3ª geração. "
            "Profissionais de saúde: só se fizeram procedimentos invasivos geradores de aerossol sem EPI "
            "antes de completar 24h de tratamento adequado do paciente."
        ),
    },
    {
        "id": "surto_comunitario_nt97",
        "titulo": "Surto comunitário de DM (NT 97/2024)",
        "tema": "surto",
        "tags": "surto comunitario dm sorogrupo cultura pcr 3 casos 3 meses incidencia canal endemico",
        "fonte": "NT nº 97/2024-DPNI/SVSA/MS",
        "texto": (
            "Surto comunitário de doença meningocócica: ocorrência de pelo menos três casos primários "
            "(sem vínculo entre si), do mesmo sorogrupo, confirmados por cultura ou PCR, no período "
            "≤3 meses, em uma mesma localidade (distrito, bairro, cidade). A incidência atual deve "
            "estar superior à incidência média esperada dos últimos cinco anos (diagrama de controle/"
            "canal endêmico), desconsiderando anos atípicos. Se incidência histórica muito baixa, "
            "comparar com regional/estadual. Também avaliar se o número de casos dobra de uma semana "
            "para a outra. Encerramento do cenário de surto: regresso sustentado de pelo menos 3 meses "
            "ao canal endêmico, em discussão conjunta municipal, estadual e MS."
        ),
    },
    {
        "id": "surto_institucional_nt97",
        "titulo": "Surto institucional de DM (NT 97/2024)",
        "tema": "surto",
        "tags": "surto institucional escola universidade creche 2 casos sorogrupo cultura pcr",
        "fonte": "NT nº 97/2024-DPNI/SVSA/MS",
        "texto": (
            "Surto institucional de DM: pelo menos dois casos primários (sem vínculo entre si), "
            "do mesmo sorogrupo, confirmados por cultura ou PCR, em período ≤3 meses, entre indivíduos "
            "que frequentam a mesma instituição (universidades, escolas, creches, indústrias, ILPI, "
            "unidades correcionais). Em surto, considerar quimioprofilaxia ampliada."
        ),
    },
    {
        "id": "indicadores_ms_2024",
        "titulo": "Indicadores operacionais nacionais (Informe 2024)",
        "tema": "indicadores",
        "tags": "indicador indicadores laboratorio pcr cultura investigacao 48h encerramento 60 dias quimioprofilaxia ministerio saude monitora monitoramento operacional",
        "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS",
        "texto": (
            "Indicadores de vigilância epidemiológica e laboratorial monitorados nacionalmente: "
            "(1) percentual de casos confirmados por critério laboratorial (RT-qPCR e cultura) — Brasil 2024: 36,1%; "
            "(2) percentual de casos investigados em até 48h da notificação — 97,8%; "
            "(3) percentual de casos encerrados em até 60 dias da notificação — 94,4%; "
            "(4) percentual de casos de DM com quimioprofilaxia de contatos em até 48h da notificação — 45,5%. "
            "No Caderno SINAN, confirmação laboratorial de bacterianas também considera cultura, CIE, PCR e látex."
        ),
    },
    {
        "id": "criterio_lab_caderno",
        "titulo": "Confirmação laboratorial (Caderno SINAN)",
        "tema": "laboratorio",
        "tags": "cultura cie pcr latex criterio confirmacao bacteriana especificidade",
        "fonte": "Caderno de Análises SINAN — Meningites",
        "texto": (
            "Proporção de casos de meningite bacteriana confirmados por critério laboratorial = "
            "nº de bacterianas confirmadas encerradas com cultura, CIE, PCR ou látex × 100 / "
            "nº de bacterianas confirmadas. Avalia capacidade de identificar o agente, orienta medidas "
            "de controle e melhora a especificidade do sistema. Etiologias bacterianas típicas: "
            "DM (MM, MCC, MM+MCC), MTBC, MB, MH e MP."
        ),
    },
    {
        "id": "quimio_inconsistencia",
        "titulo": "Inconsistência quimioprofilaxia × etiologia",
        "tema": "qualidade",
        "tags": "inconsistencia quimio etiologia dm hib qualidade sinan",
        "fonte": "Caderno de Análises SINAN — Meningites",
        "texto": (
            "A quimioprofilaxia é medida de controle para prevenir casos secundários e só está indicada "
            "para doença meningocócica (MM, MCC, MM+MCC) e meningite por Haemophilus (MH/Hib). "
            "Não deve ser realizada para as demais etiologias. Quimio registrada em etiologia não elegível "
            "deve ser auditada (erro de classificação ou de preenchimento)."
        ),
    },
    {
        "id": "investigacao_analise",
        "titulo": "Objetivos da investigação epidemiológica",
        "tema": "investigacao",
        "tags": "investigacao fonte transmissao surto medidas controle ficha sinan",
        "fonte": "Guia de Vigilância em Saúde — Meningites",
        "texto": (
            "A investigação visa caracterizar clinicamente o caso (incluindo exames laboratoriais), "
            "identificar possíveis fontes de transmissão, verificar necessidade de identificação de "
            "contatos e implementar medidas de controle. Perguntas-guia: qual a fonte de infecção? "
            "Houve transmissão a outras pessoas? É caso isolado ou surto? Há medidas a executar? "
            "A investigação não se esgota no preenchimento da ficha SINAN."
        ),
    },
    {
        "id": "monitoramento_semanal",
        "titulo": "Monitoramento semanal recomendado",
        "tema": "monitoramento",
        "tags": "monitoramento semanal dm viral municipio canal endemico sorogrupo letalidade",
        "fonte": "Guia de Vigilância em Saúde — Meningites",
        "texto": (
            "Atividades recomendadas: acompanhamento semanal de casos de DM e meningite viral por "
            "município para detectar surtos; revisão das fichas; acompanhamento de incidência e "
            "letalidade por etiologia, sazonalidade e sorogrupo predominante de N. meningitidis; "
            "análise de indicadores operacionais (oportunidade de quimio, investigação, encerramento "
            "e % confirmação laboratorial)."
        ),
    },
    {
        "id": "incidencia_letalidade",
        "titulo": "Incidência, mortalidade e letalidade",
        "tema": "epidemiologia",
        "tags": "incidencia mortalidade letalidade 100 mil confirmados populacao",
        "fonte": "Caderno de Análises SINAN / Informe Meningites",
        "texto": (
            "Coeficiente de incidência: casos confirmados / população × 100.000. "
            "Mortalidade: óbitos por meningite / população × 100.000. "
            "Letalidade: óbitos por meningite / casos confirmados × 100. "
            "Calcular por etiologia, município, faixa etária e sexo. Usar população do ano e área "
            "avaliada (DATASUS/IBGE). Meningites bacterianas costumam ter letalidade bem maior "
            "que as virais."
        ),
    },
]


FAQ_RAPIDO = [
    {
        "pergunta": "O que fazer diante de um caso de doença meningocócica?",
        "doc_ids": ["notif_24h", "contato_proximo_nt97", "quimio_nt97", "investigacao_analise"],
    },
    {
        "pergunta": "Quando caracterizar surto comunitário de DM?",
        "doc_ids": ["surto_comunitario_nt97"],
    },
    {
        "pergunta": "Quais indicadores o MS monitora para meningites?",
        "doc_ids": ["indicadores_ms_2024", "criterio_lab_caderno"],
    },
    {
        "pergunta": "Quimioprofilaxia é indicada para meningite viral?",
        "doc_ids": ["quimio_inconsistencia", "quimio_nt97"],
    },
]
