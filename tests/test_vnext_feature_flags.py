import os

from meningites.feature_flags import enabled


def test_feature_flag_defaults_to_false(monkeypatch):
    monkeypatch.delenv("MENINGITES_VNEXT_AGENT_UI", raising=False)
    assert enabled("MENINGITES_VNEXT_AGENT_UI", default=False) is False


def test_feature_flag_accepts_explicit_true(monkeypatch):
    monkeypatch.setenv("MENINGITES_VNEXT_AGENT_UI", "true")
    assert enabled("MENINGITES_VNEXT_AGENT_UI", default=False) is True


def test_feature_flag_rejects_false(monkeypatch):
    monkeypatch.setenv("MENINGITES_VNEXT_AGENT_UI", "0")
    assert enabled("MENINGITES_VNEXT_AGENT_UI", default=True) is False
