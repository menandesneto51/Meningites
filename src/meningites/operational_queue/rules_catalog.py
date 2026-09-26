"""Catálogo inicial de regras operacionais VNext.

Somente regras de presença de fila (n > 0). Não introduz limiares clínicos,
incidência, definição de surto ou meta normativa nova.
"""
from meningites.operational_queue.municipal_engine import SignalRule


PRODUCTION_RULES = (
    SignalRule(
        rule_id="fila-cievs-presente",
        metric="fila_cievs_n",
        title="Município com itens na fila CIEVS",
        category="operacao",
        priority="moderada",
        operator="gt",
        threshold=0,
        description="Há pelo menos um item já produzido pela fila CIEVS vigente.",
        suggested_actions=("Revisar os itens priorizados na fila CIEVS vigente.",),
    ),
    SignalRule(
        rule_id="gal-tipagem-pendente",
        metric="gal_tipagem_pendente_n",
        title="Pendência de tipagem GAL/SINAN",
        category="laboratorio",
        priority="alta",
        operator="gt",
        threshold=0,
        description="Há pelo menos um registro na fila de tipagem GAL/SINAN produzida pelo módulo 32.",
        suggested_actions=("Revisar a fila de tipagem e a atualização correspondente no SINAN.",),
    ),
    SignalRule(
        rule_id="sih-sem-sinan",
        metric="sih_sem_sinan_n",
        title="Internação compatível sem vínculo SINAN",
        category="reconciliacao",
        priority="alta",
        operator="gt",
        threshold=0,
        description="Há pelo menos um registro na fila SIH sem vínculo SINAN produzida pelo módulo 33.",
        suggested_actions=("Revisar a fila SIH/SINAN e confirmar a necessidade de investigação/reconciliação.",),
    ),
    SignalRule(
        rule_id="redcap-sem-sinan",
        metric="redcap_sem_sinan_n",
        title="Registro RedCap aberto sem vínculo SINAN",
        category="reconciliacao",
        priority="alta",
        operator="gt",
        threshold=0,
        description="Há pelo menos um registro no gap RedCap/SINAN produzido pelo módulo 35.",
        suggested_actions=("Revisar o registro na fila RedCap e o vínculo com SINAN.",),
    ),
)
