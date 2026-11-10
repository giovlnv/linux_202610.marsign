import platform
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from pymobiledevice3.common import get_home_folder
from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError, RemotePairingCompletedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote import tunnel_service, userspace_tunnel
from pymobiledevice3.usbmux import list_devices

from apple import data_dir


class DeviceNotFound(Exception):
    pass


def _host_file():
    return data_dir() / "pairing-host"


def pairing_host():
    path = _host_file()
    return path.read_text().strip() if path.is_file() else platform.node()


def save_pairing_host(name):
    _host_file().write_text(name + "\n")


async def usb_devices():
    try:
        return await list_devices()
    except ConnectionFailedToUsbmuxdError:
        return []


async def _wifi_provider(udid):
    services = await tunnel_service.get_remote_pairing_tunnel_services(udid=udid)
    if not services:
        raise DeviceNotFound("iPhone not found on Wi-Fi. Keep it on the same network as this computer.")
    for extra in services[1:]:
        await extra.close()
    return services[0], None


@asynccontextmanager
async def wifi(udid=None):
    async def provider(serial, autopair, remotepairing_fallback=True):
        return await _wifi_provider(udid)

    userspace_tunnel._create_no_root_tunnel_provider = provider
    host, node = pairing_host(), platform.node
    platform.node = lambda: host
    try:
        async with userspace_tunnel.UserspaceRsdTunnel() as rsd:
            yield rsd
    finally:
        platform.node = node


@asynccontextmanager
async def connect(udid=None):
    usb = [d for d in await usb_devices() if d.is_usb and udid in (None, d.serial)]
    if not usb:
        async with wifi(udid) as rsd:
            yield rsd
        return
    lockdown = await create_using_usbmux(serial=usb[0].serial)
    try:
        yield lockdown
    finally:
        await lockdown.close()


def pairing_records():
    return sorted(get_home_folder().glob("remote_*.plist"))


async def pair_wifi(udid=None):
    usb = [d for d in await usb_devices() if d.is_usb and udid in (None, d.serial)]
    if not usb:
        raise DeviceNotFound("Plug the iPhone in over USB and unlock it.")
    lockdown = await create_using_usbmux(serial=usb[0].serial)
    try:
        service = await tunnel_service.RemotePairingLockdownService.create(lockdown)
        try:
            await service.connect(autopair=True)
        except RemotePairingCompletedError:
            pass
        finally:
            await service.close()
        save_pairing_host(platform.node())
        return get_home_folder() / f"remote_{lockdown.udid}.plist"
    finally:
        await lockdown.close()


def import_pairing(path, host=None):
    source = Path(path)
    if not source.name.startswith("remote_") or source.suffix != ".plist":
        raise ValueError("Expected a remote_<udid>.plist pairing record")
    target = get_home_folder() / source.name
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    target.chmod(0o600)
    if host:
        save_pairing_host(host)
    return target
