import ast
from pathlib import Path

import numpy as np
import pandas as pd


DASHBOARD = Path("dashboard_meningites_v22_refinado.py")


def _load_selected_functions(*names):
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    assert {node.name for node in selected} == set(names)
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {"pd": pd, "np": np}
    exec(compile(module, str(DASHBOARD), "exec"), namespace)
    return namespace


def test_dashboard_source_is_valid_python():
    ast.parse(DASHBOARD.read_text(encoding="utf-8"))


def test_sum_preserves_all_missing_group_as_missing():
    ns = _load_selected_functions("_sum_preserve_missing")
    fn = ns["_sum_preserve_missing"]

    all_missing = fn(pd.Series([np.nan, None]))
    observed_zero = fn(pd.Series([0, np.nan]))

    assert pd.isna(all_missing)
    assert observed_zero == 0


def test_metric_mask_distinguishes_missing_from_real_zero():
    ns = _load_selected_functions("_metric_with_data_mask")
    values, has_data = ns["_metric_with_data_mask"](
        pd.Series([np.nan, 0, 2, ""])
    )

    assert pd.isna(values.iloc[0])
    assert values.iloc[1] == 0
    assert has_data.tolist() == [False, True, True, False]


def test_map_does_not_reintroduce_missing_as_zero():
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "choropleth_or_points"
    )
    segment = ast.get_source_segment(source, fn)

    assert "_sum_preserve_missing" in segment
    assert "_has_metric_data" in segment
    assert "Sem dado (N/D)" in segment
    assert "zero colorido = zero observado" in segment
    assert ".fillna(0.0)" not in segment


def test_active_scope_summary_prioritizes_specific_territory():
    ns = _load_selected_functions("active_scope_summary")
    fn = ns["active_scope_summary"]

    assert fn([2026], [], [], [], [], []) == "Mato Grosso · Ano: 2026"
    assert fn([2026], ["Baixada Cuiabana"], [], [], [], []) == (
        "Regional: Baixada Cuiabana · Ano: 2026"
    )
    assert fn([2026], ["Baixada Cuiabana"], ["Cuiabá"], ["DM"], [], []) == (
        "Município: Cuiabá · Ano: 2026 · filtros clínicos ativos"
    )


def test_global_status_bar_is_rendered_from_active_filters():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "scope_text = active_scope_summary(" in source
    assert "render_global_status_bar(OUT, scope_text)" in source
    assert 'chip("Escopo ativo", status["scope"])' in source
    assert 'role="status"' in source
