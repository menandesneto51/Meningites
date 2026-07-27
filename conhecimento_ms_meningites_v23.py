# -*- coding: utf-8 -*-
"""
conhecimento_ms_meningites_v23.py
Base de conhecimento local (trechos normativos) para o assistente CIEVS.
Fontes públicas: Informe Meningites 2024, NT Conjunta nº 154/2024-DPNI/SVSA/MS
(retifica/revoga a NT 97/2024), Caderno de Análises SINAN (Meningites),
Guia de Vigilância em Saúde.
"""

from __future__ import annotations

NORMA_SURTO_QUIMIO = (
    "NT Conjunta nº 154/2024-DPNI/SVSA/MS "
    "(retifica e revoga a NT nº 97/2024-DPNI/SVSA/MS)"
)

DOCS = [
    {
        "id": "norma_vigente_nt154",
        "titulo": "Norma vigente — NT Conjunta 154/2024",
        "tema": "norma",
        "tags": "nt 154 97 retifica revoga vigilancia meningite dm hib",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "A Nota Técnica Conjunta nº 154/2024-DPNI/SVSA/MS (SEI 25000.108654/2024-97) "
            "revisa definições de caso suspeito, contatos, surto de doença meningocócica e "
            "orientações de quimioprofilaxia para DM e doença invasiva por Hib; inclui "
            "orientações de vacinação pós-DIHib; e revoga/retifica a NT nº 97/2024-DPNI/SVSA/MS "
            "e as definições equivalentes da 6ª edição do Guia de Vigilância em Saúde. "
            "Os conceitos da NT 154 devem ser adotados a partir de sua publicação e serão "
            "incorporados à 7ª edição do GVS. Use sempre a NT 154 como referência operacional "
            "atual; a NT 97 permanece apenas como documento histórico revogado."
        ),
    },
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
        "id": "caso_suspeita_nt154",
        "titulo": "Definição de caso suspeito (NT 154/2024)",
        "tema": "definicao_caso",
        "tags": "caso suspeito febre rigidez nuca cefaleia vomito petequia fontanela kernig brudzinski",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "Caso suspeito de meningite (NT 154/2024): "
            "(1) indivíduo com febre acompanhada de dois ou mais entre: cefaleia intensa, vômito, "
            "confusão/alteração mental, fotofobia, torpor, convulsão; OU "
            "(2) febre com pelo menos um sinal de irritação meníngea (rigidez de nuca, Kernig ou Brudzinski); OU "
            "(3) febre de início súbito com erupções petequiais ou sufusões hemorrágicas; OU "
            "(4) em menores de 2 anos, além do acima, febre com irritabilidade, choro persistente, "
            "sonolência ou abaulamento de fontanela. "
            "Em surto, usar definição mais sensível: febre + um ou mais de confusão, convulsão, torpor, "
            "irritação meníngea ou petéquias/sufusões; OU febre + dois ou mais entre cefaleia, vômito e fotofobia."
        ),
    },
    {
        "id": "contato_proximo_nt154",
        "titulo": "Contato próximo (NT 154/2024)",
        "tema": "contatos",
        "tags": "contato proximo exposicao goticulas domicilio creche escola 4 horas 10 dias 1 metro",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "Contato próximo (NT 154/2024): indivíduo com contato direto e prolongado com caso "
            "suspeito ou confirmado de DM ou doença invasiva por Hib, com exposição a gotículas "
            "de secreções respiratórias. "
            "Retrospectivo: do início dos sintomas até 10 dias anteriores. "
            "Prospectivo: do início dos sintomas até 24h após início de tratamento com "
            "cefalosporina de 3ª geração (ceftriaxona/cefotaxima) ou rifampicina. "
            "Situações: mesmo domicílio/dormitório; beijo/troca salivar; exposição próxima e contínua "
            "de pelo menos 4 horas E até 1 metro em ambiente fechado; exposição por pelo menos "
            "5 dias (contínuos ou não) — ex. creche/ensino infantil; procedimentos geradores de "
            "aerossol/gotícula sem EPI antes de 24h de tratamento. "
            "Contato transitório isolado não configura contato próximo."
        ),
    },
    {
        "id": "quimio_nt154",
        "titulo": "Quimioprofilaxia — indicação e prazo (NT 154/2024)",
        "tema": "quimioprofilaxia",
        "tags": "quimioprofilaxia rifampicina ceftriaxona ciprofloxacino azitromicina 24h 48h 10 dias 30 dias dm hib",
        "fonte": f"{NORMA_SURTO_QUIMIO}; Informe Meningites 2024",
        "texto": (
            "Objetivo: interromper transmissão por descolonização de nasofaringe e prevenir casos "
            "secundários. Realizar o mais breve possível nos contatos próximos de caso suspeito/"
            "confirmado de DM ou DIHib, idealmente nas primeiras 24h após início dos sintomas. "
            "O indicador nacional monitora quimio em DM em até 48h da notificação. "
            "Após 10 dias da exposição o valor é limitado/nulo na maioria dos casos secundários de DM; "
            "para DIHib, a quimio poderá ser realizada em até 30 dias após a exposição. "
            "Em surto: quimioprofilaxia ampliada (todos com contato direto nos 10 dias anteriores "
            "e durante os sintomas). "
            "1ª escolha: rifampicina (simultânea a todos os contatos). Alternativas: ceftriaxona, "
            "ciprofloxacino; azitromicina 500 mg dose única se resistência ao cipro ou ausência das demais. "
            "Gestantes: ceftriaxona como 1ª escolha. Lactantes: rifampicina compatível com amamentação. "
            "Paciente: quimio só se o tratamento não for com cefalosporina de 3ª geração. "
            "Indicação rotineira apenas DM e Hib — não demais etiologias. "
            "Para Hi sem tipagem ainda disponível, realizar quimio nas condições de Hib até a tipagem."
        ),
    },
    {
        "id": "quimio_hib_detalhe_nt154",
        "titulo": "Quimioprofilaxia específica — DIHib (NT 154/2024)",
        "tema": "quimioprofilaxia",
        "tags": "hib dihib creche domicilio imunocomprometido menor 4 anos vacina incompleta",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "DIHib — devem receber quimio: (a) o paciente se não tratado com cefalosporina 3ª geração; "
            "(b) todos os contatos domiciliares se houver imunocomprometido ou criança <2 anos "
            "(independentemente da vacina) OU criança <4 anos não vacinada/esquema incompleto; "
            "(c) demais contatos próximos que tenham em seu domicílio imunocomprometido/<2 anos "
            "ou <4 anos com vacina incompleta (quimio só no contato direto do caso-índice); "
            "(d) em creche/ensino infantil: cuidadores e crianças <4 anos da sala do caso se contato "
            "≥5 dos 10 dias pré-sintomas ou durante sintomas, quando houver vulnerável na sala; "
            "e TODOS os contatos da sala se for o 2º caso de doença invasiva por Hi em até 60 dias. "
            "Não há evidência de quimio para Hi não-b; contudo, iniciar conforme Hib até tipagem."
        ),
    },
    {
        "id": "surto_comunitario_nt154",
        "titulo": "Surto comunitário de DM (NT 154/2024)",
        "tema": "surto",
        "tags": "surto comunitario dm sorogrupo cultura pcr 3 casos 3 meses incidencia canal endemico",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "Surto comunitário de DM (NT 154/2024): ≥3 casos primários (sem vínculo entre si), "
            "do mesmo sorogrupo, confirmados por cultura ou PCR, em período ≤3 meses, na mesma "
            "localidade (distrito, bairro, cidade). A incidência atual deve superar a média esperada "
            "dos últimos 5 anos (diagrama de controle/canal endêmico), desconsiderando anos atípicos. "
            "Se incidência histórica muito baixa, comparar com regional/estadual. Avaliar também "
            "duplicação semanal de casos. Novo sorogrupo circulante pode dispensar o critério de "
            "incidência. Alta concentração etária: avaliar a população sob risco. "
            "Encerramento: regresso sustentado ≥3 meses ao canal endêmico, em discussão conjunta "
            "municipal, estadual e MS."
        ),
    },
    {
        "id": "surto_institucional_nt154",
        "titulo": "Surto institucional de DM (NT 154/2024)",
        "tema": "surto",
        "tags": "surto institucional escola universidade creche 2 casos sorogrupo cultura pcr",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "Surto institucional de DM (NT 154/2024): ≥2 casos primários (sem vínculo entre si), "
            "do mesmo sorogrupo, confirmados por cultura ou PCR, em período ≤3 meses, entre "
            "indivíduos da mesma instituição (universidades, escolas, creches, indústrias, ILPI, "
            "unidades correcionais). Em surto, considerar quimioprofilaxia ampliada."
        ),
    },
    {
        "id": "vacina_pos_hib_nt154",
        "titulo": "Vacinação complementar pós-DIHib (NT 154/2024)",
        "tema": "vacina",
        "tags": "hib vacina dose adicional penta hexa 6 meses 2 anos dose d especial",
        "fonte": NORMA_SURTO_QUIMIO,
        "texto": (
            "Crianças com doença invasiva por Hib antes dos 2 anos podem ter risco de 2º episódio "
            "(infecção natural nessa idade não gera proteção robusta). "
            "(a) <2 anos sem vacina ou esquema incompleto: iniciar/completar com penta (rotina) "
            "ou hexa acelular (CRIE), conforme PNI. "
            "(b) 6 meses a <2 anos com esquema completo: administrar 1 dose adicional de vacina "
            "com componente Hib, intervalo mínimo 60 dias após a última dose Hib. "
            "Iniciar vacinação 30 dias após o início da doença invasiva (ou o mais breve após esse prazo). "
            "A partir de 2 anos com esquema completo, em geral não precisam dose extra. "
            "Registro da dose adicional (item b): estratégia Especial; tipo Dose D (<2 anos); "
            "categoria faixa etária; motivo CID-10 A49.2."
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
            "No Caderno SINAN, confirmação laboratorial de bacterianas também considera cultura, CIE, PCR e látex. "
            "A oportunidade de quimio e a resposta a surtos/contatos seguem a NT 154/2024."
        ),
    },
    {
        "id": "criterio_lab_caderno",
        "titulo": "Confirmação laboratorial (Caderno SINAN)",
        "tema": "laboratorio",
        "tags": "cultura cie pcr latex criterio confirmacao bacteriana especificidade liquido liquórica",
        "fonte": "Caderno de Análises SINAN — Meningites; NT 154/2024 (coleta oportuna)",
        "texto": (
            "Proporção de casos de meningite bacteriana confirmados por critério laboratorial = "
            "nº de bacterianas confirmadas encerradas com cultura, CIE, PCR ou látex × 100 / "
            "nº de bacterianas confirmadas. Avalia capacidade de identificar o agente, orienta medidas "
            "de controle e melhora a especificidade do sistema. Etiologias bacterianas típicas: "
            "DM (MM, MCC, MM+MCC), MTBC, MB, MH e MP. "
            "NT 154: coletar líquor e sangue tão logo haja suspeita; não atrasar o tratamento pela coleta; "
            "encaminhar material/cepas ao LACEN para caracterização (incluindo tipagem Hi)."
        ),
    },
    {
        "id": "quimio_inconsistencia",
        "titulo": "Inconsistência quimioprofilaxia × etiologia",
        "tema": "qualidade",
        "tags": "inconsistencia quimio etiologia dm hib qualidade sinan",
        "fonte": "Caderno de Análises SINAN — Meningites; NT 154/2024",
        "texto": (
            "A quimioprofilaxia é medida de controle para prevenir casos secundários e só está indicada "
            "para doença meningocócica (MM, MCC, MM+MCC) e doença invasiva/meningite por Haemophilus "
            "(Hib/Hi até tipagem). Não deve ser realizada para as demais etiologias. "
            "Quimio registrada em etiologia não elegível deve ser auditada (erro de classificação ou de preenchimento)."
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


# Aliases de IDs antigos (NT 97) → mantêm FAQ/links antigos funcionando
_ALIASES = {
    "caso_suspeita_nt97": "caso_suspeita_nt154",
    "contato_proximo_nt97": "contato_proximo_nt154",
    "quimio_nt97": "quimio_nt154",
    "surto_comunitario_nt97": "surto_comunitario_nt154",
    "surto_institucional_nt97": "surto_institucional_nt154",
}
_by_id = {d["id"]: d for d in DOCS}
for old, new in _ALIASES.items():
    if old not in _by_id and new in _by_id:
        clone = dict(_by_id[new])
        clone["id"] = old
        DOCS.append(clone)


FAQ_RAPIDO = [
    {
        "pergunta": "Qual norma vigora após a NT 97 — a NT 154?",
        "doc_ids": ["norma_vigente_nt154"],
    },
    {
        "pergunta": "O que fazer diante de um caso de doença meningocócica?",
        "doc_ids": ["notif_24h", "contato_proximo_nt154", "quimio_nt154", "investigacao_analise"],
    },
    {
        "pergunta": "Quando caracterizar surto comunitário de DM?",
        "doc_ids": ["surto_comunitario_nt154"],
    },
    {
        "pergunta": "Quais indicadores o MS monitora para meningites?",
        "doc_ids": ["indicadores_ms_2024", "criterio_lab_caderno"],
    },
    {
        "pergunta": "Quimioprofilaxia é indicada para meningite viral?",
        "doc_ids": ["quimio_inconsistencia", "quimio_nt154"],
    },
    {
        "pergunta": "Como proceder a vacinação após doença invasiva por Hib?",
        "doc_ids": ["vacina_pos_hib_nt154"],
    },
    {
        "pergunta": "Quem recebe quimioprofilaxia em DIHib / creche?",
        "doc_ids": ["quimio_hib_detalhe_nt154", "contato_proximo_nt154"],
    },
]
