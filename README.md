# Prototype Dev Spike

`prototype-dev-spike` — стенд для управляемой генерации прототипов приложений с помощью OpenCode/LLM-агентов.

Проект проверяет не свободный чат с агентом, а воспроизводимый pipeline, в котором агент предлагает план и реализует изменения, а наш код контролирует границы, структуру, validation и итоговый отчет.

Основной контракт текущего workflow:

```text
samples/<slice>/run_input.json
→ runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход slice от requirements stage. `scenario_result.json` — основной машинно-читаемый итог для будущего UI/отчета.

## Основные принципы

- Pipeline-код не придумывает бизнес-логику, имена новых компонентов, тестов или функций.
- Агент на этапе planning предлагает `design_delta`, `file_plan` и `validation_plan`.
- Pipeline проверяет формальные контракты: допустимые корни файлов, типы артефактов, операции `create/modify/read`, validation capability, dependency boundary и traceability.
- Реализация выполняется только в пределах утвержденного `file_plan.json`.
- Существующее поведение сохраняется по умолчанию и проверяется regression validation.
- Итог выполнения читается через `scenario_result.json`, а не через набор внутренних файлов.

## Используемые инструменты

- **Python pipeline** — подготовка run-а, синхронизация kit-а, формальная проверка плана, boundary checks, UI static checks, validation, traceability, отчеты и экспорт.
- **OpenCode** — LLM code-agent для этапов `plan`, `plan-review`, `implementation`, `repair`.
- **Taskfile** — команды внутри workspace: `install`, `test`, `build`, `validate`, `frontend-behavior`.
- **React + Python/FastAPI + JSON mock storage** — текущий prototype stack.
- **Playwright** — browser/e2e validation в browser kit.

## Структура проекта

```text
prototype-dev-spike/
  architecture-profiles/
  prototype-kits/
  prototype_pipeline/
  samples/
  tools/
  runs/
  README.md
  AGENTS.md
  .gitignore
```

### `architecture-profiles/`

Архитектурные профили верхнего уровня.

```text
architecture-profiles/simple-crud-app/profile.yaml
```

Профиль описывает общий тип приложения, например simple CRUD app. Сейчас profile используется как контекст, а исполняемые правила находятся в `prototype-kits/<kit>/architecture-contract.yaml`.

### `prototype-kits/`

Kit — шаблон приложения и набор правил для конкретного технологического стека.

Текущие kit-ы:

```text
prototype-kits/react-python-json/
prototype-kits/react-python-json-browser/
```

`react-python-json` — lightweight kit без browser/e2e validation. Он использует UI static checks, backend tests, smoke/build validation.

`react-python-json-browser` — kit с включенным frontend behavior capability. Он добавляет Playwright и `task frontend-behavior`.

Типовая структура kit-а:

```text
prototype-kits/<kit>/
  kit.yaml
  generation-rules.yaml
  architecture-contract.yaml
  Taskfile.yml
  opencode.json
  AGENTS.md
  agents/
  instructions/
  prompts/
  examples/
  template/
```

Ключевые файлы:

- `kit.yaml` — метаданные kit-а и включенные capabilities.
- `generation-rules.yaml` — общие правила генерации.
- `architecture-contract.yaml` — формальный контракт для planner-а и validation: artifact types, allowed roots, validation capabilities, file policies.
- `Taskfile.yml` — команды validation/runtime внутри workspace.
- `opencode.json` — настройки OpenCode для workspace.
- `AGENTS.md` — общие инструкции агенту.
- `agents/` — инструкции для builder/reviewer/repair.
- `instructions/` — правила архитектуры, planning, validation, forbidden changes, traceability.
- `prompts/` — prompt templates для phases `plan`, `plan-review`, `implementation`, `repair`.
- `template/` — baseline workspace, из которого создается начальный прототип.

### `samples/`

`samples/` содержит входные данные для тестовых сценариев.

Текущие samples:

```text
samples/notes-app/
samples/notes-app-slice-003-confirm-delete/
samples/notes-app-slice-004-note-count/
```

`notes-app` — начальное состояние прототипа. Slice samples описывают инкрементальные изменения.

Структура slice sample:

```text
samples/notes-app-slice-004-note-count/
  run_input.json
  requirements.json
  implementation_slice.json
  scheme_model.json
  data_sources.json
  mock_plan.json
