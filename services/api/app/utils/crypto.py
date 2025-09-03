import os, hashlib, binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def load_master_key(hex_key: str) -> bytes:
    key = binascii.unhexlify(hex_key)
    if len(key) not in (16, 24, 32):
        raise ValueError("APP_MASTER_KEY_HEX must be 16/24/32 bytes (32/48/64 hex chars)")
    return key

def encrypt_bytes(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    # AES-GCM with 12B random nonce
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ct = aesgcm.encrypt(iv, plaintext, None)
    return ct, iv

def decrypt_bytes(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None)

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
