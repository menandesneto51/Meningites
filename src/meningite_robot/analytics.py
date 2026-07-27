from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


def _cramers_v(confusion: pd.DataFrame) -> float:
    chi2 = stats.chi2_contingency(confusion.fillna(0))[0]
    n = confusion.values.sum()
    r, k = confusion.shape
    return float(np.sqrt((chi2 / max(n, 1)) / max(min(k - 1, r - 1), 1)))


def comparative_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Testes robustos entre evolução/desfecho e variáveis clínicas/sociodemográficas."""
    outcome_cols = [c for c in ["EvolucaoCaso", "ClassificacaoCaso", "obito_meningite", "hospitalizado"] if c in df.columns]
    candidate_cols = [
        c for c in df.columns
        if c.endswith("_bin")
        or c in ["SexoPaciente", "RacaPaciente", "FaixaEtaria", "ClassificacaoMeningite", "CriterioConfirmacao", "ZonaResidencia"]
    ]

    rows = []
    for outcome in outcome_cols:
        y = df[outcome]
        for x in candidate_cols:
            if x == outcome:
                continue
            temp = df[[outcome, x]].dropna()
            if temp.empty or temp[outcome].nunique() < 2 or temp[x].nunique() < 2:
                continue
            table = pd.crosstab(temp[x], temp[outcome])
            try:
                if table.shape == (2, 2):
                    # Fisher para tabelas pequenas; qui-quadrado quando adequado.
                    if (table.values < 5).any():
                        _, p = stats.fisher_exact(table.values)
                        test = "Fisher"
                    else:
                        _, p, _, _ = stats.chi2_contingency(table)
                        test = "Qui-quadrado"
                else:
                    _, p, _, _ = stats.chi2_contingency(table)
                    test = "Qui-quadrado"
                effect = _cramers_v(table)
                rows.append({
                    "desfecho": outcome,
                    "variavel": x,
                    "teste": test,
                    "p_value": p,
                    "efeito_cramers_v": effect,
                    "n": int(len(temp)),
                    "interpretacao": _interpret_p_effect(p, effect),
                })
            except Exception as exc:
                rows.append({"desfecho": outcome, "variavel": x, "teste": "erro", "erro": str(exc)})
    return pd.DataFrame(rows).sort_values(["desfecho", "p_value"], na_position="last")


def _interpret_p_effect(p: float, effect: float) -> str:
    sig = "associação estatisticamente significativa" if p < 0.05 else "sem evidência estatística robusta de associação"
    if effect < 0.1:
        mag = "efeito muito pequeno"
    elif effect < 0.3:
        mag = "efeito pequeno"
    elif effect < 0.5:
        mag = "efeito moderado"
    else:
        mag = "efeito forte"
    return f"{sig}; {mag}."


def logistic_or_model(df: pd.DataFrame, outcome: str = "obito_meningite") -> pd.DataFrame:
    """Regressão logística múltipla com OR e IC95.

    Inclui variáveis sociodemográficas, sintomas, comorbidades e vacinação.
    """
    if outcome not in df.columns or df[outcome].nunique(dropna=True) < 2:
        return pd.DataFrame({"erro": [f"Desfecho {outcome} indisponível ou sem variação."]})

    covars = []
    base_covars = ["idade_anos", "SexoPaciente", "RacaPaciente", "ZonaResidencia", "ClassificacaoMeningite"]
    covars.extend([c for c in base_covars if c in df.columns])
    covars.extend([c for c in df.columns if c.endswith("_bin") and any(prefix in c for prefix in ["Vacina", "DoencasPreexistentes", "SinaisESintomas"])])

    model_df = df[[outcome] + covars].copy().dropna(subset=[outcome])
    # Reduz cardinalidade e evita matrizes gigantes.
    cat_cols = [c for c in model_df.columns if model_df[c].dtype == "object" and c != outcome]
    for c in cat_cols:
        top = model_df[c].value_counts().head(8).index
        model_df[c] = np.where(model_df[c].isin(top), model_df[c], "Outros/Ignorado")

    X = pd.get_dummies(model_df[covars], drop_first=True, dummy_na=True)
    X = X.apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(model_df[outcome], errors="coerce")
    valid = y.notna()
    X, y = X.loc[valid], y.loc[valid]

    # Remove variáveis com variância zero e limita dimensionalidade.
    X = X.loc[:, X.nunique(dropna=True) > 1]
    if X.shape[1] > 60:
        # Seleção univariada simples para estabilidade.
        scores = {}
        for col in X.columns:
            try:
                scores[col] = abs(np.corrcoef(X[col].fillna(0), y)[0, 1])
            except Exception:
                scores[col] = 0
        keep = sorted(scores, key=scores.get, reverse=True)[:60]
        X = X[keep]

    X = sm.add_constant(X.fillna(0), has_constant="add")
    try:
        model = sm.Logit(y, X).fit(disp=False, maxiter=300)
    except Exception:
        try:
            model = sm.Logit(y, X).fit_regularized(disp=False, maxiter=300)
        except Exception as exc:
            return pd.DataFrame({"erro": [f"Falha no modelo logístico: {exc}"]})

    params = model.params
    conf = model.conf_int() if hasattr(model, "conf_int") else pd.DataFrame(index=params.index, data={0: np.nan, 1: np.nan})
    pvals = getattr(model, "pvalues", pd.Series(index=params.index, data=np.nan))

    out = pd.DataFrame({
        "variavel": params.index,
        "coef_logit": params.values,
        "OR": np.exp(params.values),
        "IC95_inf": np.exp(conf[0].values),
        "IC95_sup": np.exp(conf[1].values),
        "p_value": pvals.values,
    })
    out = out[out["variavel"] != "const"].sort_values("p_value", na_position="last")
    out["interpretacao"] = out.apply(
        lambda r: "Aumento das chances" if r["OR"] > 1 else "Redução das chances", axis=1
    )
    return out
