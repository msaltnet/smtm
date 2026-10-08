"""Explicit cash-delta accounting selection; not exchange precision rules."""


def validate_cash_accounting(mode):
    if not isinstance(mode, str) or mode not in ("legacy", "fractional"):
        raise ValueError("cash_accounting must be 'legacy' or 'fractional'")
    return mode


def validate_profile_cash_accounting(profile):
    mode = validate_cash_accounting(profile.get("cash_accounting", "legacy"))
    if mode == "fractional" and profile.get("virtual") is not True:
        raise ValueError("fractional cash_accounting requires virtual: true")
    return mode
