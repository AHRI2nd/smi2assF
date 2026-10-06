# smi2ass

`smi2ass` converts SAMI subtitle files (`.smi`) to SSA/ASS subtitle files
(`.ass`). Python 3.14 is required.

## Install and run

Install the current runtime dependencies with Python 3.14:

```sh
python3.14 -m pip install -r requirements.txt
python3.14 smi2ass.py movie.smi
```

Pass one or more input files to convert them in one run:

```sh
python3.14 smi2ass.py movie-one.smi movie-two.smi
```

The converter writes an ASS file beside each input. A single-language input
uses the `.kor.ass` suffix by default. When a file contains multiple languages,
the output suffix uses the detected language code, such as `.eng.ass` and
`.kor.ass`.

## Recovery and diagnostics

The converter automatically repairs unambiguous SAMI damage, including a
missing `</SYNC>` before the next `SYNC` cue, unmatched closing `SYNC` tags,
unclosed supported formatting tags, and recognized punctuation after an
integer timestamp such as `Start=479501??`. Each repair is printed to stderr
with the input path and source line when available.

When a timestamp is missing, negative, or too ambiguous to recover, that cue
is skipped and reported. Other cues and input files continue to be converted.
The CLI prints a per-file count of repairs and skipped cues. It exits with:

- `0` when every cue is converted or repaired.
- `1` when an input file cannot be read or any cue must be skipped.
- `2` when command-line arguments are invalid, such as when no input file is
  provided.

Unsupported font colors are left unapplied and reported; subtitle text is
preserved. Supported tags include `<p>`, `<br>`, `<b>`, `<i>`, `<u>`, `<s>`,
`<font>`, and `<rt>` (Ruby tags).

## Build and test

Use Python 3.14 to prepare the isolated build environment, run the test suite,
and create a one-file executable:

```sh
./install.sh
./build.sh
```

On Windows, run the scripts in Bash and set `PYTHON=python` if the interpreter
is not available as `python3.14`. The executable and SHA-256 file are written
to `build/dist/`. The build includes an end-to-end smoke test using a small
synthetic subtitle. The build environment is isolated at
`build/venv-py314/`.

Run the automated tests without building the executable:

```sh
python3.14 -m pip install -r requirements-dev.txt
python3.14 -m pytest
```

GitHub Actions runs the test and executable build on Linux, macOS, and Windows
with Python 3.14. Each run uploads the executable and checksum as workflow
artifacts. Pushing a `v*` tag creates a GitHub release with the three platform
builds and their checksums.

## License and credits

This project is distributed under the GNU General Public License, version 2
or (at your option) any later version. The original conversion logic was
forked from the [GomTV subtitle add-on](https://github.com/hojel/service.subtitles.gomtv).
