"""M35 URIv1 -- A2.8K: rar_l5_experimental.py unit tests.

Per plan §3/§9: (1) flag-off equivalence to baseline
`resolve_rar_deterministic_extended`, checked here against every existing
A2.5 fixture corpus and the RC1-4 legacy unit-test vectors, plus the frozen
S-D battery; (2) one mechanism test per hypothesis, written from the frozen
§8 semantics (not from observed output); (3) DX-1 isolation (no effect when
`dx1_tie_ids` is empty). No existing file is modified; this is a new,
additive test module (plan §3 deliverable 4).
"""

from __future__ import annotations

import unittest

from uri_v1.turn.rar_contracts import (
    RARCandidate,
    RAREvidence,
    RAROutcome,
    RARQuery,
)
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
from uri_v1.turn.rar_l5_experimental import resolve_rar_l5_experimental
from uri_v1.turn.rar_fixtures import get_rar_diagnostic_fixtures
from uri_v1.turn.rar_adversarial_fixtures import get_rar_adversarial_fixtures
from uri_v1.turn.rar_l5_diagnostic_fixtures import get_l5_diagnostic_fixtures


def _decision_tuple(trace):
    return (
        trace.resolution.outcome,
        trace.resolution.candidate_id,
        frozenset(trace.resolution.ambiguous_candidate_ids),
    )


class FlagOffEquivalenceTests(unittest.TestCase):
    """§9.2 / §12: with h1=h2=h3=False and dx1_tie_ids empty, the
    experimental resolver must be decision-identical to baseline on every
    fixture corpus available to unit tests (S-D here; S-A/S-B/S-C/S-E are
    checked at corpus scale by the battery script)."""

    def _assert_all_fixtures_equivalent(self, fixtures):
        for fix in fixtures:
            with self.subTest(fixture_id=fix.id):
                baseline_trace = resolve_rar_deterministic_extended(fix.query)
                experimental_trace = resolve_rar_l5_experimental(fix.query)
                self.assertEqual(
                    _decision_tuple(baseline_trace),
                    _decision_tuple(experimental_trace),
                    f"Flag-off divergence on {fix.id}",
                )

    def test_flag_off_equivalent_on_diagnostic_fixtures(self):
        self._assert_all_fixtures_equivalent(get_rar_diagnostic_fixtures())

    def test_flag_off_equivalent_on_adversarial_fixtures(self):
        self._assert_all_fixtures_equivalent(get_rar_adversarial_fixtures())

    def test_flag_off_equivalent_on_sd_fixtures(self):
        self._assert_all_fixtures_equivalent(get_l5_diagnostic_fixtures())

    def test_flag_off_equivalent_on_rc1_latest_case(self):
        c0 = RARCandidate(id="order_latest", title="Office Order 2026", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="order_prev", title="Office Order 2025", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest office order",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        self.assertEqual(
            _decision_tuple(resolve_rar_deterministic_extended(query)),
            _decision_tuple(resolve_rar_l5_experimental(query)),
        )

    def test_flag_off_equivalent_on_rc4_attachment_case(self):
        c_att = RARCandidate(id="att_scan", title="Scanned_Form.pdf", candidate_type="document", is_attachment=True)
        c_doc1 = RARCandidate(id="repo_doc1", title="Policy_Draft.pdf", candidate_type="document")
        c_doc2 = RARCandidate(id="repo_doc2", title="Guidelines.pdf", candidate_type="document")
        query = RARQuery(
            reference_expression="the attachment",
            candidates=(c_att, c_doc1, c_doc2),
            local_evidence=RAREvidence(),
        )
        self.assertEqual(
            _decision_tuple(resolve_rar_deterministic_extended(query)),
            _decision_tuple(resolve_rar_l5_experimental(query)),
        )

    def test_flag_off_dx1_tie_ids_present_is_still_a_no_op_when_h1h2h3_off(self):
        """dx1_tie_ids alone (no hypothesis flags) is DX-1's own variant, not
        a flag-off run -- but DX-1 with an EMPTY tie set must be a true
        no-op against baseline (isolation requirement, plan §3 deliverable 4)."""
        c0 = RARCandidate(id="a", title="Doc A", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="b", title="Doc B", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest doc",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        experimental = resolve_rar_l5_experimental(query, dx1_tie_ids=frozenset())
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(experimental))


