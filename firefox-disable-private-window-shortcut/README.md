# Disable Firefox Shift+Cmd+P (macOS)

Disable the built-in "New Private Window" shortcut so web apps can use
Shift+Cmd+P (e.g. Google Docs "Show non-printing characters").

This uses Firefox AutoConfig. It is unsupported and may be overwritten by
Firefox updates. Reapply after updating if the shortcut returns.

Firefox is adding an experimental `about:keyboard` UI for shortcut customization
(see https://bugzilla.mozilla.org/show_bug.cgi?id=1635774). Until that matures
and covers browser-reserved keys reliably, this AutoConfig approach remains the
most dependable way to disable Shift+Cmd+P.

## Install

1) Quit Firefox completely.
2) Run the install script (it will prompt for sudo):

```
./install.sh
```

3) Relaunch Firefox and test Shift+Cmd+P.

## Uninstall

```
./uninstall.sh
```

## Verify (optional)

Open `about:config` and confirm:

- `general.config.filename` = `firefox.cfg`
- `general.config.obscure_value` = `0`
- `general.config.sandbox_enabled` = `false`

## Notes

- Requires admin password (writes into `/Applications/Firefox.app`).
- If Firefox hangs, run `./uninstall.sh` and retry after update.
- If you switch to `about:keyboard` in the future, your customizations are stored
  in `customKeys.json` inside the profile directory; keep that backed up.

## After Firefox Updates

Firefox updates can overwrite the app bundle. If the shortcut comes back:

1) Re-run `./install.sh` (or `make install`).
2) Restart Firefox and re-test Shift+Cmd+P.
