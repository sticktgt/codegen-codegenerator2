# AGENTS.md

Краткий технический контекст для агента или другого чата, который будет дорабатывать проект `codegenerator2`.

Документ описывает текущую версию проекта и активный kit `react-python-json-browser`. Он предназначен для быстрого ввода агента в проект без обязательного чтения всего кода и всех markdown-инструкций. Детальные правила остаются в kit-инструкциях и prompt-файлах.

## Назначение проекта

`codegenerator2` — стенд для управляемой генерации демонстрационных прототипов приложений через OpenCode/LLM-агентов.

Основной workflow:

```text
samples/<scenario>/run_input.json
→ runs/<run>/workspace
→ OpenCode plan
→ formal plan validation
→ OpenCode plan-review
→ OpenCode implementation
→ boundary checks
→ UI static checks
→ validation
→ traceability
→ runs/<run>/output/scenario_result.json
```

Главный контракт:

```text
samples/<scenario>/run_input.json → runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход от requirements stage. `scenario_result.json` — основной машинно-читаемый результат запуска для будущего UI/отчета.

## Архитектурная идея

Проект генерирует код не как свободный diff, а как реализацию требований внутри заранее описанного architecture kit-а.

Активный kit разделяет приложение на уровни:

- frontend screen;
- frontend widget;
- frontend action;
- backend API;
- backend service/component;
- backend data model;
- backend JSON storage/mock data;
- validation tests;
- существующие skeleton/integration files.

Модель отвечает за содержательное планирование и реализацию:

- читает требования и контекст текущего run-а;
- читает правила активного kit-а из workspace;
- формирует `design_delta`, `file_plan` и `validation_plan`;
- самопроверяет план до записи JSON;
- реализует только утвержденный `file_plan.json`;
- исправляет ошибки только в разрешенных файлах.

Python pipeline отвечает за порядок выполнения, технические границы, запуск проверок, сбор отчетов и export artifacts. Python-код не должен становиться вторым архитектурным planner-ом и не должен переносить в себя предметные правила конкретных сценариев.

## Активный kit

Активный kit:

```text
prototype-kits/react-python-json-browser/
```

Стек kit-а:

```text
frontend: React / JavaScript
backend: Python / FastAPI
storage: local JSON files
browser validation: Playwright
validation runner: Taskfile
```

Основные файлы kit-а:

```text
prototype-kits/
  _shared/
    agents/
    examples/
    instructions/
    prompts/
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

Назначение основных файлов:

- `kit.yaml` — метаданные kit-а, stack, capabilities, limits, default validation task, путь `prompt_manifest` и путь `runtime_manifest`.
- `generation-rules.yaml` — naming и mapping scheme elements в пути файлов.
- `architecture-contract.yaml` — machine-readable contract: artifact types, allowed roots, operations, validation capabilities, workspace isolation.
- `Taskfile.yml` — команды `install`, `smoke`, `test`, `build`, `frontend-behavior`, `validate`, `export`.
- `opencode.json` — конфигурация OpenCode внутри workspace.
- `prompts/manifest.yaml` — декларативный состав prompt-модулей для фаз `plan`, `plan-review`, `implementation`, `repair`.
- `runtime/manifest.yaml` — декларативный состав agents, instructions, examples и skills, материализуемых в workspace.
- `template/` — только минимальный greenfield skeleton workspace; runtime-контекст накладывается отдельно и при incremental run.

`architecture-contract.yaml` и `generation-rules.yaml` описывают архитектурные уровни и допустимые операции. Бизнес-логика приходит из `samples/<scenario>/requirements.json`, `scheme_model.json`, `run_input.json` и `implementation_slice.json`.

## Дисциплина путей workspace

OpenCode-фазы работают внутри текущего run workspace:

```text
runs/<run>/workspace/
```

Канонические пути внутри workspace:

```text
prototype/input/...      входы текущего run-а
instructions/...         markdown-инструкции, материализованные из shared-модулей активного kit-а
prompts/...              prompt snapshots для диагностики
frontend/...             frontend prototype files
backend/...              backend prototype files
prototype/output/...     обязательные outputs фаз
```

