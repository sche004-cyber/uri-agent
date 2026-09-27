"""M33.3-R protected-anchor verification (S1-S4 frozen inputs).

Two anchor sets are verified:
- the S4 replay ANCHORS (raw bytes, read from the frozen S4 runner, which pins
  the current active RAR hash 4db77566...; the historical Batch A/A9 hash
  e02af25b... is history only and is not verified here);
- the M33.3-R frozen S1/S2/S3/S4 code and fixture set below (SHA-256 over
  bytes with CRLF normalized to LF, recorded at baseline c2f5839).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_RAR_SHA256 = "4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95"
HISTORICAL_BATCH_A_RAR_SHA256 = "e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649"

FROZEN_LF_ANCHORS = {
    "uri_v1/reference_clarification/__init__.py": "cb3fbcf8216ba13a2978e4e58f2cf736717b459e7a138a6a53da0b9d825c7f6f",
    "uri_v1/reference_clarification/attribute_narrowing.py": "dfaad7006769fcd2db19454e8716f116ce972fdef831583d75b95c92596d0022",
    "uri_v1/reference_clarification/authority.py": "607cc4703da2cb5117fdd0286a82eac650e82ae78fe7a22f3041ef4f3d6381af",
    "uri_v1/reference_clarification/binding.py": "cba395d282c03ef3006203519f151021d3c91642a86c08ded5dcbd1ea5f8a655",
    "uri_v1/reference_clarification/builder.py": "d564fbb2227fd21b6eeed68e574ed3eebd8aeddd1e5b4eb07047a68192478f59",
    "uri_v1/reference_clarification/bundle.py": "d0bd370d06b6e967dbda1e9d84274e918401c0ee2aa8ca153d28a2b9e31b279c",
    "uri_v1/reference_clarification/facts.py": "d9cb0bd9f3a2d34ce149bcca71eac7cf24f6acc34a29f1872cf16d03e67708e9",
    "uri_v1/reference_clarification/fingerprints.py": "27a582290d0b41e504c688d842512c90b8b49a643141eb349ea8ac195cd5911b",
    "uri_v1/reference_clarification/render_contracts.py": "119da8516b343078a7fa23835f9169b438dbe178f811db52aa523a934d1b9024",
    # Re-pinned 2026-09-27 by amendment S1-A1 (User decision at the S5 touchpoint: bounded
    # function-word allowlist widening). Baseline c2f5839 value: 903ef9fe...3e0e.
    "uri_v1/reference_clarification/render_validator.py": "4a29cc25381668a1a10cef81f39165f0f49e0709d0b40366e99c0fb08b6a29f3",
    "uri_v1/reference_clarification/safeguards.py": "5a4e66494303160304ddb1707f9c7b125471134cf8cbbbb2218cbb77fb9ff88c",
    "uri_v1/reference_clarification/session_adjunct.py": "ff59a5a6025011478006dd57657d5156b0a9810223f31e3833f29433ec9b7955",
    "uri_v1/reference_clarification/store.py": "928a972a6ef71e9dabe1e7bbf9980d2caa8f25a1753dd00509e0fe3f804ccf43",
    "uri_v1/reference_clarification/template_renderer.py": "016ef203c5117fddc4b47fc56a0081d5b2427aac7daf2b5640875c4d9d0acd56",
    "uri_v1/turn/rar_clarification_contract.py": "114c6b735823ed93cd958eea7b081ca845c9fa601dff880623a46a586bf49e11",
    "uri_core/capabilities/wrong_binding.py": "2454525f98fd8474445b47e9d5a3d11995a49ed4991a3916965a79740dc53654",
    "uri_core/capabilities/base.py": "98d9fdd9c95bf32f6befcf12a9f9af5355085242f3ce2a61d615aa0d3f470337",
    "uri_core/capabilities/registry.py": "551c6cff542ffc65960c783ecd6a451c9ad43e0a977abe924658b30d12c45742",
    "scripts/m33_3_s3_qualify.py": "ce8ed5f30d8bc6997164812201c6cc193337e65f40fa782627d3b62ee5e742dc",
    "scripts/m33_3_s4_replay.py": "65b5ff75f2601f43009daa313f097bd0a141fa0241819c7efe5d5d9644d9cd9d",
    "scripts/m33_3_s4_source_to_candidate.py": "0ba1233c83866cb9ef9a6068ed9e0c2c9aee2f5ce63e5cbcbc87c290aff9c32f",
    "fixtures/m33_3_arn/battery.json": "3a0250aa92af755e64151a08dca0a5ea3f42f8cd767560471d720fb10af83b01",
    "fixtures/m33_3_arn/manifest.json": "9e3cfd76377dbaac1506e1a842e446b6591e23129bfbf27d96be989122b6c3bf",
    "fixtures/m33_3_batch_a/manifest.json": "efbe1a63423af4b9092d8fadb2324a0fe1dfa38e0f88a78496dc4768c371e716",
}


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def s4_anchors() -> dict[str, str]:
    source = (ROOT / "scripts" / "m33_3_s4_replay.py").read_text(encoding="utf-8")
    start = source.index("ANCHORS = {")
    namespace: dict = {}
    exec(source[start:source.index("}", start) + 1], namespace)
    return namespace["ANCHORS"]


def verify_anchors() -> dict:
    s4 = s4_anchors()
    if s4["uri_v1/turn/rar_deterministic.py"] != CURRENT_RAR_SHA256:
        raise RuntimeError("S4 runner no longer pins the current active RAR hash")
    raw = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in s4}
    lf = {name: _lf_sha256(ROOT / name) for name in FROZEN_LF_ANCHORS}
    changed = ([n for n, d in raw.items() if d != s4[n]] +
               [n for n, d in lf.items() if d != FROZEN_LF_ANCHORS[n]])
    return {"ok": not changed, "changed": changed, "s4_anchor_count": len(s4),
            "frozen_lf_anchor_count": len(FROZEN_LF_ANCHORS), "current_rar_sha256": CURRENT_RAR_SHA256}


def require_anchors() -> dict:
    result = verify_anchors()
    if not result["ok"]:
        raise RuntimeError(f"FROZEN_ANCHOR_INTEGRITY_FAILURE: {result['changed']}")
    return result


if __name__ == "__main__":
    print(require_anchors())
