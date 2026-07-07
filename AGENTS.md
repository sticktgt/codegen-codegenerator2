# AGENTS.md

Этот файл — краткий технический контекст для агента или другого чата, который будет дорабатывать проект `prototype-dev-spike`.

## Назначение проекта

`prototype-dev-spike` — стенд для управляемой генерации прототипов приложений с помощью OpenCode/LLM-агентов. Проект проверяет workflow, в котором агент не работает свободно со всем репозиторием, а проходит через контролируемый pipeline:

```text
run_input.json
→ OpenCode planning
→ formal plan validation
→ OpenCode implementation
→ boundary / UI static / validation / traceability
→ scenario_result.json
```

Главный контракт текущего решения:

```text
samples/<slice>/run_input.json → runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход от requirements stage. `scenario_result.json` — основной отчетный контракт для будущего UI/отчета.

## Текущее стабильное состояние

Проверенный путь:

- `SLICE-003` — confirm-delete UI flow.
- `SLICE-004` — новый widget `NoteCountSummary`, screen wiring, browser/e2e validation.
- Browser kit: `prototype-kits/react-python-json-browser`.
- Последний успешный сценарий: `samples/notes-app-slice-004-note-count/run_input.json` от baseline `runs/run-003-confirm-delete-browser`.

Ожидаемый successful run создает/изменяет:

```text
created:
  frontend/src/widgets/NoteCountSummary.jsx
  frontend/e2e/note-count-summary.spec.js
modified:
  frontend/src/screens/NoteListScreen.jsx
```

и заканчивается:

```text
Pipeline final status: passed
```

## Основные директории

```text
architecture-profiles/       Общие архитектурные профили.
prototype-kits/              Исполняемые kit-ы, templates, prompts, validation contracts.
prototype_pipeline/          Python package основного pipeline.
tools/                       CLI entrypoints и вспомогательные tools.
samples/                     Входные сценарии и примеры slice.
runs/                        Runtime-директории запусков; в git хранится только .gitkeep.
```

## Активные kit-ы

```text
prototype-kits/react-python-json/
prototype-kits/react-python-json-browser/
```

`react-python-json` — lightweight kit без browser/e2e validation.

`react-python-json-browser` — kit с Playwright/browser behavior validation. Для него может потребоваться одноразовая установка browser dependencies:

```bash
cd runs/<run>/workspace
task frontend-behavior-setup
```

## Активный pipeline

Основной CLI:

```bash
python3 tools/prepare_run_from_scenario.py ...
python3 tools/run_pipeline.py ...
```

Основные этапы:

1. Prepare run — Python code создает workspace из kit template или previous run.
2. Sync inputs/prompts — Python code синхронизирует kit metadata и prompt snapshots.
3. OpenCode plan — агент пишет `plan_proposal.json` и `validation_plan_proposal.json`.
4. Validate plan — Python code проверяет formal contract и пишет `file_plan.json`, `validation_plan.json`.
5. OpenCode plan-review — агент проверяет архитектурную безопасность плана.
6. OpenCode implementation — агент меняет только файлы, разрешенные `file_plan.json`.
7. Collect changes — Python code проверяет git diff против file plan.
8. UI static checks — Python code проверяет `data-prototype-id` anchors.
9. Validation — Python code запускает `task validate`; kit выполняет smoke/pytest/build/Playwright.
10. Repair — OpenCode, только при repairable failure и `--allow-repair`.
11. Traceability — Python code строит связь requirements → files → checks.
12. Reports/export — Python code пишет `scenario_result.json`, `run_report.md`, архивы.

## Важные правила доработки

- Не возвращать старый путь `expected_files.json` / `traceability_plan.json`.
- Не добавлять business logic, имена файлов, имена тестов или правила предметной области в Python pipeline.
- Python pipeline должен проверять контракты и границы, а не генерировать функциональное решение.
- Обычные implementation/repair slice не должны менять зависимости. Новые зависимости должны появляться только через отдельный kit/dependency flow.
- `runs/` — runtime output. Не коммитить run-директории, логи, usage, dist, workspace.
- `samples/` — коммитить только компактные входные сценарии, которые нужны как тестовые cases.
- `prototype-kits/*/template/` — baseline runtime; не коммитить `node_modules`, build outputs, Playwright reports.
- Документация проекта ведется на русском языке.
- После патчей указывать измененные файлы, новые файлы, удаленные файлы и команды проверки.

## Проверка после изменений

Быстрая проверка синтаксиса:

```bash
python3 -m py_compile \
  tools/*.py \
  prototype_pipeline/*.py \
  prototype_pipeline/cli/*.py \
  prototype_pipeline/phases/*.py \
  prototype_pipeline/reports/*.py \
  prototype_pipeline/plan_validation/*.py
```

Проверка CLI:

```bash
python3 tools/run_pipeline.py --help
python3 tools/validate_plan.py --help
```

Проверочный browser run:

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

## Следующий логичный функциональный шаг

После фиксации текущего проекта в git следующий крупный шаг — accepted baseline / promotion flow:

```text
successful run → accepted current prototype state → next slice uses it automatically
```

LangGraph/LangChain не нужен как замена текущего deterministic pipeline. Его можно рассматривать позже как верхнеуровневый workflow над уже стабильным pipeline.
