"""lockpin - the disarm PIN for `cliss lock --sentry`.

Usage: printf %s "$pin" | python3 lockpin.py

Prints a salted hash of the PIN read from stdin, for CLISS_LOCK_PIN. The
screensaver checks what's typed against it, so the PIN itself is never stored
or passed around.
"""

import hashlib
import hmac
import os
import sys

# how long after the first key the PIN can be typed; the screen locks
# 2.5s after that key anyway
WINDOW = 3.0


def _digest(salt, pin):
    return hashlib.sha256(salt + pin).hexdigest()


def spec(pin):
    """A '<salt>:<hash>' string for `pin` (bytes)."""
    salt = os.urandom(16)
    return salt.hex() + ":" + _digest(salt, pin)


def matches(pin, value):
    """True if `pin` (bytes) is the PIN `value` came from."""
    try:
        salt, digest = value.split(":")
        salt = bytes.fromhex(salt)
    except ValueError:
        return False
    return hmac.compare_digest(_digest(salt, pin), digest)


def entry(typed):
    """What was typed (bytes) up to Enter, with backspaces applied."""
    out = bytearray()
    for b in typed:
        if b in (0x0a, 0x0d):
            break
        if b in (0x08, 0x7f):
            del out[-1:]
        else:
            out.append(b)
    return bytes(out)


if __name__ == "__main__":
    print(spec(sys.stdin.buffer.read()))
