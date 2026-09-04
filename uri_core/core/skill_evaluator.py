import re
from typing import Any, Dict, List, Optional, Tuple

_TOKEN_RE = re.compile(r'[a-z0-9]+')

# Registry categories that represent routable capabilities.
ROUTABLE_CAPABILITY_CATEGORIES = frozenset({
    'uri_core_capability',
    'on_demand_skill',
    'integration',
    'development',
    'skill_optimization',
})

# Categories excluded from normal capability selection.
NON_ROUTABLE_CATEGORIES = frozenset({
    'model_provider',
    'model_infrastructure',
    'hermes_specialist',
    'specialized',
})


class SkillEvaluator:
    """
    Deterministic skill evaluator.

    Determines which available capability/skill is appropriate for a user
    goal using:
    - user request
    - task/intent information
    - compact context from ContextBudget
    - registry metadata

    It never executes a capability, never authorizes side effects, and
    never invents capabilities absent from the registry.
    """

    def __init__(
        self,
        registry_items: Optional[List[Dict]] = None,
        context_budget_output: Optional[Dict] = None,
    ):
        self._registry_items = list(registry_items or [])
        self._context_budget_output = context_budget_output or {}

    # ------------------------------------------------------------------
    # Public evaluation API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        user_request: str,
        intent: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate available capabilities against a user request.

        Returns a deterministic evaluation result with:
        - evaluated_at timestamp
        - request summary
        - ranked candidates
        - best match (if any suitable)
        - routing recommendation
        - classification summary
        - capability gap flag
        """
        if not isinstance(user_request, str) or not user_request.strip():
            return self._empty_evaluation(user_request)

        signal_words = self._extract_signal_words(user_request, intent)
        candidates = self._score_candidates(signal_words, intent)
        ranked = self._rank_candidates(candidates)
        selected = self._select_top_candidates(ranked, context)
        best = self._determine_best(selected)

        return {
            'evaluated_at': self._utc_now(),
            'request': {
                'user_request': user_request,
                'signal_word_count': len(signal_words),
                'intent_present': isinstance(intent, dict),
            },
            'candidates': selected,
            'best_match': best,
            'routing_recommendation': self._build_routing_recommendation(best, selected),
            'classification_summary': self._build_classification_summary(selected),
            'has_suitable_capability': best is not None,
            'capability_gap': best is None,
        }

    def evaluate_from_context_budget(
        self,
        user_request: str,
        context_budget_output: Dict,
        intent: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate using pre-filtered ContextBudget output.

        This enables the pipeline: ContextBudget → SkillEvaluator.
        Only the compact, relevant capabilities are evaluated.
        """
        candidates = context_budget_output.get('capabilities', [])
        optimization = context_budget_output.get('optimization_candidates', [])

        if not isinstance(candidates, list):
            candidates = []
        if not isinstance(optimization, list):
            optimization = []

        combined = list(candidates) + list(optimization)
        signal_words = self._extract_signal_words(user_request, intent)

        scored = []
        for item in combined:
            score = self._score_single_item(item, signal_words)
            scored.append((score, item))

        scored.sort(key=lambda p: (-p[0], p[1].get('name', '').lower()))
        selected = [item for _, item in scored if item.get('name')]

        best_candidate = selected[0] if selected else None
        return {
            'evaluated_at': self._utc_now(),
            'request': {
                'user_request': user_request,
                'source': 'context_budget',
                'signal_word_count': len(signal_words),
            },
            'candidates': selected,
            'best_match': best_candidate,
            'routing_recommendation': self._build_routing_recommendation(best_candidate, selected),
            'classification_summary': self._build_classification_summary(selected),
            'has_suitable_capability': bool(best_candidate),
            'capability_gap': not bool(best_candidate),
        }

    # ------------------------------------------------------------------
    # Signal extraction
    # ------------------------------------------------------------------

    def _extract_signal_words(self, user_request: str, intent: Optional[Dict]) -> set:
        parts = [user_request.lower()]
        if isinstance(intent, dict):
            for key in ('task_type', 'domain', 'requested_output'):
                val = intent.get(key)
                if isinstance(val, str):
                    parts.append(val.lower())
            entities = intent.get('entities')
            if isinstance(entities, list):
                for ent in entities:
                    if isinstance(ent, str):
                        parts.append(ent.lower())
                    elif isinstance(ent, dict):
                        for v in ent.values():
                            if isinstance(v, str):
                                parts.append(v.lower())
        combined = ' '.join(parts)
        return {
            w
            for w in _TOKEN_RE.findall(combined)
            if len(w) >= 3
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_single_item(self, item: Dict, signal_words: set) -> float:
        category = item.get('category', '')
        if category in NON_ROUTABLE_CATEGORIES:
            return 0.0

        name = (item.get('name') or '').lower()
        purpose = (item.get('purpose') or '').lower()

        item_text = f"{name} {purpose}"
        item_words = set(_TOKEN_RE.findall(item_text))
        overlap = len(signal_words & item_words)

        score = overlap * 20.0

        # Small category weighting so a relevant on_demand_skill can
        # compete with a URI core item when the overlap is equal.
        if category == 'uri_core_capability':
            score += 3.0
        elif category == 'on_demand_skill':
            score += 2.0
        elif category == 'skill_optimization':
            score += 2.0
            if 'pre_reasoning' in (item.get('invocation_conditions') or []):
                if self._is_optimization_relevant(item, signal_words):
                    score += 15.0
        elif category == 'integration':
            score += 1.5
        elif category == 'development':
            score += 1.0

        if purpose and (set(_TOKEN_RE.findall(purpose)) & signal_words):
            score += 20.0

        risk = item.get('execution_risk', 'unknown')
        if risk == 'high':
            score -= 25.0
        elif risk == 'variable':
            score -= 5.0

        return max(0.0, score)

    def _is_relevant_for(self, item: Dict, signal_words: set) -> bool:
        name = (item.get('name') or '').lower()
        purpose = (item.get('purpose') or '').lower()
        item_words = set(_TOKEN_RE.findall(f"{name} {purpose}"))
        return bool(signal_words & item_words)

    def _is_optimization_relevant(self, item: Dict, signal_words: set) -> bool:
        """
        Optimization skills like Defuddle are relevant when the current
        request signals a heavy reasoning/context workload.

        Determined from the request, not from the item's own metadata.
        """
        heavy_signals = {
            'context',
            'long',
            'large',
            'summarize',
            'summarization',
            'reasoning',
            'complex',
            'reduce',
            'optimize',
            'token',
        }
        return bool(signal_words & heavy_signals)

    def _score_candidates(self, signal_words: set, intent: Optional[Dict]) -> List[Tuple[float, Dict]]:
        results = []
        for item in self._registry_items:
            if not isinstance(item, dict):
                continue
            cat = item.get('category', '')
            if cat in NON_ROUTABLE_CATEGORIES:
                continue
            score = self._score_single_item(item, signal_words)
            results.append((score, item))
        return results

    def _rank_candidates(self, scored: List[Tuple[float, Dict]]) -> List[Dict]:
        scored.sort(key=lambda p: (-p[0], p[1].get('name', '').lower()))
        return [
            dict(item, _eval_score=score)
            for score, item in scored
        ]

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_top_candidates(
        self,
        ranked: List[Dict],
        context: Optional[Dict] = None,
    ) -> List[Dict]:
        max_items = context.get('max_capabilities', 20) if isinstance(context, dict) else 20
        max_score = context.get('min_score', 10) if isinstance(context, dict) else 10

        selected = []
        for item in ranked:
            score = self._extract_score(item)
            if score >= max_score or len(selected) < 5:
                selected.append(item)
            if len(selected) >= max_items:
                break
        return selected

    def _extract_score(self, item: Dict) -> float:
        if not isinstance(item, dict):
            return 0.0
        sc = item.get('_eval_score')
        if isinstance(sc, (int, float)):
            return float(sc)
        return 0.0

    # ------------------------------------------------------------------
    # Best match determination
    # ------------------------------------------------------------------

    def _determine_best(self, candidates: List[Dict]) -> Optional[Dict]:
        if not candidates:
            return None
        best = None
        best_score = -1
        for item in candidates:
            score = self._extract_score(item)
            if score > best_score:
                best_score = score
                best = item
        if best_score < 10:
            return None
        return best

    # ------------------------------------------------------------------
    # Routing recommendation
    # ------------------------------------------------------------------

    def _build_routing_recommendation(
        self,
        best: Optional[Dict],
        candidates: List[Dict],
    ) -> Dict[str, Any]:
        if best is None:
            return {
                'destination': 'none',
                'reason': 'No suitable capability found for this request.',
                'requires_user_clarification': True,
            }

        category = best.get('category', '')
        name = best.get('name', '')

        if category == 'uri_core_capability':
            return {
                'destination': 'uri_runtime',
                'capability': name,
                'reason': f'URI-owned capability {name} is appropriate for this request.',
                'requires_user_clarification': False,
            }
        elif category == 'on_demand_skill':
            return {
                'destination': 'hermes',
                'capability': name,
                'reason': f'Hermes skill {name} may assist with this request.',
                'requires_user_clarification': False,
            }
        elif category == 'skill_optimization':
            return {
                'destination': 'optimization',
                'capability': name,
                'reason': f'Optimization capability {name} can improve context efficiency.',
                'requires_user_clarification': False,
            }
        elif category == 'integration':
            return {
                'destination': 'hermes',
                'capability': name,
                'reason': f'Integration skill {name} may be relevant.',
                'requires_user_clarification': False,
            }
        elif category == 'development':
            return {
                'destination': 'hermes',
                'capability': name,
                'reason': f'Development tool {name} may assist.',
                'requires_user_clarification': False,
            }
        else:
            return {
                'destination': 'review_required',
                'reason': f'Unexpected category {category} for capability {name}. Manual review needed.',
                'requires_user_clarification': True,
            }

    # ------------------------------------------------------------------
    # Classification summary
    # ------------------------------------------------------------------

    def _build_classification_summary(self, candidates: List[Dict]) -> Dict[str, int]:
        summary = {
            'uri_core_capability': 0,
            'on_demand_skill': 0,
            'skill_optimization': 0,
            'integration': 0,
            'development': 0,
            'excluded_non_routable': 0,
            'total_registry_items': 0,
        }
        total = 0
        for item in self._registry_items:
            if not isinstance(item, dict):
                continue
            total += 1
            cat = item.get('category', '')
            if cat in ROUTABLE_CAPABILITY_CATEGORIES:
                summary[cat] = summary.get(cat, 0) + 1
            else:
                summary['excluded_non_routable'] += 1
        summary['total_registry_items'] = total
        return summary

    # ------------------------------------------------------------------
    # Empty/low-information handling
    # ------------------------------------------------------------------

    def _empty_evaluation(self, user_request: str) -> Dict[str, Any]:
        return {
            'evaluated_at': self._utc_now(),
            'request': {
                'user_request': user_request,
                'signal_word_count': 0,
                'intent_present': False,
            },
            'candidates': [],
            'best_match': None,
            'routing_recommendation': {
                'destination': 'none',
                'reason': 'Request could not be evaluated (empty or invalid).',
                'requires_user_clarification': True,
            },
            'classification_summary': {
                'uri_core_capability': 0,
                'on_demand_skill': 0,
                'skill_optimization': 0,
                'integration': 0,
                'development': 0,
                'excluded_non_routable': 0,
                'total_registry_items': len(self._registry_items),
            },
            'has_suitable_capability': False,
            'capability_gap': True,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _utc_now(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def evaluate_with_score_annotation(
        self,
        user_request: str,
        intent: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate with per-candidate scores annotated in the result.
        Used by tests to verify scoring logic.
        """
        result = self.evaluate(user_request, intent)
        for candidate in result.get('candidates', []):
            if not isinstance(candidate, dict):
                continue
            candidate['_eval_score'] = self._score_single_item(
                candidate,
                self._extract_signal_words(user_request, intent),
            )
        return result
