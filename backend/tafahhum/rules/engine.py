"""The scholarly rule engine.

Rules are data, not code. They live in the database with their provenance, they
are loaded per query, and the set that fired is recorded so that "why did
Tafahhum retrieve this source?" has an answer that terminates in a citation.

Tier order is absolute: a rule in a lower tier can never relax a constraint set
by a higher one. This is what stops a response-formatting preference from
loosening a source-provenance requirement, which is the direction such systems
usually fail in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg

from tafahhum.core.enums import QueryType, RuleTier


@dataclass(frozen=True)
class Rule:
    rule_key: str
    name: str
    description: str
    tier: RuleTier
    priority: int
    source_book: str
    source_reference: str | None
    verification_status: str
    applies_to: list[QueryType]
    effects: dict[str, Any]
    required_source_slugs: list[str]
    preferred_source_slugs: list[str]
    excluded_source_slugs: list[str]

    @property
    def is_scholarly(self) -> bool:
        """True only for rules that carry a book attribution."""
        return self.source_book != "TAFAHHUM_BASELINE"

    @property
    def provenance(self) -> str:
        if not self.is_scholarly:
            return "Tafahhum baseline (structural; no scholarly claim)"
        ref = self.source_reference or "no reference recorded"
        return f"{self.source_book}, {ref} [{self.verification_status}]"


@dataclass
class RetrievalPlan:
    """The merged effect of every rule that fired."""

    query_type: QueryType
    effects: dict[str, Any] = field(default_factory=dict)
    required_works: list[str] = field(default_factory=list)
    preferred_works: list[str] = field(default_factory=list)
    excluded_works: list[str] = field(default_factory=list)
    applied_rules: list[Rule] = field(default_factory=list)

    #: Effect keys already set by a higher tier, which lower tiers may not touch.
    _locked: set[str] = field(default_factory=set, repr=False)

    @property
    def per_work_cap(self) -> int:
        return int(self.effects.get("per_work_cap", 3))

    @property
    def isolate_named_works(self) -> bool:
        return bool(self.effects.get("isolate_named_works", False))

    @property
    def order_by_death_year(self) -> bool:
        return self.effects.get("order_by") == "author_death_year_hijri"

    def explain(self) -> list[dict[str, str]]:
        """The rule set, with provenance, for the transparency panel."""
        return [
            {
                "rule": r.rule_key,
                "name": r.name,
                "tier": r.tier.value,
                "provenance": r.provenance,
                "scholarly": str(r.is_scholarly),
            }
            for r in self.applied_rules
        ]


def load_rules(conn: psycopg.Connection, query_type: QueryType) -> list[Rule]:
    """Load active rules applying to this query type, in tier then priority order.

    A rule with an empty `applies_to_query_types` applies universally.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            -- The enum array is cast to text[] because psycopg has no adapter
            -- registered for the custom query_type enum.
            SELECT rule_key, name, description, tier::text AS tier, priority,
                   source_book, source_reference,
                   verification_status::text AS verification_status,
                   applies_to_query_types::text[] AS applies_to_query_types,
                   effects, required_source_slugs, preferred_source_slugs,
                   excluded_source_slugs
            FROM scholarly_rule
            WHERE is_active
              AND (cardinality(applies_to_query_types) = 0
                   OR %s = ANY(applies_to_query_types))
            ORDER BY
                array_position(
                    ARRAY['SYSTEM_INTEGRITY','SOURCE_PROVENANCE','SCHOLARLY_METHOD',
                          'QUERY_STRATEGY','EVIDENCE_QUALITY','RESPONSE_STRUCTURE',
                          'LANGUAGE_GENERATION']::text[],
                    tier::text
                ),
                priority
            """,
            (query_type.value,),
        )
        rows = cur.fetchall()

    return [
        Rule(
            rule_key=r["rule_key"],
            name=r["name"],
            description=r["description"],
            tier=RuleTier(r["tier"]),
            priority=r["priority"],
            source_book=r["source_book"],
            source_reference=r["source_reference"],
            verification_status=r["verification_status"],
            applies_to=[QueryType(t) for t in r["applies_to_query_types"]],
            effects=r["effects"] or {},
            required_source_slugs=r["required_source_slugs"] or [],
            preferred_source_slugs=r["preferred_source_slugs"] or [],
            excluded_source_slugs=r["excluded_source_slugs"] or [],
        )
        for r in rows
    ]


def build_plan(rules: list[Rule], query_type: QueryType) -> RetrievalPlan:
    """Merge rules into a plan, honouring tier precedence.

    Rules arrive in tier order. The first rule to set an effect key wins and
    locks it, so a later, lower-tier rule cannot override a higher-tier decision.
    Exclusions are the exception: they accumulate, because excluding a source is
    always a tightening and tightening is never blocked.
    """
    plan = RetrievalPlan(query_type=query_type)

    for rule in rules:
        for key, value in rule.effects.items():
            if key in plan._locked:
                continue
            plan.effects[key] = value
            plan._locked.add(key)

        for slug in rule.required_source_slugs:
            if slug not in plan.required_works:
                plan.required_works.append(slug)
        for slug in rule.preferred_source_slugs:
            if slug not in plan.preferred_works:
                plan.preferred_works.append(slug)
        for slug in rule.excluded_source_slugs:
            if slug not in plan.excluded_works:
                plan.excluded_works.append(slug)

        plan.applied_rules.append(rule)

    return plan


def plan_for(conn: psycopg.Connection, query_type: QueryType) -> RetrievalPlan:
    return build_plan(load_rules(conn, query_type), query_type)
