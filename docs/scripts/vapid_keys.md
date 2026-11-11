# `scripts/vapid_keys.py`

**Purpose:** makes the key pair that browser push (see [../notifications.md](../notifications.md))
needs. Run it once per installation.

**Touches:** nothing. It does not read or change the database and needs no `.env`.

```bash
python -m scripts.vapid_keys
```

## What it prints

```
VAPID_PUBLIC_KEY=BC2T-0Pjq_G3...
VAPID_PRIVATE_KEY=MIGHAgEAMBMG...
VAPID_SUBJECT=mailto:you@example.com
```

Paste the three lines into the server's `.env` and **replace the `VAPID_SUBJECT`** with a real
`mailto:` address: push services use it to reach you if something misbehaves. Restart the API.
Until all three are set, the app hides the push switch and the feed works without it.

## Care

- `VAPID_PRIVATE_KEY` is a secret. Do not commit it or paste it into a chat.
- Run it **once**. A new pair means every browser that turned push on must switch it on again,
  because their subscriptions belong to the old public key.
