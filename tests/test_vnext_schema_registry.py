import pytest

from meningites.domain.schema_registry import SCHEMAS, require_schema, schema_catalog


def test_schema_registry_exposes_current_contracts():
    catalog = schema_catalog()
    assert catalog["agent_context"]["current"] == "agent-context-vnext-1"
    assert catalog["llm_response"]["current"] == "llm-response-vnext-2"


def test_require_schema_accepts_current_version():
    assert require_schema({"schema_version": "agent-context-vnext-1"}, "agent_context") == "agent-context-vnext-1"


def test_require_schema_rejects_unknown_version():
    with pytest.raises(ValueError):
        require_schema({"schema_version": "agent-context-vnext-99"}, "agent_context")


def test_require_schema_rejects_missing_version():
    with pytest.raises(ValueError):
        require_schema({}, "agent_context")


def test_every_contract_has_current_version_in_accepted():
    for contract in SCHEMAS.values():
        assert contract.current in contract.accepted
