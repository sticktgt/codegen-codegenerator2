# codegenerator2

`codegenerator2` — экспериментальный стенд для управляемой генерации демонстрационных прототипов приложений с помощью OpenCode/LLM-агентов.

Проект проверяет воспроизводимый pipeline: requirements-сценарий превращается в план изменений, план формально проверяется, агент реализует только разрешенные файлы, после чего Python-код проверяет границы изменений, UI anchors, validation, traceability и формирует итоговый отчет.

Основной контракт workflow:

```text
samples/<scenario>/run_input.json
→ runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход от requirements stage. `scenario_result.json` — основной машинно-читаемый итог для будущего UI/отчета.

## Основные принципы

- Pipeline-код не придумывает бизнес-логику, имена новых компонентов, тестов или функций.
- Агент на этапе planning предлагает `design_delta`, `file_plan` и `validation_plan`.
- Pipeline проверяет обязательные JSON outputs, безопасные пути, forbidden paths, allowed roots, dependency boundary, git diff boundary, UI anchors, validation и traceability.
- Реализация выполняется только в пределах утвержденного `file_plan.json`.
- Существующее поведение сохраняется по умолчанию и проверяется regression validation.
- Dependency/package changes допустимы только если они явно предложены планом, разрешены контрактом, включены в `file_plan.json` и имеют краткое обоснование.
- Частые repair-проблемы переводятся в переносимые kit-level patterns/examples, а не в частные Python-запреты.
- Итог выполнения читается через `scenario_result.json`; внутренние файлы используются для диагностики.

## Архитектурная идея

Цель проекта — генерировать код в рамках заранее описанного архитектурного шаблона, а не свободно редактировать репозиторий.

Активный kit задает уровни приложения:

- UI screens;
- UI widgets;
- frontend actions;
- backend API modules;
- backend services/components;
- backend data models;
- backend JSON storage/mock data;
- backend tests;
- browser/e2e tests;
- existing skeleton/integration files.

Требования описывают, что нужно реализовать. Architecture kit описывает, где и как это должно быть реализовано. Python pipeline контролирует процесс и границы, но не заменяет planner.

Planning flow:

```text
requirements + scheme context + architecture rules
→ model-generated design_delta / file_plan_draft / validation_plan_proposal
→ model self-check against architecture rules
→ formal Python plan validation
→ approved file_plan.json / validation_plan.json
```

Implementation flow:

```text
approved file_plan.json / validation_plan.json
→ OpenCode implementation
→ changed_files.json / UI static / task validate / traceability
→ scenario_result.json
```

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
```

### `architecture-profiles/`

Верхнеуровневые архитектурные профили. Сейчас есть:

```text
architecture-profiles/simple-crud-app/profile.yaml
```

Текущие исполняемые правила pipeline находятся в активном kit-е `prototype-kits/react-python-json-browser/`.

### `prototype-kits/`

Каталог architecture kit-ов. Активный kit:

```text
prototype-kits/react-python-json-browser/
```

Kit содержит template workspace, machine-readable contracts, manifest-ы композиции runtime-контекста и validation commands. Общие и стековые модули prompts, instructions, agents, examples и skills находятся в `prototype-kits/_shared/` и повторно используются kit-ами. Активный kit выбирает нужные модули декларативными manifest-ами; Python не выбирает модули по смыслу scenario.

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

- `cli/run_pipeline.py` — основной CLI orchestration;
- `phases/` — отдельные этапы pipeline: clean, prompt sync, sync inputs, OpenCode, reports, status;
- `plan_validation/` — formal validation planner output against architecture contract;
- `reports/` — `run_report.md` и `scenario_result.json`;
- `summary.py` — сбор `run_summary.json`, итогового статуса и usage summary.

### `tools/`

CLI entrypoints и helper tools.

Основные команды:

- `tools/prepare_run_from_scenario.py` — подготовка run из `samples/<scenario>/run_input.json`; materialize scenario input и вызывает подготовку workspace.
- `tools/prepare_workspace.py` — низкоуровневая подготовка workspace: копирование kit template или baseline из предыдущего run, overlay kit runtime files, копирование `prototype/input`, создание git baseline commit.
- `tools/run_pipeline.py` — совместимый entrypoint основного pipeline.
- `tools/run_opencode_phase.py` — запуск одной OpenCode-фазы с prompt prefix и expected outputs.
- `tools/validate_plan.py` — formal validation `plan_proposal.json` и `validation_plan_proposal.json`.
- `tools/collect_changes.py` — сбор git diff и boundary check против `file_plan.json`.
- `tools/run_ui_static_checks.py` — static checks UI anchors.
- `tools/run_validation.py` — запуск validation runner.
- `tools/build_code_traceability.py` — построение `code_traceability.json`.
- `tools/collect_agent_reports.py` — сбор JSON reports из `prototype/output`.
- `tools/export_artifact.py` — export `prototype_artifact.zip`.
- `tools/export_run_bundle.py` — export diagnostics bundle.
- `tools/sync_run_inputs.py` — синхронизация input artifacts в run/workspace.
- `tools/usage_metrics.py` — сбор usage deltas.

### `samples/`

Каталог входных сценариев. Каждый scenario описывает один slice для генерации.

Текущие sample groups:

```text
samples/notes-app/
samples/notes-app-slice-002/
samples/notes-app-slice-003-confirm-delete/
samples/notes-app-slice-004-note-count/
samples/tasks-app/
samples/customers-app/
samples/products-app/
samples/requests-app/
```

Типовой состав scenario:

```text
requirements.json
scheme_model.json
implementation_slice.json
run_input.json
mock_plan.json
data_sources.json
```

Назначение файлов:

- `requirements.json` — требования, которые нужно реализовать и проверить.
- `scheme_model.json` — схема/архитектурные элементы из requirements/design stage; не является доказательством существования кода.
- `implementation_slice.json` — compatibility view slice-а для prompt-ов и старых сценариев.
- `run_input.json` — канонический вход pipeline, который ссылается на остальные файлы scenario.
- `mock_plan.json` — план/описание mock data для прототипа.
- `data_sources.json` — описание источников данных и mock/storage ограничений.

