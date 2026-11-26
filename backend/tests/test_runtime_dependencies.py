from pathlib import Path


def test_httpx_is_pinned_as_a_runtime_dependency():
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    entries = [line.strip().lower() for line in requirements.read_text().splitlines() if line.strip()]

    assert "httpx==0.28.1" in entries
