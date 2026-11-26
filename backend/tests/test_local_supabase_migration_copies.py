from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
EXPECTED = [
    ("20261119000100_analyses.sql", "001_analyses.sql"),
    ("20261119000200_context.sql", "002_context.sql"),
    ("20261119000300_evidence_snapshots.sql", "003_evidence_snapshots.sql"),
    ("20261119000400_claim_evidence.sql", "004_claim_evidence.sql"),
    ("20261119000500_evidence_comparison_dedup.sql", "005_evidence_comparison_dedup.sql"),
]


def test_cli_migrations_are_byte_identical_and_ordered_copies():
    names = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    assert names == [cli_name for cli_name, _ in EXPECTED]
    for cli_name, source_name in EXPECTED:
        assert (MIGRATIONS / cli_name).read_bytes() == (ROOT / "backend" / "sql" / source_name).read_bytes()
