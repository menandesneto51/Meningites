# ADR — Chave territorial municipal no VNext

**Data:** 2026-09-26  
**Status:** Aceito para compatibilidade com o pipeline atual

## Decisão

O Meningites VNext usará **IBGE-6** como chave municipal interna enquanto integrar artefatos legados do projeto.

Exemplos:
- Cuiabá: `5103403` na forma IBGE-7 externa → `510340` na chave interna;
- Várzea Grande: `5108402` → `510840`.

## Motivo

O contrato legado `meningites_v17_common.norm_code6` e módulos como SIH V33 e CIPV V34 já normalizam para seis dígitos. O VNext inicialmente aceitava até sete dígitos, o que poderia gerar duas entidades para o mesmo município durante merges entre fontes.

## Regras

1. Nunca inferir código municipal apenas pelo nome.
2. Aceitar código de entrada com 6 ou 7 dígitos, normalizando para IBGE-6.
3. Preservar o valor original na evidência/procedência quando necessário à auditoria.
4. Uma futura dimensão territorial poderá manter simultaneamente IBGE-6 interno e IBGE-7 oficial, mas a mudança deverá ser feita por migração explícita, não por heurística.
5. Testes devem cobrir merge de fontes 6×7 dígitos para impedir regressão.
