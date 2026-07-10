# codegenerator2

`codegenerator2` — экспериментальный стенд для управляемой генерации прототипов приложений с помощью OpenCode/LLM-агентов.

Проект проверяет не свободную работу агента со всем репозиторием, а воспроизводимый pipeline: requirements-сценарий превращается в план изменений, план формально проверяется, агент реализует только разрешенные файлы, после чего наш Python-код проверяет границы, UI anchors, validation, traceability и формирует итоговый отчет.

Основной контракт текущего workflow:

```text
samples/<scenario>/run_input.json
→ runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход от requirements stage. `scenario_result.json` — основной машинно-читаемый итог для будущего UI/отчета.

## Основные принципы

- Pipeline-код не придумывает бизнес-логику, имена новых компонентов, тестов или функций.
- Агент на этапе planning предлагает `design_delta`, `file_plan` и `validation_plan`.
- Pipeline проверяет machine-readable safety boundary: обязательные JSON outputs, безопасные пути, forbidden paths, allowed roots, dependency boundary, git diff boundaries, static UI anchors, validation и traceability. Архитектурный смысл плана должна сформировать и самопроверить модель по правилам kit-а.
- Реализация выполняется только в пределах утвержденного `file_plan.json`; Python не исправляет содержательный смысл плана, чтобы сделать его удобнее для реализации.
- Существующее поведение сохраняется по умолчанию и проверяется regression validation.
- Dependency/package changes не запрещены как класс, но должны быть явно предложены планом, разрешены контрактом, включены в `file_plan.json` и иметь краткое обоснование. Обычные slice должны по возможности использовать зависимости kit-а.
- Итог выполнения читается через `scenario_result.json`, а не через набор внутренних файлов.

## Архитектурная идея

Задача проекта — генерировать код в рамках заранее описанного архитектурного шаблона, а не свободно редактировать репозиторий. Шаблон задает уровни приложения и правила для каждого уровня:

- UI screens;
- UI widgets;
- frontend actions;
- backend API modules;
- backend services/components;
- backend data models;
- backend storage/mock data;
- validation tests;
- existing skeleton/integration files.

Для каждого уровня kit описывает место в проекте, допустимые операции, naming convention и validation capabilities. Требования описывают, что нужно реализовать; architecture kit описывает, где и как это должно быть реализовано.

Планирование должно происходить на стороне модели:

```text
requirements + scheme context + architecture rules
→ model-generated design_delta / file_plan_draft / validation_plan_proposal
→ model self-check against architecture rules
→ final plan JSON
```

Python не должен подменять этот процесс и становиться скрытым planner-ом. Если модель выбрала неверный слой, неверный `artifact_type` или неверную операцию `create/modify`, это ошибка плана, которую надо исправлять правилами/prompt-ами или будущим replan-механизмом, а не содержательной нормализацией в Python.

## Где живут правила

Правила активного архитектурного шаблона находятся в kit-е:

```text
prototype-kits/react-python-json-browser/
  architecture-contract.yaml      machine-readable contract: artifact types, roots, operations, validation capabilities
  generation-rules.yaml           naming and scheme-to-file mapping
  instructions/architecture.md    human-readable layer rules and skeleton/integration rules
  instructions/planning-rules.md  planner checklist and output rules
  instructions/coding-rules.md    implementation coding rules
  instructions/validation-rules.md validation and UI anchor rules
  prompts/                        phase prompts that reference these rules
  examples/                       examples, not ready-made implementation
  template/                       minimal skeleton workspace