### `runs/`

Runtime-директории запусков. В git хранится только `.gitkeep` и служебные baseline examples, если они явно добавлены.

Типовая структура run:

```text
runs/<run>/
  input/
  workspace/
  output/
  logs/
  usage/
  agent_reports/
  dist/
  opencode_plan_prompt.txt
  opencode_plan_review_prompt.txt
  opencode_implementation_prompt.txt
  opencode_repair_prompt.txt
```

### `workspace/` внутри run

`runs/<run>/workspace` — рабочее дерево, в котором OpenCode читает и пишет файлы.

Внутри workspace:

```text
backend/
frontend/
prototype/input/
prototype/output/
instructions/
agents/
examples/
.opencode/skills/
prompts/manifest.yaml
runtime/manifest.yaml
AGENTS.md
Taskfile.yml
opencode.json
kit.yaml
generation-rules.yaml
architecture-contract.yaml
```

Назначение основных частей:

- `backend/` — Python/FastAPI-compatible backend.
- `frontend/` — React prototype.
- `prototype/input/` — canonical и compatibility inputs, promoted `file_plan.json`, `validation_plan.json`, kit contracts и baseline context.
- `prototype/output/` — agent phase outputs и промежуточные отчеты внутри workspace.
- `instructions/` — materialized markdown runtime instructions из `runtime/manifest.yaml`.
- `agents/` — materialized OpenCode agent descriptions.
- `examples/` — materialized pattern examples.
- `.opencode/skills/` — optional OpenCode skills.
- `prompts/manifest.yaml` и `runtime/manifest.yaml` — kit manifests, доступные агенту как часть runtime context.
- `AGENTS.md`, `Taskfile.yml`, `opencode.json`, `kit.yaml`, `generation-rules.yaml`, `architecture-contract.yaml` — kit/runtime contracts.

При подготовке run workspace коммитится как baseline. Semantic generated changes должны появляться только после implementation/repair и только в allowed files из promoted file plan.

## Активный kit: `react-python-json-browser`

Активный kit:

```text
prototype-kits/react-python-json-browser/
```

Стек:

```text
frontend: React / JavaScript
backend: Python / FastAPI-compatible structure
storage: local JSON files
browser/e2e: Playwright
validation runner: Taskfile
```

Поддерживаемые capabilities текущего kit-а:

- list view;
- form editor;
- text search;
- local CRUD;
- local JSON storage;
- mock data;
- browser/e2e UI validation.

Ограничения из `kit.yaml`:

- `max_entities: 5`;
- `max_screens: 8`;
- `external_integrations: 0`.

### Структура kit-а

```text
prototype-kits/
  _shared/
    agents/
    examples/
    instructions/
      core/
      architecture-addons/
      frontend/react/
      backend/python-fastapi/
      storage/json/
      testing/
    prompts/
      core/
      stack/react-python-browser/
      storage/json/
      testing/pytest-playwright/
    skills/
  react-python-json-browser/
    kit.yaml
    generation-rules.yaml
    architecture-contract.yaml
    Taskfile.yml
    opencode.json
    AGENTS.md
    prompts/manifest.yaml
    runtime/manifest.yaml
    template/
```

### `kit.yaml`

Метаданные kit-а:

- id: `react-python-json-browser`;
- stack;
- supported capabilities;
- limits;
- default validation task;
- ссылка на `architecture-contract.yaml`;
- `prompt_manifest` — относительный путь к manifest композиции prompt-ов.
- `runtime_manifest` — относительный путь к manifest materialization для agents, instructions, examples и skills.

### `generation-rules.yaml`

Правила naming и mapping scheme elements → files. Это kit-specific файл: он описывает текущую структуру React/FastAPI/JSON prototype, а не универсальную схему для всех будущих стеков.

Основные секции:

- `name`, `version` — идентификация набора правил.
- `naming` — соглашения по преобразованию имен: PascalCase для экранов/компонентов/actions, snake_case для backend modules и storage files.
- `scheme_to_file_rules[]` — правила преобразования scheme element type в путь, artifact type и operation policy.
- `integration_files` — существующие skeleton/integration файлы, которые можно модифицировать только по плану.
- `forbidden_paths` — пути, которые generated implementation не должен создавать или менять.

Основные mapping rules:

```text
screen        → frontend/src/screens/{PascalName}Screen.jsx
widget        → frontend/src/widgets/{PascalName}.jsx
action        → frontend/src/actions/{PascalName}.js
component     → backend/app/services/{snake_name}.py
api           → backend/app/api/{snake_resource}.py
data_entity   → backend/app/models/{snake_name}.py
mock          → backend/app/storage/{snake_name}_mock.json
```

Integration files:

```text
frontend/src/routes/routeRegistry.js
frontend/src/App.jsx
backend/app/main.py
backend/app/storage/__init__.py
```

Обычные slices модифицируют integration files только при наличии соответствующего плана.

### `architecture-contract.yaml`

Machine-readable contract для pipeline validation. Это kit-specific контракт для текущего React/FastAPI/JSON/browser runtime.

Основные секции:

- `schema_version`, `id`, `version` — версия формата и идентификатор contract.
- `principles` — высокоуровневые ограничения: generated code не должен выходить за разрешенные слои, runtime files не являются semantic implementation changes.
- `run_input_contract` — какие входные файлы scenario/run считаются canonical input.
- `planner_output` — обязательная структура `plan_proposal.json`, `validation_plan_proposal.json`, `design_delta`, file plan и validation checks.
- `artifact_types` — допустимые artifact type, разрешенные operations и layer ownership.
- `path_policy` — allowed roots, forbidden roots, runtime/baseline paths, generated vs non-semantic artifacts.
- `validation_capabilities` — какие проверки поддерживает kit: backend pytest, build, ui_static, Playwright frontend behavior.
- `validation_policy` — как связывать validation checks с executable files, non-file checks и validation intent.
- `ui_validation` — контракт `data-prototype-id`, screen/widget/action anchors и правила static UI checks.
- `workspace_isolation` — workspace-root discipline и запрет на semantic changes вне workspace.

