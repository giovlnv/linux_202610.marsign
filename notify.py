import os

import requests


def webhook():
    return os.environ.get("MARSIGN_HA_WEBHOOK", "").strip()


def message(resigned=(), failed=(), unreachable=()):
    lines = []
    if unreachable:
        apps = ", ".join(f"{name} ({days:.1f} days left)" for name, days in unreachable)
        lines.append(f"Couldn't reach the iPhone to re-sign {apps}.")
    lines.extend(failed)
    if resigned:
        apps = ", ".join(f"{name} (until {expires:%d/%m})" for name, expires in resigned)
        lines.append(f"Re-signed {apps}.")
    if not lines:
        return None
    if unreachable:
        title = "Marsign: iPhone not reachable"
    elif failed:
        title = "Marsign: re-sign failed"
    else:
        title = "Marsign: apps re-signed"
    return title, "\n".join(lines)


def send(title, body):
    url = webhook()
    if not url:
        return False
    try:
        requests.post(url, json={"title": title, "message": body}, timeout=15).raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Home Assistant notification failed: {e}")
        return False


def report(**results):
    content = message(**results)
    if content:
        send(*content)