Правила чтения:

- читать `instructions/...` из текущего workspace;
- не читать repository-root `/instructions/...`;
- не использовать source files из `prototype-kits/...` как состояние текущего run-а;
- `prototype/input/instructions/...` — compatibility mirror, если он создан pipeline; основной prompt-facing путь — `instructions/...`.

Правила записи:

- писать generated code только в файлы, разрешенные `prototype/input/file_plan.json`;
- писать phase reports только в `prototype/output/...`;
- не писать в `samples/`, `prototype-kits/`, `architecture-profiles/`, `tools/`, `prototype_pipeline/` во время OpenCode implementation/repair.

## Роль Python-кода

Python pipeline выполняет:

- подготовку workspace;
- синхронизацию kit context;
- синхронизацию run inputs;
- синхронизацию prompt snapshots при `--sync-prompts`;
- запуск OpenCode-фаз;
- проверку обязательных JSON outputs;
- formal plan validation;
- сбор agent reports;
- сбор git diff;
- проверку boundary по утвержденному `file_plan.json`;
- UI static checks по `data-prototype-id` anchors;
- запуск `task validate`;
- сбор traceability;
- сбор usage metrics;
- формирование `run_summary.json`, `scenario_result.json`, `run_report.md`;
- export prototype artifact и diagnostics archive.

Python pipeline не выполняет:

- генерацию бизнес-логики;
- выбор новых feature-файлов за модель;
- выбор имен тестов за модель;
- содержательную нормализацию `artifact_type`;
- автоматическое исправление неверного архитектурного слоя;
- замену kit-level test contracts частными Python-эвристиками.

Допустимые Python checks — технические и machine-readable: безопасные пути, forbidden paths, dependency boundary, обязательные files, JSON shape, UI anchors, validation status, traceability status.

## Этапы pipeline

### 1. Подготовка run

CLI:

```bash
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/<scenario>/run_input.json \
  --run runs/<run> \
  --kit prototype-kits/react-python-json-browser
```

Создает `runs/<run>/workspace` из kit template и материализует входы в `runs/<run>/input` и `runs/<run>/workspace/prototype/input`.

Для incremental run используется `--from-run <previous-successful-run>`.

### 2. Очистка и синхронизация

`run_pipeline.py --clean` сбрасывает runtime outputs/logs/usage/dist и workspace к baseline.

`--sync-prompts` собирает run prompt snapshots из модулей, перечисленных активным kit prompt manifest. Python не выбирает модули по содержанию scenario: порядок и состав полностью задаются manifest-ом. Монолитные legacy prompt-файлы не поддерживаются.

`--kit` синхронизирует в run architecture contract, generation rules, kit metadata и materialized runtime context.

### 3. OpenCode plan

Модель читает `prototype/input/...`, `instructions/...`, существующие files workspace и пишет:

```text
prototype/output/plan_proposal.json
prototype/output/validation_plan_proposal.json
```

Pipeline собирает их в agent reports.

### 4. Формальная валидация плана

Python проверяет plan proposal на соответствие architecture contract и validation rules.

После успешной проверки утвержденные artifacts записываются в workspace baseline:

```text
prototype/input/file_plan.json
prototype/input/validation_plan.json
```

### 5. OpenCode plan-review

Модель проверяет план как reviewer и пишет:

```text
prototype/output/plan_review.json
```

Review может завершиться `pass` или `warning`, если file plan безопасен и проблемы только metadata-level.

### 6. OpenCode implementation

Модель реализует только файлы из `prototype/input/file_plan.json` и пишет:

```text
prototype/output/implementation_report.json
prototype/output/change_manifest.json
```

### 7. Сбор изменений и boundary check

Python сравнивает workspace diff с утвержденным file plan и пишет:

```text
prototype/output/changed_files.json
prototype/output/workspace.diff
```