```

Python-код может читать machine-readable части этих правил для safety checks, но правила разработки должны оставаться в kit-е. Не переносить предметную архитектурную логику в `prototype_pipeline/` и `tools/`.

## Роль Python-кода

Python pipeline отвечает за порядок действий и контроль исполнения:

- подготовка workspace;
- sync kit context;
- запуск OpenCode phases;
- проверка наличия и формата обязательных JSON outputs;
- минимальные safety checks по путям и forbidden files;
- сбор git diff и boundary check против утвержденного `file_plan.json`;
- статические проверки результата кода, например `data-prototype-id`;
- запуск `task validate`;
- traceability, reports, diagnostics, usage logs.

Python pipeline не должен:

- придумывать имена feature-файлов, тестов или scheme elements;
- исправлять `artifact_type`, выбранный моделью;
- превращать `create` в `modify` по смыслу плана;
- добавлять частные исключения под конкретный LLM output;
- дублировать architecture kit в Python-условиях.

Допустимая нормализация — техническая: canonical path separators, default для необязательных полей, совместимость старого/нового имени поля, сортировка/запись JSON. Содержательные решения остаются в модели и architecture rules.

## Используемые инструменты

- **Python pipeline** — подготовка run-а, синхронизация kit-а, формальная проверка плана, boundary checks, UI static checks, запуск validation, traceability, отчеты и экспорт.
- **OpenCode** — LLM code-agent для этапов `plan`, `plan-review`, `implementation`, `repair`.
- **Taskfile** — команды validation/runtime внутри workspace: `install`, `smoke`, `test`, `build`, `frontend-behavior`, `validate`.
- **React + Python/FastAPI + JSON mock storage** — текущий prototype stack.
- **Pytest** — backend/API/service validation.
- **Vite build** — frontend build validation.
- **Playwright** — browser/e2e validation.

OpenCode может во время implementation/repair читать файлы и запускать отдельные диагностические команды, если это нужно для работы агента. Эти действия не являются официальным validation stage и должны быть неинтерактивными: без Playwright `--debug`, `--ui`, `codegen`, `show-trace` и headed mode. Официальный результат validation определяется только pipeline-этапом `Run validation`, который запускает `tools/run_validation.py`. Для `validate` скрипт выполняет стадии validation последовательно (`install`, `smoke`, `test`, `build`, `frontend-behavior`) и собирает их в один `validation_result.json`, не останавливаясь на первом backend failure. При этом downstream failures помечаются зависимостями: если backend smoke/pytest или frontend build уже упали, browser/e2e failures являются диагностическим контекстом, а не обязательной первичной причиной repair.

Если после implementation уже упали file boundary или UI static checks, pipeline всё равно сначала запускает staged validation как диагностику перед repair. Это нужно, чтобы repair видел полный набор наблюдаемых проблем: boundary, ui_static, backend pytest, build и browser/e2e. Post-repair validation остаётся источником истины.

По умолчанию при `--allow-repair` pipeline допускает до двух repair-попыток (`--max-repair-attempts`, default `2`). Это нужно для случаев, где первый repair устраняет root failure backend/smoke/test, а после повторной validation остаётся уже независимая frontend/e2e ошибка. Такой цикл не заменяет validation: после каждой repair-попытки заново выполняются collect changes, UI static checks и staged validation.

Перед каждой repair-попыткой pipeline пишет компактный `prototype/output/repair_context.json`. Это не новый валидатор, а диагностический handoff для агента: текущие boundary/ui_static/validation failures, root/downstream stages, хвосты validation logs, relevant workspace paths и краткая история предыдущих repair. Цель файла — помочь repair сделать рабочую точечную правку и вернуть управление pipeline, а не просто лучше объяснить failure.

Для защиты от случайных интерактивных Playwright diagnostics pipeline дополнительно запускает OpenCode phases с `CI=1`, `PWDEBUG=0`, `PLAYWRIGHT_HEADLESS=1` и временным workspace-local shim для `npm`/`npx`/`playwright`, который блокирует `--debug`, `--ui`, `--headed`, `codegen` и `show-trace`. Это инфраструктурная защита, а не часть generated prototype.

## Отчётные артефакты фаз

Контрактными результатами фаз являются JSON-файлы, которые явно требуются prompt-ами: `plan_proposal.json`, `validation_plan_proposal.json`, `plan_review.json`, `implementation_report.json`, `change_manifest.json`, `repair_report.json`. Stdout-сводки и вспомогательные действия агента не заменяют эти файлы.

## Repair как safety net

Repair — нормальная страховочная фаза, но частые однотипные repair-срабатывания нужно переводить в kit-level инструкции и reference examples. Сейчас типовые причины repair: согласование API route/prefix с тестами, изоляция JSON mock storage в pytest, Playwright selectors, стабильность e2e test data и соответствие тестовых ожиданий фактической семантике требования.

Если repair внёс изменения, но агент не успел записать `repair_report.json`, pipeline может создать fallback-отчёт и продолжить post-repair проверки. Failed diagnostic tool calls во время repair также могут быть оставлены как warnings, если workspace изменился и OpenCode завершился успешно. Такой отчёт не заменяет содержательную диагностику агента; итоговым источником истины остаются `changed_files.json`, `validation_result.json` и post-repair validation.

Внутри repair действует бюджет на дорогие диагностические команды: повторные `npm run test:e2e` / `playwright test` и широкие `pytest`-циклы могут быть остановлены runner-ом. Если repair уже изменил workspace, это трактуется как controlled handoff, а не как окончательная неудача: phase завершается с `completion_mode: guarded_handoff`, pipeline собирает изменения и запускает официальные post-repair checks. Если они всё ещё падают и попытки остались, следующая repair-попытка получит обновленный `repair_context.json`.

Не надо закрывать эти случаи растущим набором Python-запретов. Python-checker должен оставаться на уровне контрактных инвариантов: границы файлов, forbidden paths, dependency boundary, обязательные отчёты, грубые UI anchor инварианты.

## Структура проекта

```text
codegenerator2/
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

