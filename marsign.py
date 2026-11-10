import argparse
import asyncio
import getpass
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.installation_proxy import InstallationProxyService

import device
import notify
import registry
import signer
from apple import AppleError, account, data_dir, portal

SERVICE = "marsign-refresh"
UNIT_DIR = Path("/etc/systemd/system")
CREDSTORE = Path("/etc/credstore.encrypted")


def check_ipa(path):
    ipa = Path(path)
    if not ipa.is_file():
        sys.exit(f"File not found: {ipa}")
    return ipa


async def describe(dev, connection):
    name = await dev.get_value(key="DeviceName")
    version = await dev.get_value(key="ProductVersion")
    udid = await dev.get_value(key="UniqueDeviceID")
    print(f"{name}  iOS {version}  [{connection}]  {udid}")


async def cmd_devices(args):
    usb = [d for d in await device.usb_devices() if d.is_usb]
    for d in usb:
        lockdown = await create_using_usbmux(serial=d.serial)
        try:
            await describe(lockdown, "USB")
        finally:
            await lockdown.close()
    if not usb:
        async with device.wifi(args.udid) as rsd:
            await describe(rsd, "Wi-Fi")


async def cmd_apps(args):
    async with device.connect(args.udid) as dev:
        async with InstallationProxyService(lockdown=dev) as proxy:
            apps = await proxy.get_apps(application_type="User")
    for bundle_id, info in sorted(apps.items()):
        name = info.get("CFBundleDisplayName") or info.get("CFBundleName", "?")
        print(f"{name}  {info.get('CFBundleShortVersionString', '?')}  {bundle_id}")


async def cmd_login(args):
    email = args.email or input("Apple ID: ").strip()
    note = "not saved" if args.no_save else "saved in the system keyring"
    password = getpass.getpass(f"Password ({note}): ")
    s = account.login(email, password, lambda prompt: input(prompt).strip(), save_password=not args.no_save)
    print(f"Signed in as {s['email']}")
    print(f"Team {portal.team()}")


async def cmd_logout(args):
    account.logout()
    print("Signed out")


async def cmd_save_password(args):
    password = getpass.getpass("Apple ID password (encrypted with systemd-creds): ")
    subprocess.run(["sudo", "install", "-d", "-m", "700", str(CREDSTORE)], check=True)
    subprocess.run(
        ["sudo", "systemd-creds", "encrypt", f"--name={account.CREDENTIAL_NAME}", "-",
         str(CREDSTORE / account.CREDENTIAL_NAME)],
        input=password.encode(), check=True)
    print(f"Saved to {CREDSTORE / account.CREDENTIAL_NAME}; only {SERVICE}.service can read it")


async def cmd_setup(args):
    print(f"zsign ready: {signer.ensure_zsign()}")


async def cmd_profile(args):
    info = signer.read_profile(args.profile)
    print(f"Name:      {info['name']}")
    print(f"Bundle ID: {info['bundle_id']}")
    print(f"Team:      {info['team']}")
    print(f"Expires:   {info['expires']:%Y-%m-%d %H:%M}")
    print(f"Devices:   {', '.join(info['devices']) or 'none'}")


def manual_sign(args, ipa, output=None):
    if not (args.p12 and args.profile):
        sys.exit("Manual signing needs both --p12 and --profile")
    out, info = signer.sign(ipa, args.p12, args.profile, args.password, output)
    print(f"Signed {info['bundle_id']} (expires {info['expires']:%Y-%m-%d}) -> {out}")
    return out


async def cmd_sign(args):
    manual_sign(args, check_ipa(args.ipa), args.output)


async def push(dev, signed):
    async with InstallationProxyService(lockdown=dev) as proxy:
        await proxy.install_from_local(signed)


async def sign_and_push(dev, ipa):
    app = signer.ipa_info(ipa)
    device_name = await dev.get_value(key="DeviceName")
    udid = await dev.get_value(key="UniqueDeviceID")
    print(f"{app['name']} {app['version']} -> {device_name}")
    assets = portal.provision(app["bundle_id"], app["name"], udid, device_name)
    signed = Path(tempfile.gettempdir()) / f"marsign-{assets['bundle_id']}.ipa"
    _, info = signer.sign(ipa, assets["p12"], assets["profile"], assets["password"], signed)
    print(f"Signed {info['bundle_id']} (expires {info['expires']:%Y-%m-%d})")
    await push(dev, signed)
    signed.unlink(missing_ok=True)
    registry.record(ipa, app, info["bundle_id"], info["expires"])
    print(f"Installed {app['name']}")
    return info


