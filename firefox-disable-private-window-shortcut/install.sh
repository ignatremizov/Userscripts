#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

APP="/Applications/Firefox.app"
RES="$APP/Contents/Resources"
PREF_DIR="$RES/defaults/pref"

mkdir -p "$PREF_DIR"

cat > "$PREF_DIR/autoconfig.js" <<'EOF'
pref("general.config.filename", "firefox.cfg");
pref("general.config.obscure_value", 0);
pref("general.config.sandbox_enabled", false);
EOF

cat > "$RES/firefox.cfg" <<'EOF'
// IMPORTANT: Start your code on the 2nd line
pref("autoconfig.test.value", "loaded");

try {
  let { classes: Cc, interfaces: Ci } = Components;

  let prefs = Cc["@mozilla.org/preferences-service;1"]
    .getService(Ci.nsIPrefBranch);
  prefs.setBoolPref("autoconfig.services.ok", true);

  function nukePrivateKey(doc) {
    let key = doc.getElementById("key_privatebrowsing");
    if (key && key.parentNode) {
      key.parentNode.removeChild(key);
      prefs.setBoolPref("autoconfig.pbkey.removed", true);
    }
  }

  let observer = {
    observe(subject) {
      let win = subject;
      if (!win || !win.addEventListener) return;

      win.addEventListener("DOMContentLoaded", function(e) {
        let doc = e.originalTarget;
        let href = doc && doc.location ? doc.location.href : "";
        if (href.startsWith("chrome://browser/content/browser.")) {
          nukePrivateKey(doc);
          let mo = new win.MutationObserver(() => nukePrivateKey(doc));
          mo.observe(doc, { childList: true, subtree: true });
        }
      }, { once: false });
    },
  };

  let obs = Cc["@mozilla.org/observer-service;1"]
    .getService(Ci.nsIObserverService);
  obs.addObserver(observer, "chrome-document-global-created");
} catch (e) {
  pref("autoconfig.services.error", String(e));
}
EOF

echo "Installed AutoConfig files into $APP"
echo "Restart Firefox to apply."
