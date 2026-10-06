# smi2ass

`smi2ass` converts SAMI subtitle files to SSA/ASS. The desktop app accepts
`.smi` and `.SMI` files on macOS and Windows.

## Use the desktop app

Open the macOS `.app` or Windows `.exe`, then drag one or more subtitle files
or folders into the drop area. You can also choose files or folders with the
buttons in the app. Folders are searched recursively; only files ending in
`.smi` or `.SMI` are added.

Each `.ass` file is written beside its source subtitle. Existing output files
are skipped by default. Select **Overwrite existing ASS files** before
converting if you want to replace them. Repairs, skipped cues, and file errors
appear in the conversion list and history area.

The app does not change or move the original subtitle files. Multilanguage
inputs produce one ASS file per detected language, for example
`episode.eng.ass` and `episode.kor.ass`.

## Download builds

GitHub Actions builds the app on Windows and macOS for Apple Silicon and Intel
Macs. Open the repository's **Actions** page, select a successful **Desktop
builds** run, and download the artifact for your platform:

- `smi2ass-macos-arm64`: macOS Apple Silicon `.app` archive.
- `smi2ass-macos-x86_64`: macOS Intel `.app` archive.
- `smi2ass-windows-x86_64`: Windows `.exe`.

Extract the macOS archive before opening the `.app`. Builds are not signed or
notarized by default, so macOS may require Control-clicking the app and
choosing **Open** the first time. Windows may show a SmartScreen warning for
the unsigned `.exe`.

The workflow builds on pushes to `master`, pull requests, manual dispatches,
and `v*` tags. Tag builds are attached to a GitHub release.

## Command-line use

The original CLI remains available for explicit input paths:

```sh
python3.14 -m pip install -r requirements.txt
python3.14 smi2ass.py movie.smi
python3.14 smi2ass.py movie-one.smi movie-two.smi
```

The CLI writes each ASS file beside its input. A single-language input uses
`.kor.ass` by default. Multilanguage output uses the detected language codes.

## Recovery and diagnostics

The converter automatically repairs unambiguous SAMI damage, including a
missing `</SYNC>` before the next `SYNC` cue, unmatched closing `SYNC` tags,
unclosed supported formatting tags, and recognized punctuation after an
integer timestamp such as `Start=479501??`.

When a timestamp is missing, negative, or too ambiguous to recover, that cue
is skipped while other cues and input files continue. Unsupported font colors
are left unapplied and reported; subtitle text is preserved. Supported tags
include `<p>`, `<br>`, `<b>`, `<i>`, `<u>`, `<s>`, `<font>`, and `<rt>` (Ruby
tags).

## Development

Use Python 3.14 with Tk support to run the desktop app from source:

```sh
python3.14 -m pip install -r requirements-dev.txt
python3.14 smi2ass_gui.py
```

Run the test suite with `python3.14 -m pytest`. GitHub Actions also runs the
tests and packages the platform app. The package build is performed by the
workflow so each app is created on its target operating system.

## License and credits

This project is distributed under the GNU General Public License, version 2
or (at your option) any later version. The original conversion logic was
forked from the [GomTV subtitle add-on](https://github.com/hojel/service.subtitles.gomtv).
