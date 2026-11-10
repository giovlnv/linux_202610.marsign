# Marsign

Personal installer and weekly re-signer for my own iPhone apps (Marscade, Familiar), run on Linux.
Day to day it runs on ares: a systemd timer re-signs the apps over Wi-Fi and Home Assistant sends the result.

## Setup

    sudo apt install -y usbmuxd python3-venv git
    git clone https://github.com/giovlnv/linux_202610.marsign && cd linux_202610.marsign
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python marsign.py setup

## Commands

Run as `.venv/bin/python marsign.py <command>`.

    login                    sign in with your Apple ID (password kept in the keyring unless --no-save)
    install app.ipa          sign with your Apple ID, install, and remember it for refresh
    status                   apps installed through Marsign and days left
    refresh [--force]        re-sign apps with 2 days or less left
    pair-wifi                create the Wi-Fi pairing record (once, iPhone on USB)
    import-pairing FILE --host NAME   use a Wi-Fi pairing record made on machine NAME
    save-password            save the Apple ID password for the timer (systemd-creds)
    schedule [--time 03:00]  daily check with a systemd timer
    unschedule               remove the timer
    notify-test              send a test notification to Home Assistant
    devices                  the iPhone over USB, or over Wi-Fi when nothing is plugged in
    apps                     installed user apps
    uninstall BUNDLE_ID      remove an app from the iPhone
    logout                   forget the saved Apple session

Manual signing, without an Apple ID:

    profile dev.mobileprovision
    sign app.ipa --p12 cert.p12 --password PW --profile dev.mobileprovision
    install app.ipa --p12 cert.p12 --password PW --profile dev.mobileprovision

## Wi-Fi

iOS 17 and later cut off the old Wi-Fi connection as soon as a service starts, so Marsign uses the
same RemotePairing tunnel as Xcode. `pair-wifi` creates its record once over USB, with no prompt on
the iPhone; it is saved as `~/.local/share/pymobiledevice3/remote_<udid>.plist`. After that every
command finds the iPhone on the local network by itself. A plugged-in iPhone is always used over USB.

The iPhone only accepts the record from the hostname that paired it, so Marsign saves that name as
`pairing-host` in the data folder and sends it when connecting. `import-pairing --host` sets it on
another machine.

The record gives full access to the iPhone: keep it private and never commit it.

## ares

Everything below runs on ares as `mars`, after the setup above.

1. Copy the data from the machine that already signs (`~/.local/share/Marsign` and the
   `remote_<udid>.plist` record), so the same certificate and Apple session are reused. Starting fresh
   instead would revoke the certificate the installed apps are signed with.

        sudo install -d -o mars -g mars /srv/config/marsign
        rsync -a ~/.local/share/Marsign/ ~/.local/share/pymobiledevice3/remote_*.plist mars@ares:/srv/config/marsign/

2. On ares:

        export MARSIGN_DATA=/srv/config/marsign
        .venv/bin/python marsign.py import-pairing /srv/config/marsign/remote_<udid>.plist --host <pairing machine>
        rm /srv/config/marsign/remote_<udid>.plist
        .venv/bin/python marsign.py save-password
        echo 'MARSIGN_HA_WEBHOOK=http://localhost:8123/api/webhook/<webhook_id>' > /srv/config/marsign/env
        chmod 600 /srv/config/marsign/env
        .venv/bin/python marsign.py devices
        .venv/bin/python marsign.py schedule
        sudo systemctl start marsign-refresh.service    # first run; add --force by hand to test a re-sign

3. Logs: `journalctl -u marsign-refresh`.

Discovery uses mDNS: if ufw is on, allow it with `sudo ufw allow 5353/udp`.

## Home Assistant

Marsign posts `{"title", "message"}` to the webhook after each refresh: apps re-signed, a re-sign
failed, or the iPhone was not reachable while apps were due. An automation passes it to the phone:

    alias: marsign notifications
    triggers:
      - trigger: webhook
        webhook_id: <webhook_id>
        allowed_methods: [POST]
        local_only: true
    actions:
      - action: notify.mobile_app_<iphone>
        data:
          title: "{{ trigger.json.title }}"
          message: "{{ trigger.json.message }}"

## Where things are kept

`~/.local/share/Marsign`, or `MARSIGN_DATA` when set: the Apple session token, this machine's device
identity, the signing key and certificate, provisioning profiles, a copy of each installed .ipa and
the app list. The password lives in the keyring (desktop) or in
`/etc/credstore.encrypted/marsign-apple` (ares), which only the timer's service can decrypt.

Apple rejects locally generated device identity data now, so Marsign gets it from an anisette v3 server:
`mac-ani.jkcoxson.com` by default, the same as iloader. Alternatives are `new.ani.sidestore.io` and
`ani3.stikstore.app`; set `MARSIGN_ANISETTE` to use one.
The server sees this machine's device identifier, never the Apple ID, password or codes.

The certificate is registered under the machine name "Marsign", so it lives alongside AltStore's
or Xcode's instead of replacing them. Only older Marsign certificates are ever revoked.

## Tests

    .venv/bin/python -m unittest discover -s tests -t .

## Credits

The Apple sign-in and developer-portal flow follows [iPASide](https://github.com/pwnapplehat/iPASide)
(MIT). Signing uses [zsign](https://github.com/zhlynn/zsign); device access and the Wi-Fi tunnel use
[pymobiledevice3](https://github.com/doronz88/pymobiledevice3); the anisette v3 protocol follows
[isideload](https://github.com/nab138/isideload), iloader's library.