Boundary должен быть `passed`. Unexpected files, forbidden paths, missing required files или policy violations делают запуск failed или repairable failure.

### 8. UI static checks

Python проверяет anchors, указанные validation plan и generated UI files, и пишет:

```text
prototype/output/ui_static_check_result.json
```

При `--strict-ui-checks` blockers считаются repairable failure.

### 9. Validation

Python запускает validation task активного kit-а:

```bash
task validate
```

Для текущего kit-а `task validate` выполняет:

```text
install → smoke → test → build → frontend-behavior
```

Результат:

```text
prototype/output/validation_result.json
prototype/output/validation.stdout.log
prototype/output/validation.stderr.log
```

### 10. Repair

Если включен `--allow-repair`, validation/boundary/ui_static failures могут запустить OpenCode repair.

Repair читает:

```text
prototype/output/repair_context.json
prototype/output/validation_result.json
prototype/output/changed_files.json
prototype/output/ui_static_check_result.json
```

Repair пишет:

```text
prototype/output/repair_report.json
```

После repair повторяются collect changes, UI static checks и validation. Максимальное число попыток задается `--max-repair-attempts`.

### 11. Traceability

Python строит связь требований, changed files и validation checks:

```text
prototype/output/code_traceability.json
```

Успешные статусы требований:

```text
implemented_and_validated
validated_unchanged
```

### 12. Summary, scenario result и export

Pipeline пишет:

```text
runs/<run>/output/run_summary.json
runs/<run>/output/scenario_result.json
runs/<run>/output/run_report.md
runs/<run>/dist/prototype_artifact.zip
runs/<run>/dist/run_diagnostics.zip
```

## Отчеты фаз

Обязательные OpenCode phase outputs:

```text
plan:
  prototype/output/plan_proposal.json
  prototype/output/validation_plan_proposal.json

plan-review:
  prototype/output/plan_review.json

implementation:
  prototype/output/implementation_report.json
  prototype/output/change_manifest.json

repair:
  prototype/output/repair_report.json
```

Все phase reports должны быть JSON, кроме logs. Human-readable stdout не считается контрактом.

## Основные runtime-результаты

```text
runs/<run>/output/run_summary.json          полный summary pipeline
runs/<run>/output/scenario_result.json      основной итоговый контракт
runs/<run>/output/run_report.md             markdown-отчет для человека
runs/<run>/output/code_traceability.json    покрытие требований
runs/<run>/output/changed_files.json        boundary и список изменений
runs/<run>/output/ui_static_check_result.json
runs/<run>/output/validation_result.json
runs/<run>/output/agent_reports.json
runs/<run>/output/pipeline_events.jsonl
runs/<run>/output/workspace.diff
runs/<run>/dist/prototype_artifact.zip
runs/<run>/dist/run_diagnostics.zip
```

`scenario_result.json` содержит:

- `final_status`;
- `stage_status`;
- `slice`;
- `changed_files`;
- `validation`;
- `traceability`;
- `repair`;
- `artifacts`;
- `usage`;
- `inputs`.

## Правила реализации для текущего kit-а

### Границы file plan

- Любой generated source/test file должен быть в `file_plan.json`.
- Integration/skeleton files модифицируются только если разрешены contract/generation rules.
- Runtime outputs и phase reports не считаются semantic generated code.
- `dependency/package` files не меняются в обычных slices без явного плана и разрешения.

### Backend / FastAPI / JSON storage

Для feature API используется стандартный route contract:

```python
# backend/app/api/<resources>.py
router = APIRouter(prefix="/<resources>")

# backend/app/main.py
app.include_router(<resources>_router, prefix="/api")
```

Публичный путь:

```text
/api/<resources>
```

Правила:

- frontend и backend pytest используют тот же публичный путь;
- API, frontend и tests используют одинаковые имена query params;
- для query values с `+`, пробелами, `&`, `%`, `#` использовать `params={...}` в pytest и `URLSearchParams` во frontend;
- service layer поддерживает dependency injection для JSON storage;
- test storage должен использовать full temp path, не `Path(...).name`;
- provider для FastAPI dependency override должен быть импортируемым напрямую из API module;
- tests должны использовать `app.dependency_overrides[get_<resource>_service]`, а не FastAPI internals.

