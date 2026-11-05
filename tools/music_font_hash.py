"""Validate generated C font sources across Git newline conversions."""
import hashlib


def source_digest_matches(data: bytes, expected: str) -> bool:
    lf = data.replace(b"\r\n", b"\n")
    if b"\r" in lf:
        return False
    return expected in {
        hashlib.sha256(lf).hexdigest(),
        hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest(),
    }
