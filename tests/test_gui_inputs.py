from pathlib import Path

from smi2ass_gui_support import collect_smi_files


def test_collect_smi_files_finds_only_smi_extensions_recursively(tmp_path):
    root = tmp_path / 'Season 1'
    nested = root / 'Disc 1'
    nested.mkdir(parents=True)
    lower = root / 'Episode 1.smi'
    upper = nested / 'Episode 2.SMI'
    extensionless = nested / 'Episode 3'
    mixed_case = nested / 'Episode 4.SmI'
    other = nested / 'cover.jpg'
    for path in (lower, upper, extensionless, mixed_case, other):
        path.write_text('fixture', encoding='utf-8')

    result = collect_smi_files([root])

    expected = sorted([lower.resolve(), upper.resolve()], key=lambda path: str(path).casefold())
    assert result == expected


def test_collect_smi_files_deduplicates_files_and_folders(tmp_path):
    root = tmp_path / 'input'
    root.mkdir()
    source = root / 'episode.smi'
    source.write_text('fixture', encoding='utf-8')

    result = collect_smi_files([source, root, source])

    assert result == [source.resolve()]
