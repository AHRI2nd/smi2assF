# smi2ass

**smi2ass** converts SAMI subtitle files (`.smi`) to SubStation Alpha (`.ass`).
This fork provides a drag-and-drop desktop app for macOS and Windows, as well
as a command-line interface.

## Features

- Convert dropped subtitle files or folders immediately. Folders are searched
  recursively.
- Show the desktop interface in Korean or English based on the device language.
- When adding a folder, search its subfolders recursively. The desktop app
  accepts files whose extension is exactly `.smi` or `.SMI`.
- Write each `.ass` beside its source `.smi`; source files are left in place.
- Convert SAMI files containing multiple languages into separate language
  outputs, such as `episode.eng.ass` and `episode.kor.ass`.
- In the desktop app, preserve existing `.ass` files by default. Missing
  language outputs are still created when only some outputs already exist.
  Enable **기존 ASS 파일 덮어쓰기** to replace existing outputs.
- Repair recognized SAMI markup and timestamp damage, and show repairs, skipped
  cues, existing outputs, and file errors in the app or CLI.

## Download

Run a build from the repository's
[GitHub Actions](https://github.com/AHRI2nd/smi2assF/actions) page. The
**CI checks** workflow runs tests on pushes to `master` and pull requests. To
build release files, open **Build release draft**, select **Run workflow**, and
enter a release tag such as `v1.2.0`. The workflow builds Apple Silicon macOS
and Windows x86-64 versions from `master`, then creates a draft release. Intel
Mac builds are not provided.

Select **verify_only** to run the same package builds and smoke tests without
creating a release draft. Windows builds verify installation, the installed app,
and uninstallation. Installer diagnostic logs are saved as a separate artifact
on both successful and failed runs.

| Artifact | Build |
| --- | --- |
| `smi2assF.osx-arm64.dmg` | macOS disk image containing `smi2assF.app` |
| `smi2assF.windows-x86_64.exe` | Windows installer that installs `smi2assF.exe` |
| `*.sha256` | SHA-256 checksums for the release files |

Actions artifacts are uploaded as individual files without ZIP packaging.
Download the `.dmg` or `.exe` directly. The draft release also contains these
files and their checksums as direct downloads.
Review the draft and publish it from the
[Releases page](https://github.com/AHRI2nd/smi2assF/releases) when it is ready.

The macOS `.dmg` opens as a disk image containing `smi2assF.app`. The release
workflow requires Developer ID signing and Apple notarization for both the app
and the disk image. It validates their stapled tickets and Gatekeeper acceptance
before uploading them. Signing credentials must be configured as described below;
missing credentials or failed notarization stop the release build.
Windows may show a SmartScreen warning for the unsigned executable.

## Use the desktop app

1. Open `smi2assF.app` on macOS. On Windows, run
   `smi2assF.windows-x86_64.exe` to install the app, then launch `smi2assF`
   from the Start menu. The installer places `smi2assF.exe` in your local
   `%LOCALAPPDATA%\Programs\smi2assF` folder and adds an uninstaller.
2. Drag `.smi` or `.SMI` files or folders into the drop area. Conversion starts
   immediately, and results are written beside each source file.
3. Turn on **기존 ASS 파일 덮어쓰기** at the bottom only when existing outputs
   should be replaced. The desktop interface follows the device language and
   uses Korean or English.

Folders are searched recursively. Other extensions, including mixed-case
variants such as `.Smi`, are not added by the desktop app. When a source
contains multiple languages, the app checks each language output separately:
existing files are preserved by default while missing language outputs are
created.

## Command-line use

Python 3.14 is required. Install the runtime dependencies, then pass one or
more input paths to the converter:

```sh
python3.14 -m pip install -r requirements.txt
python3.14 smi2ass.py episode.smi
python3.14 smi2ass.py episode-one.smi episode-two.smi
```

The CLI writes outputs beside the input files. Single-language output uses
`.kor.ass` by default; multilanguage input produces one file per detected
language. The CLI overwrites existing outputs. It accepts the paths you
provide directly; extension filtering and recursive folder discovery are
desktop-app features.

## Recovery and diagnostics

The converter repairs recognized, unambiguous damage, including:

- A missing `</SYNC>` before the next `SYNC` cue.
- A closing `SYNC` tag without a matching open tag.
- Unclosed supported formatting tags within a cue.
- Recognized punctuation after an integer timestamp, for example
  `Start=479501??`.

Cues with missing, negative, or ambiguous timestamps are skipped while other
cues and input files continue. Unsupported font colors are reported and left
unapplied. The app shows repair, skip, and file-error details in its history;
the CLI prints diagnostics and returns a nonzero status if a cue was skipped or
a file could not be processed.

Supported subtitle markup includes `<p>`, `<br>`, `<b>`, `<i>`, `<u>`, `<s>`,
`<font>`, and `<rt>` (Ruby tags).

## Development

Use Python 3.14 on macOS and Python 3.13 on Windows. Python 3.13 keeps Windows
Tk on Tcl 8.6, which is required by the bundled drag-and-drop runtime. A Python
build with Tk support is needed to run the desktop
interface. Install development dependencies, run the tests, and launch the GUI:

```sh
python3.14 -m pip install -r requirements-dev.txt
python3.14 -m pytest -q
python3.14 smi2ass_gui.py
```

To package the app locally, use Python 3.14 with Tk support on macOS or Python
3.13 on Windows:

```sh
PYTHON=python3.14 bash install.sh
bash build.sh
```

On Windows, use `PYTHON=python` with Python 3.13 selected in `PATH`.

The build scripts support Apple Silicon macOS and Windows x86-64. Pushes to
`master` and pull requests run tests only. The manual release workflow builds
both applications from `master`, runs the test suite, smoke-tests each app, and
creates a draft release with SHA-256 checksums.
Enable **verify_only** when validating packaging changes without creating a draft.

### Apple signing for GitHub releases

An Apple Developer Program membership and a **Developer ID Application**
certificate with its private key are required. Export that identity from Keychain
Access as a password-protected `.p12` file. An Apple Development, Apple Distribution,
or Developer ID Installer certificate is not suitable for this app bundle.
[Apple's Developer ID certificate guide](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/)
explains the certificate requirements.

Configure these repository Actions secrets in **Settings → Secrets and variables
→ Actions**:

| Secret | Value |
| --- | --- |
| `APPLE_CERTIFICATE_P12_BASE64` | Base64 encoding of the `.p12` containing the certificate and private key |
| `APPLE_CERTIFICATE_PASSWORD` | Password used when exporting that `.p12` |
| `APPLE_ID` | Apple Account email with access to the developer team |
| `APPLE_TEAM_ID` | The 10-character Team ID associated with the certificate |
| `APPLE_APP_SPECIFIC_PASSWORD` | An app-specific password generated for that Apple Account, not its account password |

The certificate can be uploaded without printing its contents:

```sh
base64 -i /absolute/path/DeveloperID.p12 | gh secret set APPLE_CERTIFICATE_P12_BASE64 --repo AHRI2nd/smi2assF
gh secret set APPLE_CERTIFICATE_PASSWORD --repo AHRI2nd/smi2assF
gh secret set APPLE_ID --repo AHRI2nd/smi2assF
gh secret set APPLE_TEAM_ID --repo AHRI2nd/smi2assF
gh secret set APPLE_APP_SPECIFIC_PASSWORD --repo AHRI2nd/smi2assF
```

The last four commands prompt for their values. Certificate files, private keys,
and passwords belong in GitHub Secrets, not source control or diagnostic artifacts.
The app-specific password is created at [account.apple.com](https://account.apple.com/)
under **Sign-In and Security → App-Specific Passwords**.

The macOS job imports the identity into a temporary keychain, confirms its
certificate type and Team ID, and validates the notarization credentials before
building. PyInstaller signs the collected native binaries with a secure timestamp
and hardened runtime. The workflow notarizes and staples the app, creates and signs
the DMG, then notarizes and staples the DMG. It mounts the final disk image and
checks the enclosed app's ticket, signature, Gatekeeper assessment, and startup.
The SHA-256 checksum is generated after all signing and stapling steps.
[PyInstaller signing documentation](https://pyinstaller.org/en/stable/feature-notes.html#macos-binary-code-signing),
[Apple notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow)

Each notarization wait is limited to 20 minutes, with progress output every 30
seconds. Apple's queue can exceed that limit; in that case the job fails and the
submission ID remains in the `macos-notarization-diagnostics` artifact. The service
may continue processing after the local wait times out. The workflow preserves
notary logs when available and always attempts to remove the temporary keychain.
It never uploads the keychain or certificate as a diagnostic artifact.

Use **verify_only** for the first run after configuring the secrets. This runs the
same signed packaging checks without creating a release draft. Both macOS and
Windows jobs must pass before publishing a release. Local `bash build.sh` builds
remain ad-hoc signed development packages unless `MACOS_RELEASE_SIGNING=1` and
the prepared signing environment are explicitly supplied.

## Project lineage and credits

This repository continues work from two earlier projects:

1. The original SAMI conversion implementation was derived from the
   [`service.subtitles.gomtv` Kodi add-on](https://github.com/hojel/service.subtitles.gomtv/tree/3a7342961e140eaf8250659b0ac6158ce5e6bc5c/resources/lib).
   The converter's source header identifies this upstream snapshot and commit.
2. [Trustin Lee's `smi2ass`](https://github.com/trustin/smi2ass) adapted that
   converter into a standalone project. Its README credits Trustin Lee with
   Ruby tag support, improved whitespace preservation, executable packaging,
   the Python 2 to Python 3 and BeautifulSoup 3 to BeautifulSoup 4 updates, and
   cleanup. The converter source retains its 2018 copyright notice for Trustin
   Heuiseung Lee and other contributors.

Additional contributions recorded in this repository include:

- [goodGhost](https://github.com/good-ghost): Python 3.7 compatibility and a
  BeautifulSoup compatibility fix.
- Tsukimori Ahri, current fork maintainer: Python 3.14 modernization, SAMI
  recovery and diagnostics, the desktop interface, recursive folder handling,
  and macOS/Windows GitHub Actions packaging.

The source code is licensed under the GNU General Public License, version 2 or
any later version, as stated in the source notices. See [LICENSE.txt](LICENSE.txt)
for the license text. Please retain the existing copyright and license notices
when redistributing the source.
