## Ignat's scripts

A collection of scripts I wrote for various tasks

- `firefox-disable-private-window-shortcut/README.md`: Disable Shift+Cmd+P in Firefox (macOS) so web apps can use it. Use `cd firefox-disable-private-window-shortcut && make install` or `cd firefox-disable-private-window-shortcut && make uninstall`.

### Git helpers

- `bin/restack-branch-refs`: Restack a linear branch stack after rebasing the tip branch. Intended workflow is `main -> branch1 -> branch2 -> fork`, then run from the rebased tip branch.
  - Dry run: `restack-branch-refs --base main --tip fork`
  - Apply locally: `restack-branch-refs --base main --tip fork --apply`
  - Apply and push: `restack-branch-refs --base main --tip fork --push`
  - Scope to your stacked branch names if needed: `restack-branch-refs --base main --tip fork --match-prefix feat/ --match-prefix fix/`
  - Show the rewritten series with `git range-diff`: `restack-branch-refs --base main --tip fork --range-diff`
  - Assumes a linear stack on the old tip branch first-parent chain and that `<tip>@{1}` still points to the pre-rebase tip.

### Shell helpers

- `bin/alarm`: Sleep for a short duration, then ring the terminal bell.
  - Install: `install -m 755 bin/alarm ~/.local/bin/alarm`
  - Usage: `alarm <number>[s|m|h|d]`
  - Examples: `alarm 30s`, `alarm 10m`, `alarm 2h`, `alarm 1d`
  - Omitting the suffix defaults to minutes: `alarm 5` waits 5 minutes.
