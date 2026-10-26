# Installing Quiet Home

Samsung only installs apps signed with a free Samsung certificate made for your
TV, so the first install takes about an hour. These steps follow
[Glass Home's install guide](https://github.com/victaphu/glass-home-samsung-tv/blob/main/docs/INSTALL.md),
which was tested on a 2023 Samsung Q70C (Tizen 8) from a Mac. Menu names can
differ a little on other models.

You need the computer on the same network as the TV, a free
[Samsung account](https://account.samsung.com/), Python 3, Node.js 20+ and Git.
macOS or Linux; on Windows use WSL.

## 1. Developer Mode

1. On the TV: **Home > Apps**, scroll down, open **App Settings** (gear).
2. Type **1 2 3 4 5** on the remote (or the on-screen number pad).
3. **Developer mode: On**, **Host PC IP**: this computer's address
   (`python3 tv.py info` prints it if they don't match), **OK**.
4. Restart the TV: hold the power button until it turns off, then turn it on.

## 2. Samsung's Tizen SDK (command line only)

Download the `web-cli_Tizen_SDK_10.0_<your OS>` installer from
<https://download.tizen.org/sdk/Installer/tizen-sdk_10.0/>, then:

```sh
chmod +x web-cli_Tizen_SDK_10.0_*.bin
./web-cli_Tizen_SDK_10.0_*.bin --show-license        # read Samsung's licence
./web-cli_Tizen_SDK_10.0_*.bin --accept-license ~/tizen-studio
```

About 330 MB, no admin password. On Apple Silicon the tools run under Rosetta 2.

## 3. Samsung's certificate tool

```sh
git clone https://github.com/Samsung/tizen-agent-skills ~/tizen-agent-skills
git -C ~/tizen-agent-skills checkout 06f07eca4ce44985be1c2944d58466a82eb15692   # version Glass Home tested
node ~/tizen-agent-skills/tizen-sdk-skills/common/lib/cli/sdk-init-cli.js ~/tizen-studio
```

## 4. Settings file and device ID

```sh
cp scripts/tizen-env.example.sh scripts/tizen-env.sh
. scripts/tizen-env.sh
sdb connect "$TV" && sdb -s "$TV" shell 0 getduid
```

Put the printed ID in `scripts/tizen-env.sh` as `DUID=`. (`python3 tv.py backup`
also saves it in the backup folder as `duid.txt`.)

## 5. Your Samsung certificate

```sh
. scripts/tizen-env.sh
mkdir -p ~/.quiet-home-secrets && chmod 700 ~/.quiet-home-secrets
(umask 077; printf 'TIZEN_CERTIFICATE_PASSWORD=%sAa1\n' "$(openssl rand -base64 30 | tr -dc 'A-Za-z0-9' | cut -c1-20)" > ~/.quiet-home-secrets/cert-password.env)

node "$CERTCLI" generate-samsung-author --profile-name "$PROFILE" --identity "Quiet Home" --country <2-letter country> --password-file ~/.quiet-home-secrets/cert-password.env
node "$CERTCLI" generate-samsung-distributor --profile-name "$PROFILE" --duid-list "$DUID" --privilege Public --password-file ~/.quiet-home-secrets/cert-password.env

cp "$CA_DIR/vd_tizen_dev_public2.crt" "$CERT_DIR/"
PW="$(sed -n 's/^TIZEN_CERTIFICATE_PASSWORD=//p' ~/.quiet-home-secrets/cert-password.env)"
tizen security-profiles add -n "$PROFILE" -A -a "$CERT_DIR/author.p12" -p "$PW" \
  -d "$CERT_DIR/distributor.p12" -dp "$PW" -dc "$CERT_DIR/vd_tizen_dev_public2.crt"
unset PW
tizen cli-config "profiles.path=$TIZEN_DATA/profile/profiles.xml"
```

The first command opens a Samsung sign-in in your browser. Certificates are
valid for a year. **Back up `author.p12` and the password file**: updates must
be signed with the same author certificate.

## 6. Install, then make it the start screen

```sh
python3 tv.py apps        # check the dock app IDs; edit launcher/js/config.js if needed
python3 tv.py install     # build, install, open, check it's on screen, photo
python3 tv.py autostart   # pin it, Start with Smart Hub Home off, Autorun Last App on, power-on test
```

Then turn **Developer Mode off** again (step 1, Off, restart). Quiet Home keeps
working; turn Developer Mode on only to update it.

## Troubleshooting

- **`sdb connect` fails:** Developer Mode is off, Host PC IP doesn't match this
  computer, or the TV wasn't restarted after turning it on.
- **Certificate or device ID error on install:** the `DUID` in the distributor
  certificate must match `sdb shell 0 getduid`; `tizen security-profiles list`
  should show your profile as active.
- **An app is missing from the dock:** it isn't installed, or its ID differs;
  put the ID from `python3 tv.py apps` first in its `ids` in
  `launcher/js/config.js`, then `python3 tv.py install` again.
- **A Samsung OS upgrade removed it:** reinstall the same way.