async def cmd_install(args):
    ipa = check_ipa(args.ipa)
    async with device.connect(args.udid) as dev:
        if args.unsigned_ok:
            await push(dev, ipa)
        elif args.p12 or args.profile:
            await push(dev, manual_sign(args, ipa))
        else:
            await sign_and_push(dev, ipa)


async def cmd_pair_wifi(args):
    record = await device.pair_wifi(args.udid)
    print(f"Wi-Fi pairing record: {record}")
    print(f"Copy it to the machine that re-signs and run: marsign.py import-pairing <file> --host {device.pairing_host()}")


async def cmd_import_pairing(args):
    print(f"Imported to {device.import_pairing(args.record, args.host)}")
    print(f"Connecting as {device.pairing_host()}")


async def cmd_status(args):
    apps = registry.load()
    if not apps:
        print("No apps installed through Marsign yet.")
    for bundle_id, entry in sorted(apps.items()):
        print(f"{entry['name']} {entry['version']}  {registry.days_left(entry):.1f} days left  {bundle_id}")


async def refresh(due, udid):
    resigned, failed = [], []
    async with device.connect(udid) as dev:
        for entry in due.values():
            ipa = registry.ipa_path(entry)
            if not ipa.is_file():
                failed.append(f"{entry['name']}: stored .ipa missing, install it again")
                continue
            try:
                info = await sign_and_push(dev, ipa)
                resigned.append((entry["name"], info["expires"]))
            except Exception as e:
                failed.append(f"{entry['name']}: {e}")
    return resigned, failed


async def cmd_refresh(args):
    apps = registry.load()
    due = {b: e for b, e in apps.items() if args.force or registry.days_left(e) <= args.days}
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {len(due)} of {len(apps)} apps due for refresh")
    if not due:
        return
    try:
        resigned, failed = await refresh(due, args.udid)
    except device.DeviceNotFound:
        notify.report(unreachable=[(e["name"], registry.days_left(e)) for e in due.values()])
        raise
    except Exception as e:
        notify.report(failed=[f"{type(e).__name__}: {e}"])
        raise
    notify.report(resigned=resigned, failed=failed)
    if failed:
        sys.exit("Refresh failed for:\n  " + "\n  ".join(failed))


async def cmd_uninstall(args):
    async with device.connect(args.udid) as dev:
        async with InstallationProxyService(lockdown=dev) as proxy:
            await proxy.uninstall(args.bundle_id)
    registry.forget(args.bundle_id)
    print(f"Removed {args.bundle_id}")