Этот файл используется formal plan validation, boundary checks, UI static checks и отчетностью. Он не заменяет markdown-инструкции, а задает машинно проверяемые ограничения для pipeline.

### `Taskfile.yml`

Команды validation/export.

Текущий `task validate` выполняет:

```text
install
smoke
test
build
frontend-behavior
```

Назначение task-ов:

- `install` — Python venv, backend dependencies, npm dependencies, Playwright Chromium.
- `smoke` — backend smoke import/health check.
- `test` — backend pytest.
- `build` — frontend production build через Vite.
- `frontend-behavior` — Playwright browser/e2e tests.
- `validate` — полный validation chain.
- `export` — упаковка prototype artifact.

### `opencode.json`

Конфигурация OpenCode для workspace.

### `agents/`

Agent descriptions для OpenCode:

```text
agents/prototype-builder.md
agents/prototype-reviewer.md
agents/prototype-repair.md
```

### Prompt-модули и `prompts/manifest.yaml`

Полные prompt-файлы больше не хранятся внутри kit-а как четыре монолитных источника. Kit задаёт декларативную композицию:

```text
prototype-kits/react-python-json-browser/prompts/manifest.yaml
prototype-kits/_shared/prompts/
  core/<phase>.md
  stack/react-python-browser/<phase>.md
  storage/json/<phase>.md
  testing/pytest-playwright/<phase>.md
```

`manifest.yaml` содержит:

- `version` — версия формата manifest;
- `path_base` — база разрешения путей (`repository`, `kit` или `manifest`);
- `phases` — mapping фаз `plan`, `plan-review`, `implementation`, `repair` в упорядоченные списки prompt-модулей.

Порядок модулей значим: `prompt_sync.py` объединяет их сверху вниз, без смыслового выбора по scenario. Для текущего kit-а каждая фаза получает общий модуль, модуль React/Python browser stack, модуль local JSON storage и модуль pytest/Playwright. При замене только хранилища можно сохранить остальные модули и заменить `storage/json` на модуль другого storage-профиля.

При `--sync-prompts` pipeline собирает по одному run snapshot на фазу:

```text
opencode_plan_prompt.txt
opencode_plan_review_prompt.txt
opencode_implementation_prompt.txt
opencode_repair_prompt.txt
```

Если `prompts/manifest.yaml` отсутствует или ссылается на отсутствующие модули, prompt sync возвращает предупреждение/ошибку синхронизации. Обратная совместимость с монолитными `prompts/*_prompt.md` не поддерживается.

### Runtime manifest и materialized runtime context

Файл:

```text
prototype-kits/react-python-json-browser/runtime/manifest.yaml
```

задает, какие shared-модули нужно материализовать в workspace перед запуском OpenCode. Он не анализирует scenario и не выбирает модули динамически: состав runtime-контекста полностью задан kit-ом.

Структура:

- `version` — версия формата manifest.
- `path_base` — база разрешения `source` путей: сейчас используется `repository`.
- `runtime.agents[]` — пары `source`/`target`, копируемые в `workspace/agents/`.
- `runtime.instructions[]` — пары `source`/`target`, копируемые в `workspace/instructions/`.
- `runtime.examples[]` — пары `source`/`target`, копируемые в `workspace/examples/`.
- `runtime.opencode[]` — пары `source`/`target`, копируемые в `workspace/.opencode/`; сейчас используется для skills.

Пример элемента:

```yaml
- source: prototype-kits/_shared/instructions/frontend/react
  target: frontend
```

означает: скопировать shared-модуль React-инструкций в `workspace/instructions/frontend/`.

После materialization workspace содержит runtime-копии:

```text
workspace/agents/
workspace/instructions/
workspace/examples/
workspace/.opencode/skills/
workspace/runtime/manifest.yaml
```

Эти файлы являются runtime context и baseline. Они не должны попадать в semantic generated changes.

### `instructions/`

Human-readable правила разбиты по зонам ответственности и хранятся как shared-модули. Kit materializes выбранный набор в `workspace/instructions/` через `runtime/manifest.yaml`.

```text
prototype-kits/_shared/instructions/
  core/
  architecture-addons/
  frontend/react/
  backend/python-fastapi/
  storage/json/
  testing/

workspace/instructions/
  core/
    architecture.md
    architecture-addons/react-python-json-browser.md
    coding.md
    planning.md
    file-boundaries.md
    traceability.md
    pipeline-output.md
    repair.md
    implementation-guidance.md
  frontend/
    react.md
    patterns/react-json-crud.md
  backend/
    python-fastapi.md
    storage-json.md
    patterns/fastapi-json-crud.md
  testing/
    validation-planning.md
    backend-pytest.md
    browser-e2e.md
    test-method-catalog.md
    examples/
```

`core/architecture.md` содержит постоянные правила. Stack/kit-specific часть вынесена в `core/architecture-addons/react-python-json-browser.md`. Prompt каждой фазы читает только нужные ей модули; небольшой обязательный baseline указан в `opencode.json`.

`test-method-catalog.md` задает допустимые test method ids, например:

```text
backend.pytest.api.mutable-state
backend.pytest.service.unit
backend.smoke.import-health
web.ui.static-anchors
web.e2e.playwright.crud-list-search-flow
web.e2e.playwright.form-submit-flow
web.e2e.playwright.item-action-flow
web.e2e.playwright.async-state-transition
web.e2e.playwright.filtered-list-flow
web.e2e.playwright.count-assertion
```

### `.opencode/skills/`

