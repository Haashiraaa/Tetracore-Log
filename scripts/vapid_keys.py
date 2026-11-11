# scripts/vapid_keys.py

"""Make the key pair browser push needs. Run it once, paste the output into the server's .env.

    python -m scripts.vapid_keys

Prints three lines. VAPID_SUBJECT is yours to fill in (a mailto: address the push services can
reach you on). Needs no database. Keep VAPID_PRIVATE_KEY secret. Changing the pair later makes
every browser that turned push on stop receiving it until they switch it on again.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_keys() -> tuple[str, str]:
    """(public key, private key), both URL-safe base64 as the browser and pywebpush expect."""
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(  # type: ignore[union-attr]
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    private = vapid.private_key.private_bytes(  # type: ignore[union-attr]
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())
    return _b64(public), _b64(private)


def main() -> int:
    public, private = make_keys()
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
    print("VAPID_SUBJECT=mailto:you@example.com")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
