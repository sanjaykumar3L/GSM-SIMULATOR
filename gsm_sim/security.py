"""Synthetic GSM-style security procedure. NOT a real A3/A8/A5 implementation."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# The simulator uses HMAC for A3/A8-like challenge/response and AES-GCM
# for a separate encryption example. Neither implements the actual GSM algorithms.

@dataclass(frozen=True)
class Authentication:
    rand: str
    network_sres: str
    sim_sres: str
    kc: str | None
    accepted: bool

def demo_a3(secret: bytes, rand: bytes) -> bytes:
    if len(secret) != 16 or len(rand) != 16:
        raise ValueError("Demo subscriber key and RAND must each be 16 bytes")
    return hmac.new(secret, b"DEMO-A3-" + rand, hashlib.sha256).digest()[:4]

def demo_a8(secret: bytes, rand: bytes) -> bytes:
    if len(secret) != 16 or len(rand) != 16:
        raise ValueError("Demo subscriber key and RAND must each be 16 bytes")
    return hmac.new(secret, b"DEMO-A8-" + rand, hashlib.sha256).digest()[:8]

def authenticate(network_key: bytes, sim_key: bytes, rand: bytes | None = None) -> Authentication:
    rand = rand if rand is not None else os.urandom(16)
    expected = demo_a3(network_key, rand)
    received = demo_a3(sim_key, rand)
    ok = hmac.compare_digest(expected, received)
    return Authentication(
        rand=rand.hex(), network_sres=expected.hex(), sim_sres=received.hex(),
        kc=demo_a8(sim_key, rand).hex() if ok else None, accepted=ok,
    )

def _aes_key(kc_hex: str) -> bytes:
    kc = bytes.fromhex(kc_hex)
    if len(kc) != 8:
        raise ValueError("Expected 64-bit simulated Kc")
    return hashlib.sha256(b"SIMULATION-AES-GCM-" + kc).digest()

def encrypt(plaintext: str, kc_hex: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_aes_key(kc_hex)).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")

def decrypt(token: str, kc_hex: str) -> str:
    raw = base64.b64decode(token, validate=True)
    if len(raw) < 28:
        raise ValueError("Malformed encrypted payload")
    plaintext = AESGCM(_aes_key(kc_hex)).decrypt(raw[:12], raw[12:], None)
    return plaintext.decode("utf-8")