Runtime manifest materializes экспериментальный некритичный skill:

```text
.opencode/skills/prototype-crud-flow/SKILL.md
```

Он доступен через native OpenCode skill tool как компактный CRUD-checklist. Канонические `instructions/` остаются источником правил, поэтому отсутствие или неиспользование skill не ломает pipeline.

### `examples/`

Короткие примеры patterns, не готовое приложение:

```text
examples/simple-crud/README.md
examples/search-filter/README.md
```

### `template/`

`template/` — минимальный skeleton проекта прототипа. Он копируется только при greenfield-подготовке run-а. Kit runtime (`AGENTS.md`, `opencode.json`, `Taskfile.yml`, kit prompt manifest и materialized modules из `runtime/manifest.yaml`) накладывается отдельно, поэтому обновляется также при incremental run поверх предыдущего workspace. Общие prompt-модули остаются repository-level источниками и собираются в run snapshots до запуска OpenCode; instructions/agents/examples/skills materialize в workspace.

Состав skeleton-а:

```text
template/
  backend/
    requirements.txt
    app/
      __init__.py
      main.py
      smoke.py
      api/__init__.py
      models/__init__.py
      services/__init__.py
      storage/__init__.py
    tests/
      __init__.py
      test_smoke.py
  frontend/
    package.json
    playwright.config.js
    vite.config.js
    e2e/.gitkeep
    src/
      App.jsx
      main.jsx
      actions/.gitkeep
      api/.gitkeep
      routes/routeRegistry.js
      screens/.gitkeep
      widgets/.gitkeep
  prototype/
    input/.gitkeep
    output/.gitkeep
```

Назначение skeleton-а:

- дать рабочий backend/frontend baseline до генерации feature-кода;
- зафиксировать integration files, которые agent должен не создавать заново, а модифицировать;
- дать `Taskfile.yml` validation commands через kit-level runtime files;
- дать `App.jsx` и `routeRegistry.js` contract для подключения первого generated screen;
- дать smoke test и `/health` endpoint для проверки, что baseline backend импортируется.

Generated code добавляется поверх skeleton-а на этапе OpenCode implementation. В greenfield slice обычно создаются новые owned-файлы в `backend/app/api`, `backend/app/services`, `backend/app/models`, `backend/app/storage`, `backend/tests`, `frontend/src/screens`, `frontend/src/widgets`, `frontend/e2e`, а skeleton/integration files изменяются по file plan.

## Scenario/run input files

Каждый sample содержит набор входных файлов requirements-stage/result-stage. На практике canonical входом для нового pipeline является `run_input.json`; остальные файлы остаются compatibility/context views и копируются в `workspace/prototype/input/`.

### `run_input.json`

Canonical scenario input. Основные поля:

- `run_input_version` — версия формата.
- `source` — источник или имя sample/scenario.
- `slice` — описание текущего implementation slice: `id`, `title`, `goal`, `change_type`, `selected_existing_elements`, `acceptance_criteria`, `constraints`, `non_goals`, `validation_expectations`.
- `requirements[]` — требования текущего slice с `id`, текстом, acceptance criteria и связанными метаданными.
- `scenario_notes[]` — дополнительные пояснения для pipeline/агента; не являются file plan.

`run_input.json` описывает намерение и критерии приемки. Он не предписывает имена файлов, artifact types, policies или конкретные операции изменения кода.

### `implementation_slice.json`

Compatibility view для текущего pipeline. Основные поля:

- `slice_id`, `title`, `goal`, `change_type`.
- `requirements[]` — требования текущего slice.
- `selected_existing_elements[]` — элементы схемы, выбранные requirements stage или analyst input как контекст.
- `preserve_existing_behavior_by_default` — правило сохранения уже принятого поведения.
- `acceptance_criteria[]`, `constraints[]`, `non_goals[]`, `validation_expectations[]`.

Planner должен использовать этот файл как входной контекст, но не как готовый file plan.

### `requirements.json`

Список требований. Обычно содержит:

- `requirements[]` — id, title/text, priority/type, acceptance criteria, notes/constraints.

В новых сценариях `run_input.json` является более полным canonical input, но `requirements.json` сохраняется для совместимости и явного requirements context.

### `scheme_model.json`

Схема логических элементов прототипа. Основные поля:

- `scheme_id`, `title`.
- `elements[]` — элементы вроде `screen.*`, `widget.*`, `action.*`, `api.*`, `service.*`, `data.*`.

Элементы могут содержать id, type, title/name, responsibilities, связанные requirements и связи с другими элементами. В incremental runs схема может быть неполной: отсутствие элемента в `scheme_model.json` не означает, что его нет в workspace или baseline traceability.

### `data_sources.json`

Описание источников данных для прототипа. Основные поля:

- `data_sources[]` — логическое имя, тип, resource/entity, ожидаемый формат, seed/mock source или ограничения.

Для текущего kit-а это обычно локальные JSON/mock источники.

### `mock_plan.json`

План mock data. Основные поля:

- `mocks[]` — какие mock files/data sets нужны, какие entities и поля должны быть представлены, какие seed records ожидаются.

Файл помогает агенту понять требуемую форму mock data, но не заменяет `generation-rules.yaml` и file plan.

## Samples подробно

### `customers-app`

Назначение: проверить переносимость CRUD/list/search правил на customer directory без task/note-specific имен.

Поля:

```text
full_name
email
phone
segment
```

Требования:

- create customer;
- edit contact data: email and phone;
- list customers with full_name, email, phone, segment;
- search by name, email, or phone;
- delete не требуется.

Ожидаемые generated элементы:

```text
frontend screen: customer directory
backend API: /api/customers
backend service/model/storage
backend pytest
browser/e2e CRUD/list/search flow
```

### `products-app`

Назначение: проверить переносимость правил на другой UI-профиль: search + category filter + numeric price.

Поля:

```text
name
sku
category
price
```

Category enum:

```text
hardware
software
service
```

