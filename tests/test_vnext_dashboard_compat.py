from pathlib import Path


DASHBOARD = Path("dashboard_meningites_v22_refinado.py")


def test_legacy_dashboard_does_not_require_vnext_package_at_top_level():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "from meningites.feature_flags import" not in text
    assert 'def _feature_enabled(name: str, default: bool = False) -> bool:' in text


def test_vnext_streamlit_panel_import_remains_lazy():
    lines = DASHBOARD.read_text(encoding="utf-8").splitlines()
    matches = [
        (idx + 1, line)
        for idx, line in enumerate(lines)
        if "from meningites.agent.streamlit_panel import render_agent_panel" in line
    ]
    assert len(matches) == 1
    _, line = matches[0]
    assert line.startswith(" " * 16) or line.startswith("\t")
