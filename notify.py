import os

import requests

from registry import until


def webhook():
    return os.environ.get("MARSIGN_HA_WEBHOOK", "").strip()


def message(resigned=(), failed=(), unreachable=()):
    lines = []
    if unreachable:
        apps = ", ".join(f"{name} ({state})" for name, state in unreachable)
        lines.append(f"Couldn't reach the iPhone to re-sign {apps}. Keep it on the home Wi-Fi; the next daily check tries again.")
    lines.extend(failed)
    if failed:
        lines.append("Run marsign.py refresh on ares to see the details and try again.")
    if resigned:
        apps = ", ".join(f"{name} (until {until(expires)})" for name, expires in resigned)
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