Требования:

- create product;
- edit price and category;
- list products;
- search by name or SKU;
- filter by category;
- delete не требуется.

Ожидаемые generated элементы:

```text
frontend screen: product catalog
search/filter widget или screen-internal controls
backend API: /api/products
backend service/model/storage
backend pytest
browser/e2e CRUD/list/search/filter flow
```

### `requests-app`

Назначение: проверить переносимость правил на сценарий со статусами, приоритетами и датой.

Поля:

```text
title
requester
status
priority
due_date
```

Status enum:

```text
new
in_progress
done
```

Priority enum:

```text
low
normal
high
```

Требования:

- create service request;
- edit status and priority;
- list requests;
- search by title or requester;
- filter by status;
- filter by priority;
- delete не требуется.

Ожидаемые generated элементы:

```text
frontend screen: request board
search/filter widget или screen-internal controls
backend API: /api/requests
backend service/model/storage
backend pytest
browser/e2e CRUD/list/search/filter flow
```

## Как формируется workspace

Run workspace находится в:

```text
runs/<run>/workspace/
```

Workspace создается до OpenCode-фаз. OpenCode не создает структуру проекта с нуля. Он работает внутри уже подготовленного workspace.

### Greenfield workspace

Для обычного нового scenario используется команда:

```bash
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/<scenario>/run_input.json \
  --run runs/<run> \
  --kit prototype-kits/react-python-json-browser
```

Последовательность подготовки:

```text
tools/prepare_run_from_scenario.py
  → читает canonical run_input.json
  → определяет sample directory
  → materialize scenario input files
  → вызывает tools/prepare_workspace.py

tools/prepare_workspace.py
  → создает runs/<run>/workspace
  → копирует prototype-kits/react-python-json-browser/template/* в workspace
  → копирует runtime kit files: AGENTS.md, Taskfile.yml, opencode.json, prompts/manifest.yaml и materialized agents/, instructions/, .opencode/skills/, examples/ из runtime/manifest.yaml
  → копирует kit.yaml, generation-rules.yaml, architecture-contract.yaml в workspace/prototype/input
  → копирует scenario files в workspace/prototype/input
  → инициализирует git repository внутри workspace
  → создает baseline commit
```

После подготовки greenfield workspace содержит только skeleton и input artifacts. Feature-код еще не создан.

### Что делает OpenCode после подготовки workspace

```text
OpenCode plan
  → читает workspace skeleton, prototype/input и instructions
  → пишет prototype/output/plan_proposal.json
  → пишет prototype/output/validation_plan_proposal.json

formal plan validation
  → проверяет plan proposal
  → копирует утвержденные планы в prototype/input/file_plan.json и prototype/input/validation_plan.json

OpenCode implementation
  → создает owned generated files
  → модифицирует integration/skeleton files, разрешенные file_plan.json
  → пишет implementation_report.json и change_manifest.json
```

Для текущего kit-а типичные generated files:

```text
backend/app/api/<resources>.py
backend/app/services/<resource>_service.py
backend/app/models/<entity>.py
backend/app/storage/<resource>_mock.json
backend/tests/test_<resource>_api.py
frontend/src/screens/<Screen>.jsx
frontend/src/widgets/<Widget>.jsx
frontend/e2e/<spec>.js
```

Типичные modified skeleton/integration files:

```text
backend/app/main.py
backend/app/storage/__init__.py
frontend/src/routes/routeRegistry.js
```

### Incremental workspace из предыдущего run

Для последовательной доработки существующего прототипа используется `--from-run`:

```bash
python3 tools/prepare_run_from_scenario.py \
  --from-run runs/<previous-successful-run> \
  --scenario samples/<next-slice>/run_input.json \
  --run runs/<new-run> \
  --kit prototype-kits/react-python-json-browser
```

В этом режиме baseline нового workspace формируется не из пустого `template/`, а из workspace предыдущего run-а.

Последовательность:

```text
tools/prepare_workspace.py
  → копирует runs/<previous-successful-run>/workspace в runs/<new-run>/workspace
  → удаляет runtime outputs и transient directories
  → overlay текущих kit runtime files, включая materialized instructions, skills, agents, examples и kit prompt manifest
  → заменяет prototype/input на input нового scenario
  → инициализирует новый git baseline commit
```

Код, созданный в предыдущем успешном run-е, остается в новом workspace и становится baseline. Новый slice должен планировать изменения поверх него: `modify` существующих feature-файлов, `create` новых owned-файлов только когда это действительно новый экран, новый ресурс, новый тестовый файл или новый слой реализации.

`--clean` в `tools/run_pipeline.py` не отменяет incremental baseline. Он делает reset/clean внутри уже подготовленного workspace и возвращает workspace к baseline commit нового run-а.

### Что должно отличать incremental scenario

Incremental scenario должен описывать следующий slice, а не повторять весь baseline. В `run_input.json` используется `change_type: "extend_existing"` или аналогичный смысловой признак текущего slice, а требования описывают только новую доработку.

Пример:

```json
{
  "slice": {
    "slice_id": "SLICE-002",
    "title": "Add product stock tracking",
    "change_type": "extend_existing",
    "requirement_ids": ["REQ-006", "REQ-007"],
    "selected_existing_elements": [
      "screen.product-catalog",
      "api.products",
      "component.product-service",
      "data.product"
    ],
    "preserve_existing_behavior_by_default": true
  }
}
```

Ожидаемый file plan для такого slice обычно содержит:

```text
modify backend/app/models/product.py
modify backend/app/services/product_service.py
modify backend/app/api/products.py
modify frontend/src/screens/ProductCatalogScreen.jsx
modify backend/tests/test_products_api.py
modify frontend/e2e/<existing-or-new-spec>.js
```

## Pipeline: этапы, входы, выходы и исполнитель

