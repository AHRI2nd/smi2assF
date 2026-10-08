# GUI Design and Dark Mode Implementation Plan

> **For agentic workers:** 실행 승인이 주어지면 `superpowers:executing-plans`를 적용해 아래 작업을 순서대로 진행한다. 사용자의 현재 브랜치·로컬 작업 지침을 따른다.

**Goal:** 작은 드래그앤드롭 변환 화면을 정돈하고 macOS/Windows 시스템 다크모드를 지원한다.

**Architecture:** 현재 Tkinter/ttk와 변환 워커를 유지한다. OS 테마 탐지·색상·변경 감지는 작은 테마 모듈로 분리하고, UI는 상태와 팔레트를 조합해 기존 위젯을 갱신한다. 변환 로직과 테마 로직은 독립시킨다.

**Tech Stack:** Python, Tkinter/ttk, tkinterdnd2 0.6.3, 표준 라이브러리 winreg/ctypes, pytest, 기존 PyInstaller·Inno Setup 빌드.

**Spec:** [디자인 및 지원 설계안](../specs/2026-10-08-gui-design-dark-mode.md)

## Global Constraints

- 기본 창 `400×280`, 최소 창 `320×260`을 유지한다. 고배율 글꼴에서 공간이 부족하면 실제 요청 크기에 맞춰 최소 크기만 늘린다.
- 조작 요소는 드롭 영역과 `기존 ASS 파일 덮어쓰기` 체크박스다.
- 드롭하면 즉시 변환하는 동작을 유지한다.
- 기기 언어가 한국어이면 한국어, 나머지는 영어를 표시한다.
- 라이트·다크모드는 운영체제 설정을 자동으로 따른다.
- 기존 Tkinter/ttk, tkinterdnd2, PyInstaller, Inno Setup 구성을 사용한다.
- Windows 빌드는 Python 3.13/Tcl 8.6을 유지한다.
- 현재 브랜치에서 로컬 작업을 수행한다. 커밋·푸시는 사용자의 명시적 요청이 있을 때 수행한다.

## Review Focus

- 최소 창·긴 영어·다섯 자리 결과 수치·고배율에서도 체크박스와 다섯 결과 지표가 보여야 한다. 작업 1·4에서 검증한다.
- 아이콘/보조문 위에 드롭해도 같은 파일이 한 번만 처리되어야 한다. 작업 1·4에서 검증한다.
- 변환 중 테마 전환·드래그 이탈이 작업 상태나 덮어쓰기 값을 바꾸면 안 된다. 작업 3에서 검증한다.
- 지원하지 않는 Tk 명령·누락된 레지스트리·고대비·실패한 DWM 호출이 시작 오류를 일으키면 안 된다. 작업 2에서 검증한다.
- 종료 뒤 타이머가 실행되지 않아야 하고 실제 설치 앱도 정상 시작·제거되어야 한다. 작업 3·4에서 검증한다.

---

## 파일별 책임

| 파일 | 변경 |
|---|---|
| `smi2ass_gui.py` | 정돈된 드롭 화면, 상태 렌더링, 크기 대응, 테마 적용, DND 바인딩·종료 관리 |
| `smi2ass_gui_support.py` | 안내·보조·상태 문구의 한국어/영어 추가·분리 |
| `smi2ass_gui_theme.py` (신규) | 팔레트, OS 설정 감지, 기능 탐지, 네이티브 창 장식, 변경 감지 수명 |
| `tests/test_gui_startup.py` | 화면 구조 변경 반영 및 기존 자동 변환 회귀 확인 |
| `tests/test_gui_localization.py` | 새 문구와 결과 지표 확인 |
| `tests/test_gui_layout.py` (신규) | 크기·언어·모드·상태 조합의 실제 위젯 경계 확인 |
| `tests/test_gui_theme.py` (신규) | OS 분기·실패 fallback·고대비·팔레트 대비 확인 |
| `tests/test_gui_theme_lifecycle.py` (신규) | 변경 감지·변환 중 갱신·타이머 정리 확인 |
| `Transfer.md` | 검증 결과·런타임 차이·재발 방지 기록, 기존 ignore 유지 |

`build.sh`와 `.github/workflows/release.yml`은 기존 검증 경로로 사용한다. 번들 메타데이터 변경은 실제 패키지 검사에서 필요성이 확인될 때 작업 4에 포함한다.

## 작업 1: 작은 드롭 화면과 상태 표현

**Files:** Modify `smi2ass_gui.py`, `smi2ass_gui_support.py`, `tests/test_gui_startup.py`, `tests/test_gui_localization.py`; Create `tests/test_gui_layout.py`.

**Interfaces:**

