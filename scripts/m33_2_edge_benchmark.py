"""Run only explicit experimental local candidates; writes raw artifacts outside source."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from uri_core.core.edge.adapters.benchmark import BenchmarkCandidate,run_benchmark,write_artifacts
root=Path(__file__).parents[1]; manifest=json.loads((root/'fixtures/m33_2_edge_benchmark/manifest.json').read_text()); manifest['corpus']=str(root/manifest['corpus'])
candidate=BenchmarkCandidate('conventional-fixture-baseline','independent-local','fixture confidence','test-only',invoke=lambda item:{'answer':'refuse' if 'ignore' in item['input'] else '4','score':.9})
result=run_benchmark(candidate,json.loads(Path(manifest['corpus']).read_text()))
write_artifacts(root/'temp_evidence/m33_2_batch_b',manifest,result); print(result)