| Этап | Исполнитель | Входы | Выходы | Смысл |
|---|---|---|---|---|
| prepare run | Python | `samples/<scenario>/run_input.json`, kit | `runs/<run>/workspace`, `runs/<run>/input` | Материализация run workspace и входов |
| clean/sync | Python | run, kit | очищенные output/logs/usage/dist, synced inputs/prompts | Воспроизводимое состояние перед запуском |
| OpenCode plan | OpenCode/LLM | `prototype/input/*`, `instructions/*`, workspace files | `plan_proposal.json`, `validation_plan_proposal.json` | План реализации и проверок |
| collect plan reports | Python | phase outputs | `agent_reports` | Сбор reports модели |
| validate plan | Python | plan proposal, architecture contract | `plan_validation_result.json`, approved plan inputs | Formal validation и утверждение плана |
| OpenCode plan-review | OpenCode/LLM | plan proposal, inputs, rules | `plan_review.json` | Дополнительная проверка плана моделью |
| OpenCode implementation | OpenCode/LLM | approved `file_plan.json`, `validation_plan.json` | source/test files, `implementation_report.json`, `change_manifest.json` | Реализация slice |
| collect changes | Python | git diff, `file_plan.json` | `changed_files.json`, `workspace.diff` | Boundary и список изменений |
| UI static checks | Python | generated UI, validation plan | `ui_static_check_result.json` | Проверка `data-prototype-id` anchors |
| validation | Python/Taskfile | workspace | `validation_result.json`, logs | `task validate` |
| repair | OpenCode/LLM | repair context, validation/boundary/ui results | `repair_report.json`, исправленные allowed files | Исправление repairable failures |
| traceability | Python | requirements, file plan, validation plan, changed files | `code_traceability.json` | Покрытие требований кодом и проверками |
| summary/report/export | Python | все outputs | `run_summary.json`, `scenario_result.json`, `run_report.md`, zip artifacts | Итоговый отчет и артефакты |

## Этап validation подробнее

Validation запускается командой kit-а:

```bash
task validate
```

Для текущего kit-а последовательность такая:

```text
install → smoke → test → build → frontend-behavior
```

Результаты сохраняются:

```text
runs/<run>/output/validation_result.json
runs/<run>/output/validation.stdout.log
runs/<run>/output/validation.stderr.log
```

`validation_result.json` фиксирует status, task, duration, stage results и ссылки на logs.

`frontend-behavior` запускает Playwright tests из `frontend/e2e/`.

## Repair

Repair запускается только при `--allow-repair` и только после repairable failure.

Repair получает контекст:

```text
prototype/output/repair_context.json
prototype/output/validation_result.json
prototype/output/changed_files.json
prototype/output/ui_static_check_result.json
```

Repair должен:

- исправлять только файлы, разрешенные `file_plan.json`;
- не расширять scope;
- не добавлять новые files вне плана;
- не менять requirements/sample/kit/pipeline;
- писать `prototype/output/repair_report.json`.

После repair pipeline повторяет:

```text
collect changes → UI static checks → validation
```

Максимум попыток задается `--max-repair-attempts`.

## Итоговый отчет `scenario_result.json`

Путь:

```text
runs/<run>/output/scenario_result.json
```

Top-level структура:

```text
scenario_result_version
run
slice
final_status
stage_status
changed_files
validation
traceability
repair
artifacts
usage
inputs
```

Смысл основных секций:

- `slice` — slice id, title, goal, change type, requirement ids, acceptance criteria.
- `stage_status` — статусы основных этапов: plan, plan_review, implementation, repair, plan_validation, boundary, ui_static, validation, traceability, final.
- `changed_files` — semantic changes, created/modified/deleted/renamed files, unexpected files, policy violations, missing required files, counts.
- `validation` — статус validation, task, duration, stdout/stderr logs, UI static result, validation checks.
- `traceability` — статус покрытия требований, primary requirements, supporting regressions, gaps, validation check ids.
- `repair` — использовался ли repair, какие repair phases запускались и с каким статусом.
- `artifacts` — пути к `prototype_artifact.zip`, `run_diagnostics.zip`, `run_report.md`, `run_summary.json`, `code_traceability.json`, `workspace.diff`.
- `usage` — requested models, usage totals и usage по фазам.
- `inputs` — ссылки на run input, implementation slice, file plan и validation plan.

Успешный запуск имеет:

```text
final_status: passed
stage_status.validation: passed
stage_status.boundary: passed
stage_status.ui_static: passed
stage_status.traceability: passed
traceability.gaps: []
```

## Другие отчетные файлы

```text
runs/<run>/output/run_summary.json
```

Полный pipeline summary: opencode results, usage, plan validation, boundary, validation, traceability, ui_static, diagnostics.

Основные поля:

- `run`, `workspace`, `kit` — идентификаторы запуска и путей.
- `stage_status` или stage-specific sections — результат каждой стадии pipeline.
- `opencode` / `phases` — результаты phase calls, статусы, usage и ссылки на логи.
- `plan_validation`, `boundary`, `ui_static`, `validation`, `traceability`, `repair` — агрегаты соответствующих стадий.
- `artifacts` — ссылки на diagnostics/report/export artifacts.

```text
runs/<run>/output/sync_run_inputs_result.json
```

Результат синхронизации kit/runtime/input файлов в workspace. Основные поля:

- `run`, `workspace`, `kit` — пути запуска.
- `actions[]` — выполненные действия, например `sync_kit.yaml`, `sync_generation-rules.yaml`, `sync_architecture-contract.yaml`, `sync_runtime_instructions`, `sync_runtime_.opencode`, `sync_runtime_runtime`, `sync_prototype_input_instructions`.
- `warnings[]` — отсутствующие manifest/source files или другие проблемы materialization.
- `runtime_manifest` — manifest, по которому материализован runtime context, если поле присутствует в текущей версии отчета.

Пустой `warnings[]` означает, что kit contracts, runtime context и compatibility-копии input-инструкций синхронизированы без замечаний.

```text
runs/<run>/output/run_report.md
```

