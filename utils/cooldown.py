# filename: utils/cooldown.py

import time


def ensure_cd(user: dict):
    """
    Ensures `user['cooldowns']` exists and is a dict.
    Always returns the user dict with safe cooldown storage.
    """
    if 'cooldowns' not in user or not isinstance(user.get('cooldowns'), dict):
        user['cooldowns'] = {}
    return user


def check_cooldown(user: dict, cmd: str, cooldown_seconds: int):
    """
    Checks cooldown for a command.

    Returns:
        ok (bool): True if user can use the command now
        remaining (int): seconds left for cooldown
        pretty (str): formatted remaining time (e.g., "2h 5m 1s")
    """
    user = ensure_cd(user)
    now = int(time.time())
    last = int(user['cooldowns'].get(cmd, 0))

    diff = now - last

    # no cooldown active
    if diff >= cooldown_seconds:
        return True, 0, "0s"

    remain = max(cooldown_seconds - diff, 0)

    # Make pretty human time
    m, s = divmod(remain, 60)
    h, m = divmod(m, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s:
        parts.append(f"{s}s")

    pretty = " ".join(parts) if parts else "0s"
    return False, remain, pretty


def update_cooldown(user: dict, cmd: str):
    """
    Updates cooldown timestamp.
    NOTE: Must save with update_user() after using this function.
    """
    user = ensure_cd(user)
    user['cooldowns'][cmd] = int(time.time())
    return user


def cleanup_cooldowns(user: dict, max_age_seconds: int = 604800):
    """
    Removes cooldowns older than max_age_seconds (default: 7 days).
    """
    user = ensure_cd(user)
    now = int(time.time())
    user['cooldowns'] = {
        cmd: ts
        for cmd, ts in user['cooldowns'].items()
        if now - ts < max_age_seconds
    }
    return user
