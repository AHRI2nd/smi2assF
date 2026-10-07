import locale
import os
import stat
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {'.smi', '.SMI'}

UI_TEXT = {
    'ko': {
        'window_title': 'SMI to ASS 변환기',
        'drop_hint': '.smi 파일 또는 폴더를 여기에 놓으세요',
        'overwrite': '기존 ASS 파일 덮어쓰기',
        'status_busy_add': '변환이 끝날 때까지 기다려 주세요.',
        'status_no_files': '.smi 또는 .SMI 파일을 찾지 못했습니다.',
        'status_scan_errors': '{count}개 위치에서 파일을 읽지 못했습니다.',
        'status_converting': '{count}개 파일을 변환하고 있습니다…',
        'status_done': '완료: {total}개 파일 · ASS 생성 {outputs}개 · 기존 파일 유지 {existing}개 · 오류 {failed}개 · 읽기 실패 {scan_errors}개',
        'dialog_busy_title': '변환 중',
        'dialog_busy_message': '변환이 끝난 뒤 앱을 닫아 주세요.',
    },
    'en': {
        'window_title': 'SMI to ASS Converter',
        'drop_hint': 'Drop .smi files or folders here',
        'overwrite': 'Overwrite existing ASS files',
        'status_busy_add': 'Wait for the current conversion to finish.',
        'status_no_files': 'No .smi or .SMI files found.',
        'status_scan_errors': 'Could not read files from {count} location(s).',
        'status_converting': 'Converting {count} file(s)…',
        'status_done': 'Complete: {total} file(s) · created {outputs} ASS file(s) · kept {existing} existing file(s) · errors {failed} · unreadable locations {scan_errors}',
        'dialog_busy_title': 'Conversion in progress',
        'dialog_busy_message': 'Wait for conversion to finish before closing the app.',
    },
}


def detect_ui_language(device_locale=None):
    """Use Korean for Korean device locales and English for all others."""
    candidates = [device_locale] if device_locale else []
    if not candidates:
        message_category = getattr(locale, 'LC_MESSAGES', None)
        if message_category is not None:
            try:
                candidates.append(locale.getlocale(message_category)[0])
            except (TypeError, ValueError):
                pass
        try:
            candidates.append(locale.getlocale()[0])
        except (TypeError, ValueError):
            pass
        candidates.extend((os.environ.get('LC_ALL'), os.environ.get('LC_MESSAGES'), os.environ.get('LANG')))

    for candidate in candidates:
        if candidate:
            language = candidate.split('.', 1)[0].split('@', 1)[0]
            language = language.replace('-', '_').split('_', 1)[0].casefold()
            return 'ko' if language == 'ko' else 'en'
    return 'en'


def localized_text(key, language, **values):
    """Return a formatted UI message in the selected supported language."""
    messages = UI_TEXT['ko' if language == 'ko' else 'en']
    return messages[key].format(**values)


@dataclass(frozen=True)
class SmiConversionSummary:
    total: int
    outputs: int
    existing: int
    failed: int


def convert_smi_files(paths, overwrite=False):
    """Convert each dropped SMI file and collect a compact UI summary."""
    from smi2ass import convert_smi_file

    outputs = existing = failed = 0
    paths = tuple(paths)
    for path in paths:
        try:
            result = convert_smi_file(path, overwrite=overwrite)
        except Exception:
            failed += 1
            continue
        outputs += len(result.outputs)
        existing += len(result.skipped_existing)
    return SmiConversionSummary(
        total=len(paths), outputs=outputs, existing=existing, failed=failed,
    )


@dataclass(frozen=True)
class SmiScanResult:
    files: tuple
    errors: tuple


def scan_smi_files(paths):
    found = {}
    errors = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            continue
        except OSError as error:
            errors.append((path, error))
            continue

        if stat.S_ISDIR(mode):
            def on_walk_error(error, root=path):
                errors.append((Path(error.filename or root), error))

            for directory, _, filenames in os.walk(path, onerror=on_walk_error):
                for filename in filenames:
                    candidate = Path(directory) / filename
                    if candidate.suffix in SUPPORTED_SUFFIXES:
                        resolved = candidate.resolve()
                        found[os.path.normcase(str(resolved))] = resolved
        elif stat.S_ISREG(mode) and path.suffix in SUPPORTED_SUFFIXES:
            candidate = path
            resolved = candidate.resolve()
            found[os.path.normcase(str(resolved))] = resolved

    return SmiScanResult(
        files=tuple(sorted(found.values(), key=lambda item: str(item).casefold())),
        errors=tuple(errors),
    )


def collect_smi_files(paths):
    """Return supported subtitle files while preserving the legacy list API."""
    return list(scan_smi_files(paths).files)