Markdown-отчет для человека.

```text
runs/<run>/output/sync_prompt_files_result.json
```

Результат проверки и синхронизации prompt snapshots. Основные поля:

- `run` — путь run-а;
- `kit` — определенный активный kit;
- `sync_requested` — был ли запрошен режим обновления snapshots;
- `prompts[]` — результат по каждой фазе;
- `warnings[]` — stale/missing/invalid manifest, external override и другие проблемы синхронизации.

Элемент `prompts[]` содержит:

- `phase` — `plan`, `plan-review`, `implementation` или `repair`;
- `prompt_file` — run snapshot, передаваемый OpenCode;
- `composition_manifest` — manifest, по которому собран prompt;
- `kit_sources[]` — упорядоченный список исходных prompt-модулей;
- `missing_sources[]` — отсутствующие модули;
- `managed_snapshot` — может ли pipeline обновлять этот файл;
- `action` — `composed_from_kit`, `none`, `check_only` или `not_synced`;
- `status` — `synced`, `up_to_date`, `stale`, `external_override`, `kit_prompt_missing`, `kit_prompt_invalid` или `kit_not_found`;
- `prompt_sha256`, `kit_source_sha256` — hashes snapshot и собранного источника.

```text
runs/<run>/output/code_traceability.json
```

Связь requirements ↔ allowed files ↔ changed files ↔ validation checks. Основные поля: requirements coverage, changed-file mapping, validation check mapping, gaps, implemented-not-validated items.

```text
runs/<run>/output/changed_files.json
```

Boundary result и подробный список изменений. Основные поля:

- `status` — passed/failed.
- `semantic_changes` или grouped changed files — created/modified/deleted/renamed semantic files.
- `unexpected_files`, `policy_violations`, `missing_required_files`, `missing_required_changes`.
- `runtime_mutated_files`, `non_semantic_changes` — runtime/log/test artifacts, которые не должны считаться generated implementation.

```text
runs/<run>/output/ui_static_check_result.json
```

UI anchor checks: checked files, warnings, blockers. Основные поля:

- `status` — passed/failed.
- `checks[]` или checked files — какие anchors проверялись.
- `warnings[]` — advisory diagnostics, например хрупкие e2e locators.
- `blockers[]` — нарушения обязательных UI anchors при strict UI checks.

```text
runs/<run>/output/validation_result.json
```

Результат `task validate`: список steps, команды, статусы, duration, stdout/stderr excerpts и общий validation status.

```text
runs/<run>/output/repair_context.json
```

Компактный вход для repair phase. Содержит failure summary, failing validation steps, boundary/static issues, allowed file plan и подсказки для целевого repair. Repair-agent читает этот файл как основной стартовый контекст.

```text
runs/<run>/workspace/prototype/output/agent_reports/*.json
```

Отчеты, которые пишет OpenCode внутри workspace: `plan_proposal.json`, `validation_plan_proposal.json`, `plan_review.json`, `implementation_report.json`, `change_manifest.json`, `repair_report.json`. Pipeline копирует/использует их для promotion, validation, traceability и diagnostics.

```text
runs/<run>/dist/prototype_artifact.zip
```

Архив с generated prototype: `frontend`, `backend`, `prototype` без node_modules, venv, frontend dist и Playwright runtime outputs.

```text
runs/<run>/dist/run_diagnostics.zip
```

Diagnostics archive для анализа запуска.

## Запуск scenarios

### Подготовка run

Команда:

```bash
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/<scenario>/run_input.json \
  --run runs/<run> \
  --kit prototype-kits/react-python-json-browser
```

Параметры:

- `--scenario` — путь к canonical `run_input.json`.
- `--sample` — директория для файлов, referenced by `run_input.json`; по умолчанию parent directory scenario.
- `--from-run` — предыдущий успешный run для incremental baseline; если указан, workspace нового run-а копируется из предыдущего workspace, а не из пустого `template/`.
- `--run` — новая runtime-директория.
- `--kit` — активный kit.

`prepare_run_from_scenario.py` является удобной командой верхнего уровня. Низкоуровневую materialization workspace выполняет `tools/prepare_workspace.py`; напрямую его обычно запускать не нужно.

### Запуск pipeline

Базовая команда:

```bash
python3 tools/run_pipeline.py \
  --run runs/<run> \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/<run>/opencode_plan_prompt.txt \
  --review-prompt-file runs/<run>/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/<run>/opencode_implementation_prompt.txt \
  --allow-repair \
  --max-repair-attempts 2 \
  --repair-prompt-file runs/<run>/opencode_repair_prompt.txt
```

Параметры `run_pipeline.py`:

- `--run` — runtime-директория запуска.
- `--kit` — kit directory для sync architecture contract, generation rules, inputs и materialized runtime context.
- `--sync-prompts` — собрать и обновить run prompt snapshots по `prompt_manifest`.
- `--clean` — очистить output/logs/usage/dist и reset workspace перед запуском.
- `--clean-root-prototype-output` — вместе с `--clean` удалить stale `./prototype/output` artifacts в root проекта.
- `--keep-plan-inputs` — вместе с `--clean` сохранить existing `file_plan.json` и `validation_plan.json`.
- `--skip-review` — пропустить OpenCode plan-review phase.
- `--fail-on-workspace-leak` — считать чтение/glob project files outside workspace ошибкой OpenCode-фазы.
- `--strict-ui-checks` — считать UI static blockers repairable failures.
- `--model` — модель OpenCode для всех OpenCode-фаз.
- `--plan-prompt-file` — prompt snapshot для plan phase.
- `--review-prompt-file` — prompt snapshot для plan-review phase.
- `--implementation-prompt-file` — prompt snapshot для implementation phase.
- `--repair-prompt-file` — prompt snapshot для repair phase.
- `--allow-repair` — разрешить repair attempts.
- `--max-repair-attempts` — максимум repair attempts.
- `--skip-validation` — пропустить validation stage.
- `--no-stream` — не зеркалировать OpenCode logs в stdout во время фаз.