- 기존 `Smi2AssApp.add_paths(paths)`와 `overwrite_existing` 값을 유지한다.
- `Smi2AssApp._render_drop_state()`는 현재 상태/결과를 로컬 문구로 표시한다.
- `Smi2AssApp._on_drop_enter(event)`/`_on_drop_leave(event)`는 문구·강조만 변경한다. TkinterDnD 계약에 맞는 action을 반환한다.
- `_on_drop`만 변환을 시작한다. 하위 아이콘·안내·보조문까지 동일 드롭 표면으로 처리하고 중복 변환을 방지한다.

- [ ] `test_gui_layout_keeps_all_content_visible`을 ko/en, 400×280/320×260, 대기/변환/완료/실패로 매개변수화한다. 모든 콘텐츠의 경계가 드롭 영역 안이며 체크박스의 높이가 요청 높이 이상인지 검사한다. 결과는 각 지표 99999까지 포함한다.
- [ ] `test_gui_result_copy_preserves_all_five_counts`에서 대상·생성·유지·변환 오류·읽기 실패가 서로 다른 값으로 모두 표시되는지 검사한다.
- [ ] `test_drop_on_child_surface_converts_once`와 `test_drop_leave_restores_previous_state`를 추가하고 기존 구조 고정 테스트를 사용자 동작 중심으로 갱신한다.
- [ ] `build/venv-py314/bin/python -m pytest tests/test_gui_startup.py tests/test_gui_localization.py tests/test_gui_layout.py -q`로 실패 원인을 확인한다.
- [ ] 설계안의 여백·폰트·얇은 테두리·Canvas 아이콘·짧은 문구를 구현한다. 결과 본문은 실제 가용 폭에 맞춰 최대 3줄까지 줄바꿈한다.
- [ ] 같은 명령으로 통과를 확인하고 macOS에서 대기/드래그/완료 화면을 한국어·영어로 육안 확인한다.

## 작업 2: OS 테마 감지와 팔레트

**Files:** Create `smi2ass_gui_theme.py`, `tests/test_gui_theme.py`; Modify `smi2ass_gui.py`.

**Interfaces:**

- `ThemeMode = Literal['light', 'dark', 'high_contrast']`.
- `ThemePalette`: frozen dataclass; 필드 `background`, `surface`, `text`, `muted`, `border`, `accent`는 색상 문자열이다.
- `detect_system_theme(root: tk.Misc) -> ThemeMode`: macOS 의미 색상 밝기 / Windows 앱 설정·고대비를 읽는다. 다른 플랫폼과 실패 시 `light`를 반환한다.
- `get_palette(root: tk.Misc, mode: ThemeMode) -> ThemePalette`: 일반 모드는 설계안의 팔레트, 고대비는 Windows 시스템 색상으로 반환한다.
- `configure_native_appearance(root: tk.Tk, mode: ThemeMode) -> None`: 지원 기능을 탐지하고 네이티브 창 외관을 적용한다. OS/Tcl API 실패를 시작 실패로 전파하지 않는다.
- `Smi2AssApp._apply_theme(mode: ThemeMode) -> None`: 기존 위젯·Canvas 항목·스타일 색만 갱신한다.

- [ ] 로컬과 패키지 Tk에서 `-appearance auto` 지원 및 라이트/다크 `systemWindowBackgroundColor` RGB 차이를 먼저 확인한다. 판별 기준은 16비트 RGB를 0~1로 정규화한 가중 밝기 `0.2126R + 0.7152G + 0.0722B < 0.5`로 정한다. 실제 두 모드 판별이 확인되어야 이 경로를 사용한다.
- [ ] `test_theme_detection_uses_app_preference`, `test_theme_detection_falls_back_when_preference_missing`, `test_high_contrast_overrides_dark`, `test_mac_appearance_is_capability_guarded`, `test_native_appearance_failure_does_not_abort_startup`을 추가한다. OS 조회 경계를 mock하여 각 반환 모드를 검사한다.
- [ ] `test_palette_text_and_focus_contrast`에서 본문/보조문 4.5:1, 강조 3:1 기준을 검사한다. 실제 상대 휘도 계산은 sRGB 선형화 후 수행한다.
- [ ] `build/venv-py314/bin/python -m pytest tests/test_gui_theme.py -q`로 예상 실패를 확인한다.
- [ ] 표준 라이브러리만 사용해 탐지와 지원 기능 분기를 구현한다. Windows `clam`은 앱 전용 스타일, macOS는 `aqua` 기본 컨트롤을 사용한다. OS 전용 모듈은 해당 OS 경로 안에서 불러온다.
- [ ] 위 테스트와 작업 1의 레이아웃 테스트를 두 모드로 실행한다. 실제 체크박스 선택/비선택/비활성/포커스 색을 확인한다.

## 작업 3: 실행 중 테마 변경과 수명 관리

