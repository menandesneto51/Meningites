"""Preflight único do Meningites VNext.

Executa, em sequência:
1) módulo 12 (opcional);
2) publisher VNext;
3) gate de validação;
4) captura de evidência somente em PASS.

Não promove ATTENTION/FAIL e não edita artefatos manualmente.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from meningites.operational_queue.publisher import publish_municipal_vnext
from meningites.validation.reconcile import publish_validation_report
from meningites.validation.evidence import publish_validation_evidence


def _run_module12(root: Path) -> dict:
    script = root / "12_indicadores_ms_operacionais_v23.py"
    if not script.exists():
        return {"step": "module12", "status": "fail", "detail": "script ausente"}
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return {
        "step": "module12",
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def run_preflight(
    *,
    repo_root: str | Path,
    outdir: str | Path,
    commit_sha: str = "",
    skip_module12: bool = False,
) -> dict:
    root = Path(repo_root).resolve()
    out = (root / outdir).resolve() if not Path(outdir).is_absolute() else Path(outdir)
    steps = []

    if not skip_module12:
        step = _run_module12(root)
        steps.append(step)
        if step["status"] != "pass":
            return _finish("fail", steps, out, "Módulo 12 falhou; preflight interrompido.")

    publish_municipal_vnext(out)
    steps.append({"step": "publisher", "status": "pass"})

    validation_paths = publish_validation_report(out)
    validation = json.loads(validation_paths["validation_json"].read_text(encoding="utf-8"))
    gate = str(validation.get("overall_status", "fail")).lower()
    steps.append({
        "step": "validation",
        "status": gate,
        "fail_n": validation.get("fail_n", 0),
        "attention_n": validation.get("attention_n", 0),
    })

    if gate != "pass":
        return _finish(gate, steps, out, "Gate não aprovado; evidência não será capturada.")

    evidence_paths = publish_validation_evidence(out, commit_sha=commit_sha or None)
    steps.append({
        "step": "evidence",
        "status": "pass",
        "json": str(evidence_paths["evidence_json"]),
        "markdown": str(evidence_paths["evidence_md"]),
    })
    return _finish("pass", steps, out, "Preflight concluído com PASS e evidência capturada.")


def _finish(status: str, steps: list[dict], out: Path, detail: str) -> dict:
    result = {
        "schema_version": "vnext-preflight-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "detail": detail,
        "outdir": str(out),
        "steps": steps,
        "human_review_required": True,
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / "preflight_vnext.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o preflight completo do Meningites VNext.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--skip-module12", action="store_true")
    args = parser.parse_args()

    result = run_preflight(
        repo_root=args.repo_root,
        outdir=args.outdir,
        commit_sha=args.commit,
        skip_module12=args.skip_module12,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
