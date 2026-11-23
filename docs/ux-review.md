# ux review (tapa de ux)

19/11/2026 · code only · rules: tapa-de-ux-en. marsign has no screens: the interface is the terminal output and the Home Assistant notifications, so the review focused on ux writing, states and errors.

reviewed: `marsign.py`, `notify.py`, `device.py`, `apple/account.py` (error messages), `README.md`. not reviewed: the real notifications on the phone.

overall: clear, plain commands with helpful `--help` text. The device errors already say what to do ("Plug the iPhone in over USB and unlock it."), and the notification title changes with the outcome.

## confuses

1. **errors say what happened and what to do**: "Couldn't reach the iPhone to re-sign Familiar (1.5 days left)." arrived on the phone with no next step. **fixed**: adds "Keep it on the home Wi-Fi; the next daily check tries again."
2. **errors say what happened and what to do**: a failed re-sign sent the raw exception ("Familiar: SomeError: …") and stopped there. **fixed**: adds "Run marsign.py refresh on ares to see the details and try again." The raw reason stays, since it's useful when debugging.
3. **every action responds**: `notify-test` printed just "Not sent". **fixed**: "Not sent: Home Assistant didn't accept it (see the error above)".

## finish

4. **one format per data type**: "1 of 1 apps due for refresh". **fixed**: real singular.
5. **one format per data type**: dates are `21/11` in notifications, `2026-11-21` in the terminal, and "1.5 days left" in `status`. Each fits its context, but a single style (`21/11` plus days left) would read better side by side. Not changed.
6. **people's words**: some Apple errors pass HTTP codes and raw response text (`SMS code rejected (HTTP 400): …`). Fine for a personal CLI; mentioned only for the planned public version.

note: `tests/test_units.py` doesn't run here because `pymobiledevice3` isn't installed (unrelated to these changes). The notify and registry tests pass.

# 20/11 (ux sweep)

20/11/2026 · code and a live pass in the terminal · rules: tapa-de-ux-en. origin/main hadn't changed since the 19/11 review (its fixes were the last commit), so this part does the safe "not changed" proposals and goes over the surfaces 19/11 didn't: `status`, `refresh` with nothing due, `uninstall`, `--help`, the file and pairing errors.

live pass: `--help`, `status`, `refresh` with nothing due, `uninstall` without a terminal, `notify-test` without a webhook, and `profile` / `import-pairing` with wrong files, all against a fake `MARSIGN_DATA` in a temp folder. Nothing that signs, installs or talks to Apple. No screenshots: marsign has no screens.

## blocks use

7. **deleting has an undo or a confirm**: `uninstall` removed the app and its data from the iPhone straight away, with no question and no way back. **fixed**: it names the app ("Remove Familiar (com.…) and its data from the iPhone? This can't be undone. [y/N]"); `--yes` skips the question, and without a terminal it refuses unless `--yes` is given.

## confuses

8. **one format per data type** (proposal 5 above): **done**. One style everywhere, in local time: `status` shows "until 26/11, 5.3 days left", `refresh` and `sign` print "until 27/11", the unreachable notification says "Familiar (until 22/11, 1.5 days left)". `profile` keeps the year (`27/11/2027 14:00`) because profiles can last a year. The `[2026-11-20 22:53]` stamp at the top of `refresh` stays: it's a log timestamp for the journal, not a date the person reads.
9. **errors say what happened and what to do**: an expired app showed as "-0.4 days left". **fixed**: "expired on 20/11", and `status` adds "Expired apps no longer open; marsign.py refresh re-signs them."
10. **errors say what happened and what to do**: with no iPhone on USB and no Wi-Fi pairing on the machine, the error said "Keep it on the same network", which can't help. **fixed**: it says Wi-Fi isn't set up yet and points to `pair-wifi` or `import-pairing`.
11. **errors say what happened and what to do**: `notify-test` without a webhook said only "MARSIGN_HA_WEBHOOK is not set". **fixed**: it shows how to run it with the URL and where the timer reads it (`<data>/env`).
12. **people's words**: wrong files ended as "Error: ValueError: Not a provisioning profile…" or "FileNotFoundError: [Errno 2] …". **fixed**: "File not found: /path" and the plain message; `import-pairing` names the file it got ("hostname isn't a pairing record; expected the remote_<udid>.plist made by pair-wifi").

## finish

13. **empty states show the way forward**: `status` and `refresh` with no apps now say "Install one with: marsign.py install app.ipa"; `refresh` with nothing due says which app is next ("Next: Athena (until 24/11, 3.1 days left); re-signed at 2 days or less").
14. **every control says what it is**: `--help` listed all 17 commands twice in one long `{devices,apps,…}` line, and the positional arguments had no help. **fixed**: the usage reads `command ...` and every argument says what it takes.
15. **people's words** (proposal 6 above): Apple errors with HTTP codes and raw response text. Not changed: still only matters for the public version.
16. README's first line still names Marscade. Not changed here: Mars's unpushed local commit 800341a already fixes it (and the matching test names).

## unslop

