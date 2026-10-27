# Installing Quiet Home

Samsung only installs apps signed with a free Samsung certificate made for your
TV, so the first install takes about an hour. After that, updates take a minute.
The steps follow
[Glass Home's install guide](https://github.com/victaphu/glass-home-samsung-tv/blob/main/docs/INSTALL.md)
(tested on a 2023 Samsung Q70C, Tizen 8). Menu names can differ a little on
other models.

Works on **Windows, macOS and Linux**. Commands below are the same everywhere,
except: on Windows type `python`, on macOS/Linux type `python3`.

## 0. What you need

- The computer and the TV on the same home network (not a guest Wi-Fi).
- A free [Samsung account](https://account.samsung.com/).
- **Python 3**, from [python.org](https://www.python.org/downloads/). On
  Windows, tick **Add python.exe to PATH** in the installer.
- **Node.js 20 or newer** (LTS), from [nodejs.org](https://nodejs.org/).
- **Git**, from [git-scm.com](https://git-scm.com/).
- On Windows: set your home Wi-Fi to **Private** (Settings > Network &
  internet > Wi-Fi > your network), so the TV can reach the computer.

Get this project (PowerShell on Windows, Terminal on macOS/Linux):

```sh
git clone https://github.com/CannedSpoon/Samsung-tv
cd Samsung-tv
git checkout claude/android-tv-debloat-homescreen-1o5gjy
python tv.py find
```

`python tv.py doctor` shows at any point what's ready and what's missing.

## 1. Developer Mode on the TV

1. On the TV: **Home > Apps**, scroll down, open **App Settings** (gear).
2. Type **1 2 3 4 5** on the remote (or the on-screen number pad).
3. **Developer mode: On**, **Host PC IP**: this computer's address
   (`python tv.py doctor` prints it), **OK**.
4. Restart the TV: hold the power button until it turns off, then turn it on.

## 2. Samsung's Tizen SDK (command line only)

From <https://download.tizen.org/sdk/Installer/tizen-sdk_10.0/> download the
`web-cli_Tizen_SDK_10.0_…` installer for your system (`windows-64.exe`,
`macos-64.bin` or `ubuntu-64.bin`). Read Samsung's licence, then install it to a
folder named `tizen-studio` in your user folder:

- **Windows** (PowerShell, in your Downloads folder):
  ```powershell
  .\web-cli_Tizen_SDK_10.0_windows-64.exe --show-license
  .\web-cli_Tizen_SDK_10.0_windows-64.exe --accept-license $HOME\tizen-studio
  ```
- **macOS / Linux**:
  ```sh
  chmod +x web-cli_Tizen_SDK_10.0_*.bin
  ./web-cli_Tizen_SDK_10.0_*.bin --show-license
  ./web-cli_Tizen_SDK_10.0_*.bin --accept-license ~/tizen-studio
  ```
  On Apple Silicon the tools run under Rosetta 2
  (`softwareupdate --install-rosetta` if you don't have it).

About 330 MB, no admin rights needed. If you install it somewhere else, set
`TIZEN_HOME` to that folder (`$env:TIZEN_HOME="D:\tizen-studio"` in PowerShell,
`export TIZEN_HOME=...` on macOS/Linux) before running `tv.py`.

## 3. Samsung's certificate tool

- **Windows** (PowerShell):
  ```powershell
  git clone https://github.com/Samsung/tizen-agent-skills $HOME\tizen-agent-skills
  git -C $HOME\tizen-agent-skills checkout 06f07eca4ce44985be1c2944d58466a82eb15692
  node $HOME\tizen-agent-skills\tizen-sdk-skills\common\lib\cli\sdk-init-cli.js $HOME\tizen-studio
  ```
- **macOS / Linux**:
  ```sh
  git clone https://github.com/Samsung/tizen-agent-skills ~/tizen-agent-skills
  git -C ~/tizen-agent-skills checkout 06f07eca4ce44985be1c2944d58466a82eb15692
  node ~/tizen-agent-skills/tizen-sdk-skills/common/lib/cli/sdk-init-cli.js ~/tizen-studio
  ```

The `checkout` pins the version Glass Home tested.

## 4. Your Samsung certificate

With the TV on and Developer Mode on:

```sh
python tv.py doctor                 # everything except "Signing profile" should be ok
python tv.py cert --country GB      # your 2-letter country code
```

This reads the TV's device ID, opens a Samsung sign-in in your browser (you
have 5 minutes), makes the certificates and registers them for signing. The
password is generated for you and kept in `.quiet-home-secrets` in your user
folder, never in this project.

**Back up two files** it names at the end (`author.p12` and
`cert-password.env`): every update must be signed with the same author
certificate. Running `cert` again keeps them; `cert --new-tv` remakes only the
part tied to the TV, for a different TV.

## 5. Install, then make it the start screen

```sh
python tv.py apps        # check the dock app IDs; edit launcher/js/config.js if needed
python tv.py install     # builds, installs, opens it, checks it's on screen
python tv.py autostart   # pin it, Start with Smart Hub Home off, Autorun Last App on, power-on test
```

Then turn **Developer Mode off** again (step 1, Off, restart the TV). Quiet Home
keeps working; turn Developer Mode on only to update it (change something, then
`python tv.py install` again).

To remove it: `python tv.py uninstall`, or on the TV **Apps > App Settings >
Quiet Home > Delete**. `python tv.py restore` offers this too.

## Troubleshooting

- **`sdb couldn't connect`:** Developer Mode is off, Host PC IP doesn't match
  this computer (`python tv.py doctor`), or the TV wasn't restarted after
  turning it on. On Windows, check the network is set to Private.
- **Certificate or device ID error on install:** run `python tv.py cert
  --country XX --new-tv` with the TV on, then install again.
- **`tizen` or `sdb` not found:** the SDK isn't in `tizen-studio` in your user
  folder; set `TIZEN_HOME` (step 2).
- **Windows, user folder name has spaces or accents:** if a `tizen` command
  fails on a path, install the SDK to `C:\tizen-studio` instead (it's found
  there automatically).
- **An app is missing from the dock:** it isn't installed, or its ID differs;
  put the ID from `python tv.py apps` first in its `ids` in
  `launcher/js/config.js`, then `python tv.py install` again.
- **A dock tile won't open its app:** the tile shows the app IDs it tried and
  the TV's error. Find the app's IDs with `python tv.py apps plus` (any word
  from its name), test them with `python tv.py launch <id> <id>`, put the one
  that opens first in that app's `ids` in `launcher/js/config.js`, then
  `python tv.py install` again.
- **A Samsung OS upgrade removed it:** `python tv.py install` again.
