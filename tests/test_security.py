import base64

import pytest
from cryptography.exceptions import InvalidTag

from gsm_sim.security import authenticate, demo_a3, demo_a8, encrypt, decrypt

KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
BAD = bytes.fromhex("ffeeddccbbaa99887766554433221100")
RAND = bytes(range(16))

def test_matching_keys_accept_and_return_gsm_sized_values():
    r = authenticate(KEY, KEY, RAND)
    assert r.accepted
    assert r.network_sres == r.sim_sres
    assert len(bytes.fromhex(r.network_sres)) == 4
    assert len(bytes.fromhex(r.kc)) == 8
    assert r == authenticate(KEY, KEY, RAND)

def test_mismatched_credentials_rejected():
    r = authenticate(KEY, BAD, RAND)
    assert r.accepted is False
    assert r.kc is None
    assert r.sim_sres != r.network_sres

def test_invalid_challenge_rejected():
    with pytest.raises(ValueError):
        authenticate(KEY, KEY, b"short")

def test_cipher_roundtrip_and_integrity_rejection():
    kc = authenticate(KEY, KEY, RAND).kc
    encoded = encrypt("Academic GSM test 🔐", kc)
    assert decrypt(encoded, kc) == "Academic GSM test 🔐"
    damaged = bytearray(base64.b64decode(encoded))
    damaged[-1] ^= 1
    with pytest.raises(InvalidTag):
        decrypt(base64.b64encode(damaged).decode("ascii"), kc)