Doesn't apply: marsign is a CLI plus Home Assistant notifications, with no web page or screen. Visual rules (contrast, targets, type, palette, motion) don't apply either; the iPhone renders the notifications.

checks: `python -m unittest discover -s tests -t .` passes, 17 tests (13 before, plus the date and uninstall tests). `tests/test_units.py` runs now with the repo's `.venv`. There's no linter or typecheck in the repo; `py_compile` passes on every file.

## tapa de ux audit (real skill, 20/11)

20/11/2026 · code and unit tests only · rules: tapa-de-ux-en (the real skill files, all ten topics in order). The sweep above worked from older reviews; this pass checks it against the actual rules. marsign is a CLI, so CLI conventions win: the visual topics became output layout, wording and terminal colour. Exercised only through the unit tests with a fake `MARSIGN_DATA` and `device.connect` / `requests.post` mocked; nothing ran `refresh`, `install`, `sign`, `uninstall` or `pair-wifi`.

reviewed: `marsign.py` (all commands, `--help`, prompts, errors), `notify.py`, `registry.py`, `device.py`, `signer.py`, `apple/account.py` (prompts and errors), `README.md`. not reviewed: the notifications as the iPhone shows them; the real `login` flow against Apple.

### topics

- **hierarchy**: lists are the only layout. `status` and `apps` joined fields with two spaces, so with names of different lengths the dates and bundle IDs zigzagged ("same component, same spacing"). Fixed: columns line up.
- **typography**: the terminal's font. Only sentence case applies: help strings are lowercase with no period, which is argparse's convention (conflict with sentence case; the project follows the CLI).
- **accessibility**: no colour, so "never colour alone" holds. "Every control says what it is" is the `--help`: every argument says what it takes (sweep item 14). Lines fit 80 columns now (two help strings wrapped mid-word: "systemd-/creds").
- **color**: no colour in the output. Adding colour isn't needed; if it ever comes, status words ("expired", "failed") stay as words.
- **buttons and actions**: "every action responds": `install --unsigned-ok` and `install --p12 --profile` finished in silence. Fixed. The `[y/N]` confirm for `uninstall` follows the CLI convention instead of "verb buttons" (conflict noted); its question already names the app and what is lost.
- **forms**: the prompts (`login`, 2FA code, phone choice, uninstall confirm). "Accept the way people type": a code pasted as "123 456" was sent with the space and rejected. Fixed. Ctrl-D at a prompt ended as "Error: EOFError: ". Fixed: "Cancelled", exit 130 like Ctrl-C (Jakob's law: the shell convention).
- **states**: the sweep covered empty states for `status` and `refresh`; `apps` with nothing printed nothing. Fixed. "The wait fits the time": the push to the iPhone is the slowest step and had no line before it. Fixed: "Installing on the iPhone...". zsign errors showed "Error: RuntimeError: zsign failed: …". Fixed: the plain message; the checksum error now says to run `setup` again.
- **ux writing**: one name for each thing: the timer was "systemd timer", "scheduled refresh", "timer" and "daily check" (in the notification). Fixed: "the daily check" in help, `unschedule` and README. The program called itself `marsign` in `--help` while every message says `marsign.py`. Fixed. Plural: "re-signed at 1 days or less" with `--days 1`. Fixed. Periods: complete-sentence errors got one, as the device errors already had.
- **navigation**: the `--help` is the map. "A short path to what people do most": it listed `devices`, `apps`, `login`... with `status` and `refresh` 12th and 13th, in a different order from the README. Fixed: the README's order, everyday commands first; and a one-line description at the top.
- **psychology**: Tesler and memory: `uninstall` needs the full signed bundle ID (with the team suffix), which people copy from `status`. Left open below. Peak-end: `refresh` ends with one line per app and a notification; fine.

### rule findings added

11 beyond the sweep: aligned columns, silent manual installs, codes with spaces, Ctrl-D ending as "Error: EOFError", `apps` empty state, no line before the push, raw RuntimeError names, four names for the daily check, two program names, "1 days", help order. Plus two finish items: periods on complete-sentence errors and help lines wrapping mid-word.

### contradictions with the sweep

None that undo its work. Sweep item 14 shortened the usage line but kept argparse's `prog="marsign"`, which contradicted every message's `marsign.py` ("one name for each thing"); fixed here.

### fixes

- 42ac80f: everything above (help order and name, columns, install responses, cancel, RuntimeError, daily-check wording, plural, 2FA code spaces, periods), with 7 new tests.

### left open

- `uninstall` could take the app name from the registry ("Familiar") instead of the signed bundle ID (Tesler, memory). Behaviour change; Mars's call.
- Apple errors with HTTP codes and raw response text (sweep item 15), and the raw exception name in the "re-sign failed" notification: still debugging aids for a personal tool.
- Missing name or version shows as "?"; the rule says "—". Stored in `apps.json` too, so changing it means a migration; small.
- Less than a day left reads "0.3 days left"; hours would read better. Taste.

checks: `python -m unittest discover -s tests -t .` with the repo's `.venv`: 24 tests pass (17 before, 7 new). `py_compile` passes on every file. No linter or typecheck in the repo.