class H1MechanismTests(unittest.TestCase):
    """H1: a Level-5 single-candidate binding requires >=1 substantive token
    (excluding stopwords/pronouns/generic-type-words/target-type/R3(a)
    recency vocabulary); on failure it falls through rather than binding."""

    def test_h1_blocks_zero_evidence_latest_binding(self):
        c0 = RARCandidate(id="new", title="X", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="old", title="Y", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest one",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        self.assertEqual(baseline.resolution.outcome, RAROutcome.RESOLVED)
        h1_trace = resolve_rar_l5_experimental(query, h1=True)
        self.assertNotEqual(h1_trace.rule_used.value, "TEMPORAL_RELATION")

    def test_h1_preserves_binding_with_substantive_evidence(self):
        c0 = RARCandidate(id="inv_new", title="Invoice_04.pdf", candidate_type="document", recency_rank=0, domain_tags=("invoice",))
        c1 = RARCandidate(id="inv_old", title="Invoice_03.pdf", candidate_type="document", recency_rank=1, domain_tags=("invoice",))
        query = RARQuery(
            reference_expression="the latest invoice",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h1_trace = resolve_rar_l5_experimental(query, h1=True)
        self.assertEqual(h1_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(h1_trace.resolution.candidate_id, "inv_new")


class H2MechanismTests(unittest.TestCase):
    """H2: explicit attachment semantics run Level 5.5's attachment-set
    evaluation before Level 5's ordinal branches."""

    def test_h2_ambiguous_attachments_precede_recency_binding(self):
        c0 = RARCandidate(id="att_x", title="Photo_X.jpg", candidate_type="document", recency_rank=0, is_attachment=True)
        c1 = RARCandidate(id="att_y", title="Photo_Y.jpg", candidate_type="document", recency_rank=1, is_attachment=True)
        query = RARQuery(
            reference_expression="the latest attachment",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        self.assertEqual(baseline.resolution.outcome, RAROutcome.RESOLVED)  # baseline commits via recency (the ICB class A mechanism)
        h2_trace = resolve_rar_l5_experimental(query, h2=True)
        self.assertEqual(h2_trace.resolution.outcome, RAROutcome.AMBIGUOUS)
        self.assertEqual(h2_trace.rule_used.value, "CURRENT_ATTACHMENT")

    def test_h2_does_not_affect_non_attachment_references(self):
        c0 = RARCandidate(id="new", title="Report_2026.pdf", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="old", title="Report_2025.pdf", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest report",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h2_trace = resolve_rar_l5_experimental(query, h2=True)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h2_trace))


class H3MechanismTests(unittest.TestCase):
    """H3: Level-5's ordinal branches operate only over candidates lexically
    compatible with the reference's substantive tokens."""

    def test_h3_domain_relative_rank_resolves_the_singleton_compatible_candidate(self):
        """A2.8K-R1 repair R1-A (independent audit §10 / §22.1): once H3
        restricts the domain to the candidates compatible with "board
        minutes", the surviving 'minutes' candidate must be evaluated at
        its DOMAIN-RELATIVE rank (0 -- it is the only, and therefore latest,
        member of its own domain), not its original global rank (1, which
        made it look non-latest against the globally-newer but
        domain-incompatible 'agenda'). H3 must both remove the ICB (never
        return 'agenda') AND achieve the intended correct binding to
        'minutes' -- prior to this repair it fell through to an
        uninformative UNKNOWN instead (see the independent final audit,
        `docs/plans/M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md` §10)."""
        agenda = RARCandidate(id="agenda", title="October_Agenda.pdf", candidate_type="document", recency_rank=0)
        minutes = RARCandidate(id="minutes", title="Board_Minutes_Sep.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        query = RARQuery(
            reference_expression="the latest board minutes",
            candidates=(agenda, minutes),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        self.assertEqual(baseline.resolution.candidate_id, "agenda")  # baseline ICB: picks pool-wide newest
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(h3_trace.resolution.candidate_id, "minutes")

    def test_h3_rank_with_gaps_in_filtered_domain(self):
        """R1-A's illustrative requirement: global ranks A=0,B=1,C=2,D=3;
        filtering to {B, D} (a gapped subset) must treat B as domain-rank 0
        and D as domain-rank 1, resolving 'latest' (domain-relative rank 0)
        to B, not to D (D's global rank) and not by falling through."""
        a = RARCandidate(id="a", title="Alpha_Report.pdf", candidate_type="document", recency_rank=0)
        b = RARCandidate(id="b", title="Board_Report.pdf", candidate_type="document", recency_rank=1, domain_tags=("board",))
        c = RARCandidate(id="c", title="Gamma_Report.pdf", candidate_type="document", recency_rank=2)
        d = RARCandidate(id="d", title="Board_Older_Report.pdf", candidate_type="document", recency_rank=3, domain_tags=("board",))
        query = RARQuery(
            reference_expression="the latest board report",
            candidates=(a, b, c, d),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(h3_trace.resolution.candidate_id, "b")

    def test_h3_domain_relative_rank_still_detects_ties_within_domain(self):
        """Two domain-compatible candidates genuinely tied at the same
        global rank must still be AMBIGUOUS after domain-relative
        re-ranking (dense re-ranking preserves ties; it does not manufacture
        a winner)."""
        agenda = RARCandidate(id="agenda", title="October_Agenda.pdf", candidate_type="document", recency_rank=0)
        minutes_a = RARCandidate(id="minutes_a", title="Board_Minutes_A.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        minutes_b = RARCandidate(id="minutes_b", title="Board_Minutes_B.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        query = RARQuery(
            reference_expression="the latest board minutes",
            candidates=(agenda, minutes_a, minutes_b),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.AMBIGUOUS)
        self.assertEqual(set(h3_trace.resolution.ambiguous_candidate_ids), {"minutes_a", "minutes_b"})

    def test_h3_domain_relative_rank_deterministic_across_repeated_calls(self):
        agenda = RARCandidate(id="agenda", title="October_Agenda.pdf", candidate_type="document", recency_rank=0)
        minutes = RARCandidate(id="minutes", title="Board_Minutes_Sep.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        query = RARQuery(
            reference_expression="the latest board minutes",
            candidates=(agenda, minutes),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        results = [resolve_rar_l5_experimental(query, h3=True).resolution.candidate_id for _ in range(5)]
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0], "minutes")

    def test_h3_no_regression_when_filtering_preserves_contiguous_domain(self):
        """When the compatible domain happens to already be the full,
        contiguously-ranked pool, domain-relative ranks must equal the
        original ranks (no behaviour change from treating the whole pool as
        its own domain)."""
        new = RARCandidate(id="new", title="Invoice_Latest.pdf", candidate_type="document", recency_rank=0, domain_tags=("invoice",))
        old = RARCandidate(id="old", title="Invoice_Older.pdf", candidate_type="document", recency_rank=1, domain_tags=("invoice",))
        query = RARQuery(
            reference_expression="the latest invoice",
            candidates=(new, old),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h3_trace))

    def test_h3_empty_domain_falls_through_rather_than_returning_ambiguous_on_full_pool(self):
        """St/Street known-limitation shape: H3's substantive-token domain
        check is a literal token match ('st' != 'street'), so the domain is
        empty even though the full pool DOES carry real ordering metadata.
        H3 must fall through (never bind on this branch), not answer with
        baseline's unrelated "no ordering metadata" abstention over the
        full pool."""
        c_street = RARCandidate(id="street", title="Main Street Annual Report.pdf", candidate_type="document", recency_rank=0)
        c_other = RARCandidate(id="other", title="Oak Avenue Report.pdf", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest report on Main St",
            candidates=(c_street, c_other),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        self.assertEqual(baseline.resolution.candidate_id, "street")  # baseline gets it right by accident (rank-only)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        # H3 must not silently reuse baseline's INSUFFICIENT_METADATA path
        # over the full pool -- it must fall through to Level 6, which
        # (unmodified) cannot resolve "st"/"street" either -> UNKNOWN.
        # Losing this bind is the disclosed St/Street brittleness (plan §5).
        self.assertNotEqual(h3_trace.failure_class, "INSUFFICIENT_METADATA")
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.UNKNOWN)

    def test_h3_no_restriction_with_zero_substantive_tokens(self):
        c0 = RARCandidate(id="new", title="X", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="old", title="Y", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest one",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h3_trace))


class H3ActivationBoundaryTests(unittest.TestCase):
    """A2.8K-R2 repair: domain-relative re-ranking must activate only when
    H3's lexical filter GENUINELY narrows the candidate domain (membership,
    not list length). An unnarrowed domain -- including the "no substantive
    tokens" case -- must reproduce baseline Level-5 exactly: original ranks,
    the `has_ordering` gate, and baseline's abstention behaviour. The R1
    independent re-audit found this activation boundary missing:
    `test_rc1_current_conflicting_no_rank0_abstains`-shaped queries were
    incorrectly RESOLVED by R1 because dense re-ranking fired even though
    nothing had been filtered out."""

    def test_genuinely_narrowed_domain_still_reranks(self):
        """Case A (directive): full pool A=0,B=1,C=2,D=3; H3 retains {B,D}
        (a strict subset) -> genuine narrowing -> domain-relative ranks
        B=0, D=1 -> 'latest' resolves to B. Same case as the existing
        gapped-rank test; kept here as an explicit activation-boundary
        positive control."""
        a = RARCandidate(id="a", title="Alpha_Report.pdf", candidate_type="document", recency_rank=0)
        b = RARCandidate(id="b", title="Board_Report.pdf", candidate_type="document", recency_rank=1, domain_tags=("board",))
        c = RARCandidate(id="c", title="Gamma_Report.pdf", candidate_type="document", recency_rank=2)
        d = RARCandidate(id="d", title="Board_Older_Report.pdf", candidate_type="document", recency_rank=3, domain_tags=("board",))
        query = RARQuery(
            reference_expression="the latest board report",
            candidates=(a, b, c, d),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(h3_trace.resolution.candidate_id, "b")

    def test_unchanged_domain_preserves_baseline_no_rank0_abstention(self):
        """Case B (directive): pool B(rank1), C(rank2); H3's lexical filter
        retains BOTH (domain unchanged) -> must NOT re-rank to B=0,C=1 ->
        must preserve baseline's no-rank-0 abstention. Exact shape of
        `test_rc1_current_conflicting_no_rank0_abstains`."""
        b = RARCandidate(id="doc_r1", title="Report 2025", candidate_type="document", recency_rank=1)
        c = RARCandidate(id="doc_r2", title="Report 2024", candidate_type="document", recency_rank=2)
        query = RARQuery(
            reference_expression="the current report",
            candidates=(b, c),
            local_evidence=RAREvidence(recency_hint="current"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertNotEqual(baseline.resolution.outcome, RAROutcome.RESOLVED)
        self.assertNotEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h3_trace))

    def test_unchanged_domain_the_current_document_case(self):
        """The directive's own second named example: 'the current document'
        with no lexical restriction narrowing the domain must not fabricate
        a rank-0 winner."""
        d1 = RARCandidate(id="doc1", title="Policy.pdf", candidate_type="document", recency_rank=1)
        d2 = RARCandidate(id="doc2", title="Policy_Old.pdf", candidate_type="document", recency_rank=2)
        query = RARQuery(
            reference_expression="the current document",
            candidates=(d1, d2),
            local_evidence=RAREvidence(recency_hint="current"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h3_trace))

    def test_no_substantive_tokens_preserves_baseline(self):
        """Case C (directive): zero substantive tokens -> `_h3_domain`
        already returns the full pool unchanged -> must not be treated as
        successful narrowing, and must reproduce baseline exactly (this
        already existed as a flag-off-style check; re-asserted here as an
        explicit activation-boundary case)."""
        c0 = RARCandidate(id="new", title="X", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="old", title="Y", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest one",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(_decision_tuple(baseline), _decision_tuple(h3_trace))

    def test_rc1_current_conflicting_no_rank0_abstains_under_h3(self):
        """The exact regression the R1 independent re-audit named: the
        legacy RC-1 stage-4 fixture must abstain under H3 exactly as it
        does under baseline."""
        c1 = RARCandidate(id="doc_r1", title="Report 2025", candidate_type="document", recency_rank=1)
        c2 = RARCandidate(id="doc_r2", title="Report 2024", candidate_type="document", recency_rank=2)
        query = RARQuery(
            reference_expression="the current report",
            candidates=(c1, c2),
            local_evidence=RAREvidence(recency_hint="current"),
        )
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertNotEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)

    def test_genuine_narrowing_still_deterministic_across_repeated_calls(self):
        a = RARCandidate(id="a", title="Alpha_Report.pdf", candidate_type="document", recency_rank=0)
        b = RARCandidate(id="b", title="Board_Report.pdf", candidate_type="document", recency_rank=1, domain_tags=("board",))
        d = RARCandidate(id="d", title="Board_Older_Report.pdf", candidate_type="document", recency_rank=3, domain_tags=("board",))
        query = RARQuery(
            reference_expression="the latest board report",
            candidates=(a, b, d),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        results = [resolve_rar_l5_experimental(query, h3=True).resolution.candidate_id for _ in range(5)]
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0], "b")

    def test_unchanged_domain_still_deterministic_across_repeated_calls(self):
        b = RARCandidate(id="doc_r1", title="Report 2025", candidate_type="document", recency_rank=1)
        c = RARCandidate(id="doc_r2", title="Report 2024", candidate_type="document", recency_rank=2)
        query = RARQuery(
            reference_expression="the current report",
            candidates=(b, c),
            local_evidence=RAREvidence(recency_hint="current"),
        )
        results = [resolve_rar_l5_experimental(query, h3=True).resolution.outcome for _ in range(5)]
        self.assertEqual(len(set(results)), 1)
        self.assertNotEqual(results[0], RAROutcome.RESOLVED)

    def test_sd_c_02_and_nb_d_01_shape_still_resolve_after_r2(self):
        """R1 non-regression (directive Phase 3): the genuinely-narrowed
        SD-C-02 shape must still resolve correctly after the R2 activation
        boundary is added."""
        agenda = RARCandidate(id="agenda", title="October_Agenda.pdf", candidate_type="document", recency_rank=0)
        minutes = RARCandidate(id="minutes", title="Board_Minutes_Sep.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        query = RARQuery(
            reference_expression="the latest board minutes",
            candidates=(agenda, minutes),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h3_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(h3_trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(h3_trace.resolution.candidate_id, "minutes")


class H4CombinationTests(unittest.TestCase):
    """H4 = H1 + H2 + H3, unmodified relative to isolated definitions."""

    def test_h4_combines_all_three_mechanisms(self):
        agenda = RARCandidate(id="agenda", title="October_Agenda.pdf", candidate_type="document", recency_rank=0)
        minutes = RARCandidate(id="minutes", title="Board_Minutes_Sep.pdf", candidate_type="document", recency_rank=1, domain_tags=("minutes",))
        query = RARQuery(
            reference_expression="the latest board minutes",
            candidates=(agenda, minutes),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        h4_trace = resolve_rar_l5_experimental(query, h1=True, h2=True, h3=True)
        h3_only_trace = resolve_rar_l5_experimental(query, h3=True)
        self.assertEqual(_decision_tuple(h4_trace), _decision_tuple(h3_only_trace))


class DX1IsolationTests(unittest.TestCase):
    """DX-1: empty tie set is a true no-op; a non-empty tie set can convert
    a wrong confident binding into a safe AMBIGUOUS (isolating rank-clock
    causation from precedence, plan §2 DX-1 row)."""

    def test_dx1_empty_tie_set_is_noop(self):
        c0 = RARCandidate(id="a", title="Doc A", candidate_type="document", recency_rank=0)
        c1 = RARCandidate(id="b", title="Doc B", candidate_type="document", recency_rank=1)
        query = RARQuery(
            reference_expression="the latest doc",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        no_dx1 = resolve_rar_l5_experimental(query)
        empty_dx1 = resolve_rar_l5_experimental(query, dx1_tie_ids=frozenset())
        self.assertEqual(_decision_tuple(no_dx1), _decision_tuple(empty_dx1))

    def test_dx1_tie_converts_wrong_binding_to_ambiguous(self):
        c0 = RARCandidate(id="x", title="Photo_X.jpg", candidate_type="document", recency_rank=0, is_attachment=True)
        c1 = RARCandidate(id="y", title="Photo_Y.jpg", candidate_type="document", recency_rank=1, is_attachment=True)
        query = RARQuery(
            reference_expression="the latest attachment",
            candidates=(c0, c1),
            local_evidence=RAREvidence(recency_hint="latest"),
        )
        baseline = resolve_rar_deterministic_extended(query)
        self.assertEqual(baseline.resolution.outcome, RAROutcome.RESOLVED)
        dx1_trace = resolve_rar_l5_experimental(query, dx1_tie_ids=frozenset({"x", "y"}))
        self.assertEqual(dx1_trace.resolution.outcome, RAROutcome.AMBIGUOUS)


if __name__ == "__main__":
    unittest.main()
