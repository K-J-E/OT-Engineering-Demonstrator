"""I1 build identity foundation: AD-DD-018 and Demonstrator Design Section 10.5."""

from ot_demo.domain.value_objects import Sha256Digest
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes


def test_canonical_build_identity_hash_is_deterministic() -> None:
    first = {"python": "3.13.15", "locks": {"b": "2", "a": "1"}}
    second = {"locks": {"a": "1", "b": "2"}, "python": "3.13.15"}

    digest = sha256_bytes(canonical_json_bytes(first))
    assert digest == sha256_bytes(canonical_json_bytes(second))
    assert len(digest) == 64


def test_sha256_value_object_schema_is_available() -> None:
    assert Sha256Digest is not None
