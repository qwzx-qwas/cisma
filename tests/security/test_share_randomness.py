import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.crypto.secret_sharing import split_secret


def test_multiple_splits_of_same_secret_usually_produce_different_shares() -> None:
    first = split_secret(42)
    second = split_secret(42)
    third = split_secret(42)

    assert len({tuple(first), tuple(second), tuple(third)}) > 1


def test_secret_sharing_uses_secrets_randbelow_not_insecure_random_sources() -> None:
    source = Path("src/secure_agg/crypto/secret_sharing.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    calls = {
        ".".join(
            part
            for part in [
                getattr(getattr(node.func, "value", None), "id", None),
                getattr(node.func, "attr", None),
            ]
            if part
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "secrets.randbelow" in calls
    assert "random.randint" not in calls
    assert "numpy.random" not in source
