from __future__ import annotations

import backend.security_gates as security_gates


if __name__ == "__main__":
    reset = getattr(security_gates, "reset_for_test", None)
    if callable(reset):
        reset()
    print("RESET_AUTH_QUOTA")
