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