### Frontend / React

Текущий `frontend/src/App.jsx` рендерит первый route через `routes[0].component`. Поэтому `routeRegistry.js` должен экспортировать `component`, а не `element`.

Для screen root, widgets, forms, fields, actions и items используются `data-prototype-id` anchors.

Стандартные anchors:

```text
screen.<entity-screen>
widget.<entity-search-or-filter>
control.open-create-<entity>
form.<entity>
field.<entity>-<field>
action.create-<entity>
action.edit-<entity>
item.<entity>
```

Clear/reset handlers не должны полагаться на синхронное обновление React state. Reset должен передавать явные значения в loader:

```text
setQuery('')
setCategory('')
fetchItems({ query: '', category: '' })
```

### Browser/e2e

Browser/e2e проверяет пользовательский demo-flow, а не внутреннюю реализацию.

Правила:

- один compact Playwright spec на основной CRUD/list/search/filter flow;
- test steps внутри одного `test(...)`, а не набор независимых brittle tests;
- opener `control.open-create-*` только открывает форму;
- submit/save находится на `action.create-*` или `action.edit-*`;
- после create/edit ждать конкретную runtime-owned row/card;
- после search/filter ждать matching row/card до count assertions;
- после clear/reset проверять возврат нескольких runtime-owned rows/cards, отличающихся по сбрасываемому измерению;
- после edit использовать current/edited values в следующих assertions/search;
- значения, которые меняются между `test.step(...)`, объявлять как `let` в scope всего test-а;
- не придумывать navigation links, если kit App их не рендерит;
- если требование перечисляет несколько search/filter dimensions, UI и e2e должны демонстрировать эти dimensions.

## Samples

Текущие sample groups:

```text
samples/notes-app/
samples/notes-app-slice-002/
samples/notes-app-slice-003-confirm-delete/
samples/notes-app-slice-004-note-count/
samples/tasks-app/
samples/customers-app/
samples/products-app/
```

Типовой состав sample:

```text
requirements.json          требования
scheme_model.json          схема/архитектурные элементы из requirements/design stage
implementation_slice.json  compatibility view slice-а
run_input.json             канонический вход pipeline
mock_plan.json             описание mock data expectations
data_sources.json          описание источников и mock/storage данных
```

`customers-app` проверяет customer directory: `full_name`, `email`, `phone`, `segment`, create, edit contact data, list, search by name/email/phone, no delete.

`products-app` проверяет product catalog: `name`, `sku`, `category`, `price`, create, edit price/category, list, search by name/SKU, filter by category, no delete.

## Проверенные команды запуска

Products app:

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

Customers app:

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

## Проверка после изменений проекта

Для изменения Python pipeline:

```bash
python3 -m py_compile <changed-python-file>
python3 tools/run_pipeline.py --help
python3 tools/validate_plan.py --help
```

Для изменения sample:

```bash
python3 -m json.tool samples/<scenario>/run_input.json >/dev/null
python3 tools/prepare_run_from_scenario.py \
  --scenario samples/<scenario>/run_input.json \
  --run /tmp/<run-name> \
  --kit prototype-kits/react-python-json-browser
```

Для изменения patch archive:

```bash
unzip -t /path/to/archive.zip
```

Для проверки generated prototype внутри workspace:

```bash
cd runs/<run>/workspace
task validate
```

## Правила доработки

- Не добавлять demo-specific правила для одного sample, если проблема не сформулирована как общий kit-level pattern.
- Не превращать Python checks в replacement для LLM planning.
- Не менять generated app skeleton без отражения в kit rules/prompts/runtime manifests.
- Не отправлять diff/patch files пользователю без прямой просьбы.
- После каждого patch handoff указывать список измененных файлов.
- Для artifacts давать ссылку на zip и коротко указывать проверки.
