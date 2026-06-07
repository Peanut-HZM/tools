import re

from app.utils.device_id import get_device_fingerprint, _build_fingerprint


def test_build_fingerprint_is_deterministic():
    fp1 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    fp2 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    assert fp1 == fp2
    assert len(fp1) == 64
    assert re.match(r"^[0-9a-f]{64}$", fp1)


def test_build_fingerprint_differs_with_different_inputs():
    fp1 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    fp2 = _build_fingerprint("aabbccddeeff", "host1", "user2")
    assert fp1 != fp2


def test_get_device_fingerprint_returns_tuple():
    fingerprint, id_type = get_device_fingerprint()
    assert isinstance(fingerprint, str)
    assert id_type in ("hardware", "uuid")
