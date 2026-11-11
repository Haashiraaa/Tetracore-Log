# tests/scripts/test_vapid_keys.py  (scripts/vapid_keys.py)

import base64

from py_vapid import Vapid

from scripts import vapid_keys


def _raw(b64: str) -> bytes:
    return base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))


def test_prints_the_three_lines_for_the_env_file(capsys):
    assert vapid_keys.main() == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT"]


def test_keys_are_a_matching_pair_pywebpush_can_load():
    public, private = vapid_keys.make_keys()
    assert len(_raw(public)) == 65 and _raw(public)[0] == 4  # an uncompressed P-256 point
    signer = Vapid.from_string(private)  # the form webpush() is given
    assert signer.public_key is not None


def test_each_run_makes_a_new_pair():
    assert vapid_keys.make_keys() != vapid_keys.make_keys()
