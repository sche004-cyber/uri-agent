"""Run the M33.2 B.1 experimental ensemble matrix and write raw evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from uri_core.core.edge.adapters.benchmark import run_benchmark, write_artifacts
from uri_core.core.edge.adapters.ensemble import (
    build_candidate_configurations,
    build_fixture_baseline_candidate,
    build_fixture_candidate_configurations,
)


def main() -> None:
    manifest = json.loads(
        (ROOT / "fixtures/m33_2_edge_benchmark/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest["corpus"] = str(ROOT / manifest["corpus"])
    corpus = json.loads(Path(manifest["corpus"]).read_text(encoding="utf-8"))
    candidates = {"fixture-baseline": build_fixture_baseline_candidate()}
    candidates.update(
        {
            f"fixture-configuration-{name.lower()}": candidate
            for name, candidate in build_fixture_candidate_configurations().items()
        }
    )
    candidates.update(
        {
            f"actual-configuration-{name.lower()}": candidate
            for name, candidate in build_candidate_configurations().items()
        }
    )

    evidence_root = ROOT / "temp_evidence/m33_2_batch_b1"
    for config_id, candidate in candidates.items():
        result = run_benchmark(candidate, corpus)
        write_artifacts(evidence_root / config_id, manifest, result)
        print(
            f"{config_id}: runtime={result.runtime_status} "
            f"qualification={result.qualification} correctness={result.correctness:.3f}"
        )


if __name__ == "__main__":
    main()
