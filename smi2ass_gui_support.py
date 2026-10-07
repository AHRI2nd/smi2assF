import locale
import os
import stat
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {'.smi', '.SMI'}

UI_TEXT = {
    'ko': {
        'window_title': 'SMI to ASS 변환기',
        'heading': 'SMI 자막을 ASS로 변환',
        'intro': '파일이나 폴더를 아래 영역에 끌어 놓으세요. 폴더는 하위 폴더까지 검색합니다.',
        'drop_hint': '여기에 SMI 파일 또는 폴더를 놓으세요',
        'file_button': '파일 선택',
        'folder_button': '폴더 선택',
        'remove_button': '선택 제거',
        'clear_button': '전체 비우기',
        'file_column': '파일',
        'path_column': '위치',
        'status_column': '상태',
        'status_pending': '대기',
        'history': '변환 내역',
        'smi_filter': 'SMI 자막',
        'all_files': '모든 파일',
        'overwrite': '기존 ASS 파일 덮어쓰기',
        'start': '변환 시작',
        'status_add_hint': '변환할 .smi 파일을 추가하세요.',
        'status_busy_add': '현재 변환이 끝난 뒤 파일을 추가해 주세요.',
        'status_added': '{count}개 파일을 목록에 추가했습니다.',
        'status_no_files': '.smi 또는 .SMI 파일을 찾지 못했습니다.',
        'status_duplicate': '이미 목록에 있는 파일입니다.',
        'status_scan_errors': '{added}개 파일 추가, {errors}개 위치 검색 실패',
        'status_remaining': '{count}개 파일이 목록에 남았습니다.',
        'status_converting': '변환 중입니다. {completed} / {total}',
        'status_done': '완료: {completed} / {total}, 복구: {repaired}, 자막 건너뜀: {skipped}, 기존 결과 건너뜀: {existing}, 오류: {failed}',
        'dialog_select_files': 'SMI 파일 선택',
        'dialog_select_folder': '자막 폴더 선택',
        'log_folder_error': '{path}: 폴더 검색 오류: {error}',
        'log_conversion_start': '변환을 시작합니다. 기존 ASS 덮어쓰기: {overwrite}',
        'yes': '예',
        'no': '아니요',
        'status_error': '오류',
        'status_partial_existing': '완료 (일부 유지)',
        'status_existing': '기존 ASS로 건너뜀',
        'status_skipped_cues': '일부 자막 건너뜀',
        'status_complete': '완료',
        'log_error': '{path}: 오류: {error}',
        'log_existing_kept': '{path}: 기존 결과를 유지했습니다.',
        'log_output': '{source} → {output}',
        'log_diagnostic': '{path}:{line} [{severity}] {message}',
        'dialog_busy_title': '변환 중',
        'dialog_busy_message': '변환이 끝난 뒤 앱을 닫아 주세요.',
    },
    'en': {
        'window_title': 'SMI to ASS Converter',
        'heading': 'Convert SMI subtitles to ASS',
        'intro': 'Drop files or folders below. Folders are searched recursively.',
        'drop_hint': 'Drop SMI files or folders here',
        'file_button': 'Choose Files',
        'folder_button': 'Choose Folder',
        'remove_button': 'Remove Selected',
        'clear_button': 'Clear All',
        'file_column': 'File',
        'path_column': 'Location',
        'status_column': 'Status',
        'status_pending': 'Pending',
        'history': 'Conversion History',
        'smi_filter': 'SMI subtitles',
        'all_files': 'All files',
        'overwrite': 'Overwrite existing ASS files',
        'start': 'Start Conversion',
        'status_add_hint': 'Add .smi files to convert.',
        'status_busy_add': 'Wait for the current conversion to finish before adding files.',
        'status_added': 'Added {count} file(s) to the list.',
        'status_no_files': 'No .smi or .SMI files found.',
        'status_duplicate': 'These files are already in the list.',
        'status_scan_errors': 'Added {added} file(s); failed to scan {errors} location(s).',
        'status_remaining': '{count} file(s) remain in the list.',
        'status_converting': 'Converting: {completed} / {total}',
        'status_done': 'Complete: {completed} / {total}, repaired: {repaired}, cues skipped: {skipped}, existing outputs skipped: {existing}, errors: {failed}',
        'dialog_select_files': 'Choose SMI files',
        'dialog_select_folder': 'Choose subtitle folder',
        'log_folder_error': '{path}: folder scan error: {error}',
        'log_conversion_start': 'Conversion started. Overwrite existing ASS: {overwrite}',
        'yes': 'Yes',
        'no': 'No',
        'status_error': 'Error',
        'status_partial_existing': 'Complete (some kept)',
        'status_existing': 'Skipped (ASS exists)',
        'status_skipped_cues': 'Some cues skipped',
        'status_complete': 'Complete',
        'log_error': '{path}: error: {error}',
        'log_existing_kept': '{path}: kept existing output.',
        'log_output': '{source} → {output}',
        'log_diagnostic': '{path}:{line} [{severity}] {message}',
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