Профиль описывает общий тип приложения, например simple CRUD app. Исполняемые правила текущего pipeline находятся в kit-е, прежде всего в `prototype-kits/react-python-json-browser/architecture-contract.yaml`.

### `prototype-kits/`

Kit — шаблон приложения и набор правил для конкретного технологического стека.

Текущий активный kit один:

```text
prototype-kits/react-python-json-browser/
```

Это React + Python + JSON kit с включенным browser/e2e validation через Playwright. Отдельный lightweight kit без browser/e2e validation сейчас не поддерживается, чтобы не держать две почти одинаковые версии правил и prompt-ов. Если позже понадобится режим без browser/e2e, его лучше добавлять как явный capability/profile внутри текущего подхода, а не копировать весь kit без необходимости.

Типовая структура kit-а:

```text
prototype-kits/react-python-json-browser/
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
- `AGENTS.md` — общие инструкции агенту внутри workspace.
- `agents/` — инструкции для builder/reviewer/repair.
- `instructions/` — правила architecture, planning, validation, forbidden changes, traceability.
- `prompts/` — prompt templates для phases `plan`, `plan-review`, `implementation`, `repair`.
- `template/` — baseline workspace, из которого создается начальный прототип.

В созданном workspace канонический prompt-facing путь для markdown-инструкций — `instructions/...`. Pipeline также может держать read-only compatibility mirror под `prototype/input/instructions/...`; это нужно только чтобы избежать шумных failed reads от агента и не является отдельным источником правил.

### `samples/`

`samples/` содержит входные данные для тестовых сценариев.

Текущие samples:

```text
samples/notes-app/
samples/notes-app-slice-003-confirm-delete/
samples/notes-app-slice-004-note-count/
```

`notes-app` — greenfield baseline, с него начинается запуск после clone. Slice samples описывают инкрементальные изменения поверх successful baseline.

Структура sample:

```text
samples/<sample>/
  run_input.json
  requirements.json
  implementation_slice.json
  scheme_model.json
  data_sources.json
  mock_plan.json
```

Назначение файлов:

- `run_input.json` — канонический вход: slice id, цель, requirements, acceptance criteria, selected existing elements, constraints.
- `implementation_slice.json` — compatibility view для prompt-ов.
- `requirements.json` — требования, связанные со slice.
- `scheme_model.json` — модель элементов прототипа до выполнения slice. Для greenfield baseline это целевая модель начального приложения.
- `data_sources.json` — описание mock/data источников.
- `mock_plan.json` — вспомогательный план mock data для kit-а.

`run_input.json` не содержит file plan, имена будущих файлов или заранее заданные новые элементы для инкрементальных slice. Это ответственность planner-а.

### `runs/`

`runs/` — runtime-директория запусков. В git хранится только `runs/.gitkeep`; сами `runs/run-*` не коммитятся.

Структура run-а:

```text
runs/<run>/
  input/
  workspace/
  output/
  logs/
  usage/
  agent_reports/
  dist/
```

Главные файлы результата:

```text
runs/<run>/output/scenario_result.json
runs/<run>/output/run_report.md
runs/<run>/output/run_summary.json
runs/<run>/dist/prototype_artifact.zip
runs/<run>/dist/run_diagnostics.zip
```

### `prototype/` внутри workspace

Каждый run содержит workspace. Внутри workspace есть служебная директория:

```text
runs/<run>/workspace/prototype/
  input/
  output/
