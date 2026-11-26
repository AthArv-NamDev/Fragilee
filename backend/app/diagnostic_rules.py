"""Versioned metadata for the conservative Phase 2B diagnostic library.

Rules intentionally describe only mechanisms supported by the Phase 2A profile
contract. Missing profile fields are information gaps, never negative findings.
"""

ENGINE_VERSION = "2b.1"

RULES = {
    "market.target_customer_clarity": {
        "version": "1.0.0", "category": "market_customer_validation",
        "title": "Target customer definition", "mechanism": "An unclear target customer makes it harder to test whether a specific group has the stated problem.",
    },
    "market.discovery_activity": {
        "version": "1.0.0", "category": "market_customer_validation",
        "title": "Customer discovery evidence", "mechanism": "Discovery activity can inform problem understanding, but activity alone does not establish demand.",
    },
    "market.willingness_to_pay": {
        "version": "1.0.0", "category": "market_customer_validation",
        "title": "Willingness-to-pay evidence", "mechanism": "Stated interest and observed payment are different signals; the profile does not establish repeatable demand.",
    },
    "market.sizing_basis": {
        "version": "1.0.0", "category": "market_customer_validation",
        "title": "Market-sizing basis", "mechanism": "A market-size estimate is more interpretable when its population, geography, period, and calculation basis are explicit.",
    },
    "economics.contribution_per_transaction": {
        "version": "1.0.0", "category": "unit_economics",
        "title": "Contribution per transaction", "mechanism": "Revenue less directly attributable variable cost indicates whether a transaction contributes toward fixed costs.",
    },
    "economics.cac_payback": {
        "version": "1.0.0", "category": "unit_economics",
        "title": "Customer acquisition payback", "mechanism": "Payback requires acquisition cost and contribution profit for the same customer and period.",
    },
    "traction.retention_cohort": {
        "version": "1.0.0", "category": "retention_traction",
        "title": "Retention evidence", "mechanism": "Retention is interpretable only for a defined customer cohort over a meaningful observation period.",
    },
    "finance.cash_runway": {
        "version": "1.0.0", "category": "funding_runway",
        "title": "Cash runway", "mechanism": "Runway depends on available cash and net cash burn; operating expense alone is not net burn.",
    },
    "marketplace.liquidity": {
        "version": "1.0.0", "category": "marketplace",
        "title": "Marketplace liquidity evidence", "mechanism": "A marketplace needs relevant supply and demand to meet in the same market and period; aggregate counts alone do not prove liquidity.",
    },
    "hardware.production_readiness": {
        "version": "1.0.0", "category": "hardware_deep_tech",
        "title": "Production readiness", "mechanism": "Minimum orders, tooling, lead times, and supplier concentration can create cash and delivery dependencies.",
    },
    "team.capability_gaps": {
        "version": "1.0.0", "category": "team_execution",
        "title": "Founder-identified capability gaps", "mechanism": "An unaddressed capability gap may constrain execution of a stated milestone.",
    },
    "operations.regulatory_pathway": {
        "version": "1.0.0", "category": "regulatory_operations",
        "title": "Regulatory pathway clarity", "mechanism": "Where regulatory obligations apply, unresolved pathway or licensing requirements can affect launch scope and timing.",
    },
    "operations.critical_dependencies": {
        "version": "1.0.0", "category": "regulatory_operations",
        "title": "Critical operational dependencies", "mechanism": "A critical supplier, platform, or infrastructure dependency may constrain continuity if it is unavailable.",
    },
}