**Files:** Modify `smi2ass_gui_theme.py`, `smi2ass_gui.py`; Create `tests/test_gui_theme_lifecycle.py`.

**Interfaces:**

- `ThemeWatcher(root: tk.Tk, on_change: Callable[[ThemeMode], None])`.
- `ThemeWatcher.start() -> None`: 초기 모드를 즉시 전달한다. macOS 지원 이벤트를 바인딩하고 필요한 플랫폼에 단일 2000ms 타이머·포커스 복귀 확인을 등록한다.
- `ThemeWatcher.stop() -> None`: 소유 타이머와 바인딩을 제거한다. 여러 번 호출해도 안전하다.
- `Smi2AssApp._dispose() -> None`: watcher 정리 후 root를 닫는다. 일반 종료와 `--smoke-test` 종료에 공통 사용한다. 변환 중 `_close`의 현재 동작은 유지한다.

- [ ] `test_watcher_delivers_initial_theme_without_event`, `test_watcher_applies_only_changed_mode`, `test_watcher_start_is_idempotent`, `test_watcher_stops_without_pending_callbacks`를 작성한다.
- [ ] `test_theme_change_preserves_busy_state_and_overwrite`에서 변환 중 테마를 바꾸고 작업 상태·덮어쓰기 값·결과 큐·DND 바인딩이 유지되는지 검사한다.
- [ ] `build/venv-py314/bin/python -m pytest tests/test_gui_theme_lifecycle.py tests/test_gui_startup.py -q`로 실패를 확인한다.
- [ ] 모든 위젯 갱신을 Tk 메인 스레드에서 수행한다. 드래그 상태를 포함한 기존 화면 상태에 새 팔레트를 적용하고 위젯을 재생성하지 않는다.
- [ ] 같은 테스트 통과 후 실제 OS 설정을 라이트→다크→라이트로 바꿔 대기·변환 중·완료 화면의 변경과 종료를 확인한다. OS 설정 변경은 사용자의 검증 환경에서 수행하고 종료 후 원래 설정으로 복구한다.

## 작업 4: 플랫폼·패키지 검증 및 기록

**Files:** `Transfer.md`, 검증에서 실제 원인이 확인된 파일만 수정. 신규 런타임·UI 프레임워크를 도입하지 않는다.

- [ ] macOS 직접 호스트 셸에서 `build/venv-py314/bin/python -m pytest -q`를 실행한다. GUI WindowServer 접근이 필요한 경우 직접 실행 권한을 사용하며 VS Code를 조작하지 않는다.
- [ ] `bash build.sh`로 실제 `.app`/DMG를 빌드한다. DMG 내부 `smi2assF.app`을 열어 두 테마·두 언어·8개 기본 조합 및 실제 Finder 드롭을 검증한다. 체크섬과 `--smoke-test` 종료 코드도 확인한다.
- [ ] macOS Retina와 Windows 100/150/200%에서 글꼴·줄바꿈·포커스·체크박스 영역을 확인한다. `test_gui_layout_expands_minimum_for_large_font`로 큰 글꼴의 요청 크기 확보를 검사한다.
- [ ] Windows 10/11 실제 화면에서 라이트·다크·앱/시스템 모드 혼합·고대비를 검증한다. CI runner의 창 생성 테스트만으로 육안 검증을 대체하지 않는다. 실행 환경이 없는 항목은 미검증으로 기록한다.
- [ ] 사용자가 푸시한 뒤 `.github/workflows/release.yml`의 `verify_only=true`로 해당 커밋의 두 플랫폼 패키징을 확인한다. 원격 실행 시 GH CLI/API만 사용한다.
- [ ] Windows 설치 파일 `smi2assF.windows-x86_64.exe` → 설치된 `smi2assF.exe` 실행 → 제거를 확인한다. 기존 제한 시간·정확한 인자 기록·설치 폴더 외부 진단 로그·유한 제거 대기를 유지한다.
- [ ] 두 플랫폼 빌드 단계·패키지 실행·업로드 성공 및 실제 다운로드 체크섬을 확인한다. 실패 단계는 로그에서 원인을 확인하고 해당 수정의 테스트·빌드를 다시 수행한다.
- [ ] `Transfer.md`에 확인한 Tk 기능·fallback·검증 환경·결과·미검증 항목을 기록한다. `.gitignore`의 `/Transfer.md` 제외를 유지한다.

## 결과 보고 기준

디자인 적용 결과, OS 자동 전환 결과, 자동 테스트 결과, 실제 패키지 및 수동 검증 결과를 각각 보고한다. 실행·설치 테스트와 실제 다크 색상 검증을 구분한다. 사용자 요청 전에는 이 계획의 제품 코드 변경·커밋·푸시를 시작하지 않는다.