def units(time, credential):
    script = Path(__file__).resolve()
    service = f"""[Unit]
Description=marsign: re-sign iPhone apps
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User={getpass.getuser()}
WorkingDirectory={script.parent}
Environment=MARSIGN_DATA={data_dir()}
EnvironmentFile=-{data_dir() / "env"}
ExecStart={sys.executable} {script} refresh
"""
    if credential:
        service += f"LoadCredentialEncrypted={account.CREDENTIAL_NAME}\n"
    timer = f"""[Unit]
Description=marsign: daily re-sign check

[Timer]
OnCalendar=*-*-* {time}:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    return service, timer


def sudo_write(path, text):
    subprocess.run(["sudo", "tee", str(path)], input=text.encode(), stdout=subprocess.DEVNULL, check=True)


async def cmd_schedule(args):
    if not shutil.which("systemctl"):
        sys.exit("Scheduling needs systemd")
    credential = (CREDSTORE / account.CREDENTIAL_NAME).exists()
    if not credential:
        print("No saved password yet (marsign.py save-password); refreshes work until Apple asks to sign in again.")
    service, timer = units(args.time, credential)
    sudo_write(UNIT_DIR / f"{SERVICE}.service", service)
    sudo_write(UNIT_DIR / f"{SERVICE}.timer", timer)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "--now", f"{SERVICE}.timer"], check=True)
    print(f"Scheduled daily at {args.time}; apps are re-signed when 2 days or less remain.")
    print(f"Log: journalctl -u {SERVICE}")


async def cmd_unschedule(args):
    subprocess.run(["sudo", "systemctl", "disable", "--now", f"{SERVICE}.timer"], check=True)
    subprocess.run(["sudo", "rm", "-f", str(UNIT_DIR / f"{SERVICE}.service"), str(UNIT_DIR / f"{SERVICE}.timer")],
                   check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    print("Removed the scheduled refresh")


async def cmd_notify_test(args):
    if not notify.webhook():
        sys.exit("MARSIGN_HA_WEBHOOK is not set")
    sent = notify.send("Marsign: test", "Notifications from Marsign work.")
    print("Sent" if sent else "Not sent")


def main():
    parser = argparse.ArgumentParser(prog="marsign")
    parser.add_argument("--udid", help="target a specific device")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("devices", help="list connected devices (USB, or Wi-Fi when none is plugged in)")
    sub.add_parser("apps", help="list installed user apps")
    login = sub.add_parser("login", help="sign in with your Apple ID")
    login.add_argument("email", nargs="?")
    login.add_argument("--no-save", action="store_true", help="don't save the password in the keyring")
    sub.add_parser("logout", help="forget the saved Apple session")
    sub.add_parser("save-password", help="save the Apple ID password for the scheduled refresh (systemd-creds)")
    sub.add_parser("setup", help="download zsign")

    profile = sub.add_parser("profile", help="show what a provisioning profile allows")
    profile.add_argument("profile")

    def signing_args(p):
        p.add_argument("--p12", help="use this certificate instead of your Apple ID")
        p.add_argument("--profile", help="use this provisioning profile instead of your Apple ID")
        p.add_argument("--password", default="", help="password for --p12")

    sign = sub.add_parser("sign", help="sign an .ipa with a given certificate and profile")
    sign.add_argument("ipa")
    sign.add_argument("-o", "--output")
    signing_args(sign)

    install = sub.add_parser("install", help="sign with your Apple ID and install an .ipa")
    install.add_argument("ipa")
    install.add_argument("--unsigned-ok", action="store_true", help="install the .ipa as-is")
    signing_args(install)

    sub.add_parser("pair-wifi", help="create the Wi-Fi pairing record (once, over USB)")
    pairing = sub.add_parser("import-pairing", help="use a Wi-Fi pairing record made on another machine")
    pairing.add_argument("record")
    pairing.add_argument("--host", help="hostname of the machine that ran pair-wifi")
    sub.add_parser("status", help="show apps installed through Marsign and days left")
    refresh_cmd = sub.add_parser("refresh", help="re-sign and reinstall apps close to expiring")
    refresh_cmd.add_argument("--days", type=float, default=2, help="refresh apps with this many days left or fewer")
    refresh_cmd.add_argument("--force", action="store_true", help="refresh every app now")
    uninstall = sub.add_parser("uninstall", help="remove an app from the iPhone")
    uninstall.add_argument("bundle_id")
    schedule = sub.add_parser("schedule", help="check every day with a systemd timer")
    schedule.add_argument("--time", default="03:00", help="daily check time, HH:MM")
    sub.add_parser("unschedule", help="remove the systemd timer")
    sub.add_parser("notify-test", help="send a test notification to Home Assistant")

    args = parser.parse_args()
    handlers = {
        "devices": cmd_devices, "apps": cmd_apps, "login": cmd_login, "logout": cmd_logout,
        "save-password": cmd_save_password, "setup": cmd_setup, "profile": cmd_profile, "sign": cmd_sign,
        "install": cmd_install, "pair-wifi": cmd_pair_wifi, "import-pairing": cmd_import_pairing,
        "status": cmd_status, "refresh": cmd_refresh, "uninstall": cmd_uninstall,
        "schedule": cmd_schedule, "unschedule": cmd_unschedule, "notify-test": cmd_notify_test,
    }
    try:
        asyncio.run(handlers[args.command](args))
    except (device.DeviceNotFound, AppleError) as e:
        sys.exit(f"\n{e}")
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        sys.exit(f"\nError: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