```

Назначение файлов:

- `run_input.json` — канонический вход: slice id, цель, requirements, acceptance criteria, selected existing elements, constraints.
- `implementation_slice.json` — compatibility view, материализованный из canonical input для prompt-ов.
- `requirements.json` — требования, связанные со slice.
- `scheme_model.json` — текущее принятое состояние прототипа до выполнения slice.
- `data_sources.json` — описание mock/data источников.
- `mock_plan.json` — вспомогательный план mock data для kit-а.

`run_input.json` не содержит file plan, имена будущих файлов или заранее заданные новые элементы. Это ответственность planner-а.

### `prototype/` внутри workspace

Каждый run содержит workspace. Внутри workspace есть служебная директория:

```text
runs/<run>/workspace/prototype/
  input/
  output/
```

`prototype/input/` — файлы, которые читает агент:

```text
run_input.json
implementation_slice.json
requirements.json
scheme_model.json
data_sources.json
mock_plan.json
kit.yaml
generation-rules.yaml
architecture-contract.yaml
file_plan.json
validation_plan.json
```

`file_plan.json` и `validation_plan.json` появляются после успешного `Validate plan`.

`prototype/output/` — рабочие результаты агента и pipeline:

```text
plan_proposal.json
validation_plan_proposal.json
plan_review.json
implementation_report.json
change_manifest.json
repair_report.json
changed_files.json
ui_static_check_result.json
validation_result.json
code_traceability.json
scenario_result.json
```

### `prototype_pipeline/`

Python package с orchestration-кодом pipeline.

```text
prototype_pipeline/
  cli/
  phases/
  plan_validation/
  reports/
  events.py
  paths.py
  summary.py