### Пример запуска products-app

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-004-products-app-browser

python3 tools/prepare_run_from_scenario.py \
  --scenario samples/products-app/run_input.json \
  --run runs/run-004-products-app-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-004-products-app-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-004-products-app-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-004-products-app-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-004-products-app-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --max-repair-attempts 2 \
  --repair-prompt-file runs/run-004-products-app-browser/opencode_repair_prompt.txt
```

### Пример запуска customers-app

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-003-customers-app-browser

python3 tools/prepare_run_from_scenario.py \
  --scenario samples/customers-app/run_input.json \
  --run runs/run-003-customers-app-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-003-customers-app-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-003-customers-app-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-003-customers-app-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-003-customers-app-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --max-repair-attempts 2 \
  --repair-prompt-file runs/run-003-customers-app-browser/opencode_repair_prompt.txt
```

### Пример запуска requests-app

```bash
cd ~/opencode/codegenerator2

rm -rf runs/run-005-requests-app-browser

python3 tools/prepare_run_from_scenario.py \
  --scenario samples/requests-app/run_input.json \
  --run runs/run-005-requests-app-browser \
  --kit prototype-kits/react-python-json-browser

python3 tools/run_pipeline.py \
  --run runs/run-005-requests-app-browser \
  --kit prototype-kits/react-python-json-browser \
  --sync-prompts \
  --clean \
  --clean-root-prototype-output \
  --strict-ui-checks \
  --model ollama-cloud/qwen3.5:397b \
  --plan-prompt-file runs/run-005-requests-app-browser/opencode_plan_prompt.txt \
  --review-prompt-file runs/run-005-requests-app-browser/opencode_plan_review_prompt.txt \
  --implementation-prompt-file runs/run-005-requests-app-browser/opencode_implementation_prompt.txt \
  --allow-repair \
  --max-repair-attempts 2 \
  --repair-prompt-file runs/run-005-requests-app-browser/opencode_repair_prompt.txt
```

### Пример запуска notes baseline

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
  --max-repair-attempts 2 \
  --repair-prompt-file runs/run-001-notes-app-browser/opencode_repair_prompt.txt
```

### Пример incremental run

```bash
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/notes-app-slice-003-confirm-delete/run_input.json \
  --from-run runs/run-001-notes-app-browser \
  --run runs/run-003-confirm-delete-browser \
  --kit prototype-kits/react-python-json-browser
```

После prepare incremental run запускается той же командой `tools/run_pipeline.py`, но с новым `--run`.

## Ожидаемые свойства generated code для текущего kit-а

### Backend

- Feature API module в `backend/app/api/<resources>.py`.
- Service module в `backend/app/services/<resource>_service.py`.
- Data model в `backend/app/models/<resource>.py`.
- Mock storage в `backend/app/storage/<resource>_mock.json` или другом пути, утвержденном file plan.
- Public API path: `/api/<resources>`.
- Router pattern:

```python
router = APIRouter(prefix="/<resources>")
```

- Main wiring:

```python
app.include_router(<resources>_router, prefix="/api")
```

- Tests use direct dependency override:

```python
from app.api.<resources> import get_<resource>_service
app.dependency_overrides[get_<resource>_service] = override
```

- Test storage uses full temp path.
- Query params are consistent across API, frontend and tests.

### Frontend

- Main screen в `frontend/src/screens/<Entity>Screen.jsx`.
- Widgets в `frontend/src/widgets/` или screen-internal, если это указано планом.
- Route registry exports `component`, not `element`:

```javascript
export const routes = [
  {
    path: '/',
    component: ProductCatalogScreen
  }
];
```

- UI uses `data-prototype-id` anchors for screen, widget, form, fields, actions and item rows/cards.
- Clear/reset handlers pass explicit reset values into loader.
- Browser/e2e uses runtime-owned values and waits for rows/cards before count assertions.

## Что коммитить в git

Коммитить:

- source code pipeline;
- kit files;
- samples;
- documentation;
- `.gitkeep` in runtime dirs if needed.

Не коммитить:

- run outputs;
- logs;
- usage files;
- generated prototype artifacts;
- node_modules;
- Python virtual environments;
- Playwright reports and test-results;
- transient workspace outputs.

## Проверка после изменений проекта

Для Python files:

```bash
python3 -m py_compile <changed-python-file>
python3 tools/run_pipeline.py --help
python3 tools/validate_plan.py --help
```

Для JSON sample files:

```bash
python3 -m json.tool samples/<scenario>/requirements.json >/dev/null
python3 -m json.tool samples/<scenario>/scheme_model.json >/dev/null
python3 -m json.tool samples/<scenario>/implementation_slice.json >/dev/null
python3 -m json.tool samples/<scenario>/run_input.json >/dev/null
python3 -m json.tool samples/<scenario>/mock_plan.json >/dev/null
python3 -m json.tool samples/<scenario>/data_sources.json >/dev/null
```

Для подготовки sample:

```bash
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/<scenario>/run_input.json \
  --run /tmp/<run-name> \
  --kit prototype-kits/react-python-json-browser
```

Для generated prototype validation:

```bash
cd runs/<run>/workspace
task validate
```

Для archive:

```bash
unzip -t /path/to/archive.zip
```

## Текущий рабочий фокус

Текущий активный путь проверки — переносимые demo-focused rules для `react-python-json-browser` kit на разных samples.

Проверяемые группы сценариев:

- `customers-app` — search по нескольким текстовым полям;
- `products-app` — search + category filter + numeric price;
- `tasks-app` — status/date oriented CRUD/list/filter flow;
- `notes-app` и incremental slices — baseline/incremental behavior.

Новые правила добавляются в kit как общие patterns/contracts, когда проблема повторяема или влияет на видимый demo-flow. Частные исправления под один sample не являются целевым результатом.