```

`prototype/input/` — файлы, которые читает агент и pipeline:

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
instructions/          optional read-only compatibility mirror of kit markdown instructions
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

Python package основного pipeline.

```text
prototype_pipeline/
  cli/run_pipeline.py
  phases/
  plan_validation/
  reports/
  events.py
  paths.py
  summary.py
```

Назначение:

- `cli/run_pipeline.py` — основной pipeline CLI.
- `phases/` — wrappers для clean, sync inputs, OpenCode, reports, status.
- `plan_validation/` — проверка формата и machine-readable safety boundary для `plan_proposal.json` и `validation_plan_proposal.json`; не исправляет архитектурный смысл плана.
- `reports/` — генерация `run_report.md` и `scenario_result.json`.
- `events.py` — event logging в `pipeline_events.jsonl`.
- `paths.py` — стандартные пути run/workspace/input/output.
- `summary.py` — сбор `run_summary.json` и расчет final status.

### `tools/`

CLI-скрипты и entrypoints к pipeline.

Основные актуальные tools:

- `prepare_run_from_scenario.py` — основной способ подготовки run-а из `run_input.json`.
- `prepare_workspace.py` — низкоуровневое создание workspace из kit template; для обычного запуска использовать `prepare_run_from_scenario.py`.
- `prepare_incremental_run.py` — низкоуровневая подготовка workspace от предыдущего run-а; вызывается через `prepare_run_from_scenario.py --from-run ...`.
- `run_pipeline.py` — полный pipeline.
- `validate_plan.py` — formal plan validation.
- `collect_changes.py` — сравнение git diff с `file_plan.json`.
- `run_ui_static_checks.py` — проверка `data-prototype-id` anchors.
- `run_validation.py` — thin CLI wrapper for staged validation. The implementation is split into `tools/validation_runner/` modules for stage execution, reporting, and workspace restore.
- `build_code_traceability.py` — traceability requirements → files → checks.
- `export_artifact.py` / `export_run_diagnostics.py` — архивы результата.

## Pipeline: этапы, входы, выходы и исполнитель

| Этап | Исполнитель | Основные входы | Основные выходы |
|---|---|---|---|
| Prepare run | Python | `samples/<sample>/run_input.json`, kit template, optional `--from-run` | `runs/<run>/workspace`, `runs/<run>/input` |
| Clean/sync | Python | kit metadata, prompt templates | synced `prototype/input/*`, prompt snapshots |
| Plan | OpenCode | `prototype/input/run_input.json`, `requirements.json`, `scheme_model.json`, kit contract | `plan_proposal.json`, `validation_plan_proposal.json` |
| Validate plan | Python | plan proposal, validation proposal, `architecture-contract.yaml` | format/safety result, `file_plan.json`, `validation_plan.json`, `plan_validation_result.json` |
| Plan review | OpenCode | proposals, approved input context, kit contract | `plan_review.json` |
| Implementation | OpenCode | `file_plan.json`, `validation_plan.json`, requirements/context | implementation files, tests, `implementation_report.json`, `change_manifest.json` |
| Collect changes | Python | git diff, `file_plan.json` | `changed_files.json` |
| UI static checks | Python | `changed_files.json`, `file_plan.json`, frontend files | `ui_static_check_result.json` |
| Validation | Python + Taskfile + pytest/npm/Playwright | workspace, `Taskfile.yml`, generated tests | `validation_result.json`, validation logs |
| Repair | OpenCode | validation/boundary/UI static failures, file plan | repaired files, `repair_report.json` |
| Traceability | Python | requirements, changed files, validation result | `code_traceability.json` |
| Reports/export | Python | all outputs | `scenario_result.json`, `run_report.md`, archives |

## Validation stage подробнее

Validation stage не выполняется OpenCode. Он реализован в нашем Python-коде:

```text
tools/run_validation.py
→ cd runs/<run>/workspace
→ task validate
```

В текущем kit-е `task validate` выполняет:

```text
task install
→ task smoke
→ task test
→ task build
→ task frontend-behavior
```

Состав проверок:

- `task install` — создает `.venv`, ставит backend requirements, выполняет `npm install`, ставит Playwright browser.
- `task smoke` — запускает backend smoke check.
- `task test` — запускает backend pytest.
- `task build` — запускает frontend build.
- `task frontend-behavior` — запускает Playwright browser/e2e tests.

Pipeline дополнительно выполняет `ui_static` до `task validate`. `ui_static` — это не e2e-тест, а статическая проверка, что созданные/измененные UI-файлы содержат нужные `data-prototype-id` anchors для scheme elements, напрямую назначенных этому файлу в `file_plan.json`. Screen-файл должен нести свой `screen.*` anchor и anchors для action-контролов, которые он реально рендерит; widget-файл не обязан нести чужие action anchors, если его file-plan item содержит только `widget.*`. Checker собирает все найденные blockers по файлу за один проход; для action anchors он учитывает как прямые literal attributes, так и простые JSX literal alternatives вроде `data-prototype-id={editing ? 'action.edit-note' : 'action.create-note'}`. Переменные вида `data-prototype-id={someVariable}` не засчитываются как стабильные anchors.

## Запуск с нуля после clone/переноса проекта

Нормальный запуск начинается с greenfield baseline `SLICE-001`, затем выполняются инкрементальные slice.

### 1. Baseline: SLICE-001 basic notes app

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-001-notes-app-browser

python3 tools/prepare_run_from_scenario.py \
  --scenario samples/notes-app/run_input.json \
  --run runs/run-001-notes-app-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-001-notes-app-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-001-notes-app-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-001-notes-app-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-001-notes-app-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --repair-prompt-file runs/run-001-notes-app-browser/opencode_repair_prompt.txt
```

Successful baseline должен закончиться:

```text
Pipeline final status: passed
```

### 2. Incremental: SLICE-003 confirm delete

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-003-confirm-delete-browser

python3 tools/prepare_run_from_scenario.py \
  --from-run runs/run-001-notes-app-browser \
  --scenario samples/notes-app-slice-003-confirm-delete/run_input.json \
  --run runs/run-003-confirm-delete-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-003-confirm-delete-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-003-confirm-delete-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-003-confirm-delete-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-003-confirm-delete-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --repair-prompt-file runs/run-003-confirm-delete-browser/opencode_repair_prompt.txt
```

### 3. Incremental: SLICE-004 note count summary

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-004-note-count-browser

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

## Параметры `run_pipeline.py`

Основные параметры:

- `--run` — директория run-а.
- `--kit` — kit, который используется для sync и validation context.
- `--sync-prompts` — обновить prompt snapshots из kit-а перед запуском.
- `--clean` — очистить run outputs/logs/usage/dist перед запуском.
- `--clean-root-prototype-output` — очистить случайный root `prototype/output` вне workspace.
- `--strict-ui-checks` — считать UI static blockers причиной repair/failure.
- `--model` — модель OpenCode.
- `--plan-prompt-file`, `--review-prompt-file`, `--implementation-prompt-file`, `--repair-prompt-file` — snapshots prompt-ов в run-директории.
- `--allow-repair` — разрешить repair phase при repairable failure.
- `--max-repair-attempts` — максимальное число repair-попыток при `--allow-repair`; по умолчанию `2`, чтобы второй repair мог устранить ошибки, проявившиеся после исправления root failure.

## Browser/e2e setup

Для Playwright иногда нужны системные зависимости. Если validation падает из-за отсутствующих browser dependencies, выполнить:

```bash
cd runs/<run>/workspace
task frontend-behavior-setup
```

Команда может потребовать системные пакеты/`sudo`, потому она не выполняется автоматически как отдельный preflight. Обычный `task validate` устанавливает Python/npm/Playwright browser dependencies в пределах workspace.

## Итоговый отчет `scenario_result.json`

Главный отчетный файл:

```text
runs/<run>/output/scenario_result.json
```

Он содержит:

- `slice` — id, title, goal, requirements, acceptance criteria.
- `final_status` — итог `passed/failed`.
- `stage_status` — статусы этапов pipeline.
- `changed_files` — созданные, измененные, unexpected, policy violations, runtime artifacts.
- `validation` — статус `task validate`, UI static result, список checks.
- `traceability` — связь requirements → files → validation checks.
- `repair` — был ли repair и какие repair phases выполнялись.
- `artifacts` — ссылки на artifact zip, diagnostics zip, report, summary.
- `usage` — LLM/tool usage по фазам.
- `inputs` — какие input-файлы использовались.

## Что коммитить в git

Коммитить:

```text
README.md
AGENTS.md
.gitignore
architecture-profiles/
prototype-kits/
prototype_pipeline/
samples/
tools/
runs/.gitkeep
```

Не коммитить:

```text
runs/run-*/
prototype/input/
prototype/output/
*.zip
__pycache__/
*.pyc
.venv/
node_modules/
dist/
build/
playwright-report/
test-results/
.env
```

## Проверка после изменений проекта

```bash
python3 -m py_compile \
  tools/*.py \
  prototype_pipeline/*.py \
  prototype_pipeline/cli/*.py \
  prototype_pipeline/phases/*.py \
  prototype_pipeline/reports/*.py \
  prototype_pipeline/plan_validation/*.py

python3 tools/run_pipeline.py --help
python3 tools/validate_plan.py --help
```

## Текущий следующий шаг

После успешного ручного sequence `SLICE-001 → SLICE-003 → SLICE-004` следующий функциональный шаг — accepted baseline / promotion flow:

```text
successful run → accepted current prototype state → next slice uses it automatically
```

Это позволит не передавать каждый раз `--from-run` вручную и приблизит workflow к будущему requirements/UI layer.

### Agent self-checks

OpenCode may run small diagnostic commands while implementing or repairing a slice, but those commands are not the canonical validation contract. The canonical checks are the pipeline phases: file boundary, UI static checks, and `tools/run_validation.py` after implementation/repair. Frontend diagnostics should use the kit runner (`npm run build`, `npm run test:e2e`) rather than raw `node --check` on JSX or Playwright ESM files. Browser/e2e tests should verify behavior through the UI or public API, not by reading private backend storage files.


### OpenCode self-check limits

Full validation is owned by the pipeline. `tools/run_validation.py` records per-stage results for install, smoke, backend pytest, frontend build, and browser/e2e, and restores semantic workspace files between stages so tests do not leak JSON mock-storage mutations or accidentally created semantic files into later checks. OpenCode phases may use focused non-interactive diagnostics, but they should not call `tools/run_validation.py`, run broad install/build/e2e loops from inside implementation or repair, or use Playwright `--debug` / UI / headed modes. This keeps repair shorter and prevents duplicate validation from being interpreted as a separate source of truth.

Backend tests for JSON-backed prototypes should isolate storage via injection, route-module dependency replacement, dependency overrides, or small app/service factories. They should not rewrite implementation source files from pytest fixtures.

## Kit implementation patterns

For recurring implementation shapes, prefer kit-level patterns over adding more prompt rules. The react-python-json-browser kit provides `instructions/implementation-patterns.md` as an index from artifact types to focused patterns, for example FastAPI JSON CRUD and React browser CRUD/list/search flows. Patterns are guidance only: they do not override `file_plan.json` and do not grant permission to create extra files.



## Контроль покрытия требований

Валидация плана проверяет покрытие первичных требований. Каждый id из `implementation_slice.requirements` должен быть связан хотя бы с одним planned implementation file и хотя бы с одной validation check. Это не даёт получить зелёный запуск, в котором одно из требований молча исчезло из traceability. При этом coverage может выводиться не только из прямого `requirement_id` в file plan, но и из `scheme_model`: если файл реализует scheme element или владеет `screen_internal` action через `design_delta.owning_artifact`, связанные requirement ids учитываются как покрытые этим файлом.

### Browser/e2e validation scope

Для browser-enabled kit e2e-проверки нужны, но они должны оставаться компактными. Для одного связного CRUD/list/search экрана предпочтителен один небольшой Playwright spec, который покрывает основной пользовательский путь и может быть связан с несколькими requirements через validation plan. Backend pytest должен покрывать API edge cases и большинство негативных сценариев. Это снижает количество repair-циклов и flaky-поведение из-за общего JSON-backed состояния между browser-тестами.

Для create/edit экранов важно различать кнопку, которая открывает форму, и кнопку, которая действительно отправляет форму. `action.create-*` лучше ставить на submit-контрол, а opener делать отдельным auxiliary control (`control.open-create-*`) или явно отличать accessible name. Playwright-тесты должны scope-ить submit button внутри формы, а не использовать page-wide `getByRole('button', { name: 'Create' })`, который может совпасть и с opener, и с submit.