```

Назначение:

- `cli/run_pipeline.py` — основной pipeline CLI.
- `phases/` — небольшие wrappers для clean, sync inputs, OpenCode, reports, status.
- `plan_validation/` — формальная проверка `plan_proposal.json` и `validation_plan_proposal.json`.
- `reports/` — генерация `run_report.md` и `scenario_result.json`.
- `events.py` — event logging в `pipeline_events.jsonl`.
- `paths.py` — стандартные пути run/workspace/input/output.
- `summary.py` — сбор `run_summary.json` и расчет final status.

### `tools/`

CLI-скрипты и тонкие entrypoints к pipeline.

Основные актуальные tools:

- `prepare_run_from_scenario.py` — готовит run из `run_input.json`.
- `prepare_workspace.py` — создает workspace из kit template.
- `prepare_incremental_run.py` — создает workspace от предыдущего successful run-а.
- `run_pipeline.py` — запускает полный pipeline.
- `validate_plan.py` — запускает formal plan validation.
- `collect_changes.py` — сравнивает git diff с `file_plan.json`.
- `run_ui_static_checks.py` — проверяет `data-prototype-id` anchors.
- `run_validation.py` — запускает `task validate` внутри workspace.
- `build_code_traceability.py` — строит связь requirement → files → validation.
- `collect_agent_reports.py` — собирает agent reports из workspace.
- `export_artifact.py` — собирает `prototype_artifact.zip`.
- `export_run_bundle.py` — собирает `run_diagnostics.zip`.
- `clean_run_artifacts.py` — чистит stale outputs/logs/runtime artifacts.
- `sync_run_inputs.py` — синхронизирует kit/input artifacts в run/workspace.
- `usage_metrics.py` — собирает OpenCode usage delta.

### `runs/`

`runs/` — рабочая область запусков. Исторические runs не хранятся в исходном дереве; директория содержит только `.gitkeep` до создания новых runs. `runs/*` исключены из git через корневой `.gitignore`.

Структура run-а:

```text
runs/<run>/
  input/
  output/
  logs/
  usage/
  agent_reports/
  dist/
  workspace/
```

Назначение:

- `workspace/` — копия прототипа и kit runtime, с git baseline для diff checks.
- `input/` — canonical и materialized input текущего run-а.
- `output/` — результаты pipeline.
- `logs/` — stdout/stderr OpenCode phases и validation.
- `usage/` — OpenCode usage deltas.
- `agent_reports/` — собранные отчеты агента.
- `dist/` — `prototype_artifact.zip` и `run_diagnostics.zip`.


### `AGENTS.md`

`AGENTS.md` — краткий технический контекст для передачи другому агенту или новому чату. Он фиксирует назначение проекта, текущий стабильный pipeline, основные директории, правила доработки и команды проверки. Это не пользовательская документация и не version history; файл предназначен для быстрого ввода разработчика/агента в контекст проекта.

### `.gitignore`

Корневой `.gitignore` исключает runtime и локальные артефакты:

```text
runs/*, кроме runs/.gitkeep
prototype/input/ и prototype/output/ в корне проекта
*.zip
__pycache__/ и *.pyc
.venv/ и другие virtualenv directories
node_modules/
dist/ и build/
playwright-report/ и test-results/
.env и локальные настройки
```

В git должны попадать исходники pipeline, kit-ы, samples, README и AGENTS.md. Runtime runs, diagnostics, usage, logs и workspace outputs не коммитятся.

## Pipeline по шагам

### 1. Prepare run

**Инструмент:** наш Python-код: `tools/prepare_run_from_scenario.py`, `prepare_workspace.py` или `prepare_incremental_run.py`.

**Вход:**

```text
samples/<slice>/run_input.json
samples/<slice>/requirements.json
samples/<slice>/scheme_model.json
samples/<slice>/data_sources.json
samples/<slice>/mock_plan.json
prototype-kits/<kit>/template
или previous run workspace через --from-run
```

**Выход:**

```text
runs/<run>/workspace/
runs/<run>/input/run_input.json
runs/<run>/input/implementation_slice.json
runs/<run>/input/architecture-contract.yaml
```

Этап создает workspace, копирует kit runtime, материализует compatibility inputs, инициализирует git baseline.

### 2. Sync prompts and kit inputs

**Инструмент:** наш Python-код в `prototype_pipeline/phases/prompt_sync.py` и `tools/sync_run_inputs.py`.

**Вход:** kit metadata и prompt templates.

**Выход:** run prompt snapshots и актуальные `kit.yaml`, `generation-rules.yaml`, `architecture-contract.yaml` в run/workspace.

При `--sync-prompts` pipeline копирует prompt templates из kit-а в run, если эти prompt-файлы не являются внешними override-файлами.

### 3. OpenCode plan

**Инструмент:** OpenCode.

**Вход:** `prototype/input/run_input.json`, `scheme_model.json`, `requirements.json`, `architecture-contract.yaml`, kit rules и текущий код workspace.

**Выход:**

```text
prototype/output/plan_proposal.json
prototype/output/validation_plan_proposal.json
```

Planner определяет `design_delta`, существующие и новые элементы, решения preserve/reuse/modify, draft file plan и validation checks.

### 4. Validate plan

**Инструмент:** наш Python-код: `tools/validate_plan.py` и `prototype_pipeline/plan_validation/`.

**Вход:**

```text
plan_proposal.json
validation_plan_proposal.json
architecture-contract.yaml
scheme_model.json
run_input.json
```

**Выход:**

```text
runs/<run>/input/file_plan.json
runs/<run>/input/validation_plan.json
runs/<run>/output/plan_validation_result.json
```

Этап проверяет схему плана, допустимые operations, artifact types, allowed roots, validation capabilities, dependency/file boundary. После успешной проверки утвержденные `file_plan.json` и `validation_plan.json` коммитятся в git baseline workspace.

### 5. OpenCode plan-review

**Инструмент:** OpenCode.

**Вход:** plan proposals, run inputs, architecture contract.

**Выход:**

```text
prototype/output/plan_review.json
```

Review проверяет архитектурную безопасность плана: не происходит ли repurpose существующего поведения, не расширен ли scope, достаточно ли validation coverage, не нарушены ли contract rules.

### 6. OpenCode implementation

**Инструмент:** OpenCode.

**Вход:** утвержденные `file_plan.json`, `validation_plan.json`, run inputs и код workspace.

**Выход:** измененные файлы прототипа и отчеты:

```text
prototype/output/implementation_report.json
prototype/output/change_manifest.json
```

Implementation может создавать/изменять только файлы, разрешенные в `file_plan.json`.

### 7. Collect changes / boundary

**Инструмент:** наш Python-код: `tools/collect_changes.py`.

**Вход:** git diff workspace и `runs/<run>/input/file_plan.json`.

**Выход:**

```text
runs/<run>/output/changed_files.json
runs/<run>/output/workspace.diff
```

Этап классифицирует created/modified/deleted files, проверяет unexpected files, read-only violations, missing required changes и runtime/non-semantic artifacts.

### 8. UI static checks

**Инструмент:** наш Python-код: `tools/run_ui_static_checks.py`.

**Вход:** `file_plan.json`, `validation_plan.json`, scheme elements и измененные frontend files.

**Выход:**

```text
runs/<run>/output/ui_static_check_result.json
```

Этап проверяет `data-prototype-id` anchors для screen/widget/action элементов, связанных с измененными frontend artifacts. Это не browser-тест и не OpenCode phase; это формальная проверка связки scheme → UI anchors.

### 9. Validation

**Инструмент:** наш Python-код: `tools/run_validation.py`, который запускает `task validate` внутри workspace. Сами проверки выполняются инструментами kit-а: pytest, Vite/build, Playwright и shell commands из `Taskfile.yml`.

**Вход:** workspace, `Taskfile.yml`, `validation_plan.json` и фактически сгенерированный код.

**Выход:**

```text
runs/<run>/output/validation_result.json
runs/<run>/logs/validation.stdout.log
runs/<run>/logs/validation.stderr.log
```

В browser kit `task validate` включает:

```text
install
smoke
backend tests / pytest
frontend build
frontend-behavior / Playwright
```

`run_validation.py` фиксирует status, exit code, duration, stdout/stderr logs. Если Playwright не может стартовать из-за системных зависимостей, результат классифицируется как `environment_failed` с диагностикой environment issue.

### 10. Repair

**Инструмент:** OpenCode, запускается только при `--allow-repair` и только если есть failure, который можно исправлять кодом.

**Вход:** validation/boundary/ui_static results, file plan, текущие изменения workspace.

**Выход:**

```text
prototype/output/repair_report.json
```

После repair pipeline повторяет boundary, UI static и validation checks.

### 11. Traceability

**Инструмент:** наш Python-код: `tools/build_code_traceability.py`.

**Вход:** `file_plan.json`, `validation_plan.json`, `changed_files.json`, `validation_result.json`, `ui_static_check_result.json`, `run_input.json`.

**Выход:**

```text
runs/<run>/output/code_traceability.json
```

Этап строит связь requirements с измененными файлами и validation checks. Primary requirements должны получить статус `implemented_and_validated`. Preserved behavior, проверенное regression checks, получает `validated_unchanged`.

### 12. Reports and export

**Инструмент:** наш Python-код: `prototype_pipeline/summary.py`, `prototype_pipeline/reports/*`, `tools/export_artifact.py`, `tools/export_run_bundle.py`.

**Выход:**

```text
runs/<run>/output/run_summary.json
runs/<run>/output/scenario_result.json
runs/<run>/output/run_report.md
runs/<run>/dist/prototype_artifact.zip
runs/<run>/dist/run_diagnostics.zip
```

`run_summary.json` рассчитывает final status. `scenario_result.json` является главным отчетным контрактом для UI.

## Запуск

### Browser/e2e run

```bash
cd ~/opencode/prototype-dev-spike

python3 tools/prepare_run_from_scenario.py \
  --from-run runs/run-003-confirm-delete-browser \
  --scenario samples/notes-app-slice-004-note-count/run_input.json \
  --run runs/run-004-note-count-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-004-note-count-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-004-note-count-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-004-note-count-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-004-note-count-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --repair-prompt-file runs/run-004-note-count-browser/opencode_repair_prompt.txt
```

### Lightweight run

```bash
cd ~/opencode/prototype-dev-spike

python3 tools/prepare_run_from_scenario.py \
  --scenario samples/notes-app-slice-003-confirm-delete/run_input.json \
  --run runs/run-003-confirm-delete \
  --kit prototype-kits/react-python-json

python3 tools/run_pipeline.py \
  --run runs/run-003-confirm-delete \
  --kit prototype-kits/react-python-json \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-003-confirm-delete/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-003-confirm-delete/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-003-confirm-delete/opencode_implementation_prompt.txt \
  --allow-repair \
  --repair-prompt-file runs/run-003-confirm-delete/opencode_repair_prompt.txt
```

### Основные параметры `run_pipeline.py`

- `--run` — директория run-а.
- `--kit` — kit для sync metadata и prompts.
- `--sync-prompts` — синхронизировать prompt snapshots из kit-а.
- `--clean` — очистить output/logs/usage/agent_reports/dist и откатить workspace к baseline.
- `--clean-root-prototype-output` — очистить stale `prototype/output` в workspace.
- `--strict-ui-checks` — считать UI static blockers причиной failure.
- `--model` — модель OpenCode.
- `--plan-prompt-file` — prompt для planning phase.
- `--review-prompt-file` — prompt для plan-review phase.
- `--implementation-prompt-file` — prompt для implementation phase.
- `--allow-repair` — разрешить repair phase.
- `--repair-prompt-file` — prompt для repair phase.

## Browser/e2e setup

Для `react-python-json-browser` нужны browser dependencies Playwright.

```bash
cd runs/<run>/workspace

task frontend-behavior-setup
```

Или напрямую:

```bash
cd runs/<run>/workspace/frontend
npx playwright install --with-deps chromium
```

## Итоговый отчет `scenario_result.json`

Главный результат run-а:

```text
runs/<run>/output/scenario_result.json
```

Верхний уровень:

```json
{
  "scenario_result_version": 1,
  "run": "runs/run-004-note-count-browser",
  "slice": {
    "slice_id": "SLICE-004",
    "title": "Show visible and total note count",
    "requirement_ids": ["REQ-007"]
  },
  "final_status": "passed",
  "stage_status": {
    "plan": "passed",
    "plan_review": "passed",
    "implementation": "passed",
    "repair": "not_run",
    "plan_validation": "passed",
    "boundary": "passed",
    "ui_static": "passed",
    "validation": "passed",
    "traceability": "passed",
    "final": "passed"
  }
}
```

Основные поля для UI/отчета:

```text
final_status
slice
stage_status
changed_files.created_files
changed_files.modified_files
changed_files.read_only_unchanged_files
validation.status
validation.ui_static.status
validation.checks
traceability.status
traceability.primary_requirements
traceability.supporting_regressions
traceability.gaps
repair.used
artifacts.prototype_artifact
artifacts.diagnostics_archive
usage.totals
```

## Критерии успешного run-а

Run успешен, если:

- `plan` завершился успешно;
- formal plan validation создал допустимые `file_plan.json` и `validation_plan.json`;
- `plan-review` не нашел blockers;
- `implementation` завершился успешно;
- фактические изменения соответствуют `file_plan.json`;
- `ui_static` не содержит blockers;
- `task validate` прошел;
- traceability для primary requirements не содержит gaps;
- artifact и diagnostics экспортированы.

Успешные тесты сами по себе не гарантируют успешный run. Final status также учитывает boundary, UI static и traceability.
