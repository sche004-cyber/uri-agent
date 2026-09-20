import json
from pathlib import Path
from uri_core.core.edge.adapters.benchmark import BenchmarkCandidate,run_benchmark
def test_proposal_only_harness_measures_and_rejects_host_execution():
 corpus=json.loads(Path('fixtures/m33_2_edge_benchmark/corpus.json').read_text())
 safe=BenchmarkCandidate('local','independent','probability','test',invoke=lambda x:{'answer':'refuse' if 'ignore' in x['input'] else '4','score':.9})
 result=run_benchmark(safe,corpus); assert result.safety=='pass' and result.ece is not None and result.qualification=='QUALIFIED_FOR_COMPARISON'
 bad=BenchmarkCandidate('bad','needle','probability','test',invoke=lambda x:{'answer':'4','score':.9,'host_function':'run'})
 assert run_benchmark(bad,corpus).qualification=='REJECTED'
def test_egress_and_score_semantics_are_fail_closed():
 candidate=BenchmarkCandidate('needle','cactus-compute',None,'unknown',invoke=lambda x:{'answer':'4'})
 assert run_benchmark(candidate,[{'expected':'4'}]).qualification=='REJECTED'
