# AGENTS.md

Краткий технический контекст для агента или другого чата, который будет дорабатывать проект `codegenerator2`.

## Назначение

`codegenerator2` — стенд для управляемой генерации прототипов приложений через OpenCode/LLM-агентов. Агент работает не свободно со всем репозиторием, а внутри контролируемого pipeline:

```text
run_input.json
→ OpenCode plan
→ formal plan validation
→ OpenCode plan-review
→ OpenCode implementation
→ boundary / UI static / validation / traceability
→ scenario_result.json
```

Главный контракт:

```text
samples/<scenario>/run_input.json → runs/<run>/output/scenario_result.json
```

`run_input.json` — канонический вход от requirements stage. `scenario_result.json` — основной отчетный контракт для будущего UI/отчета.

## Основная архитектурная идея

Цель проекта — генерировать код не как свободный diff, а как реализацию требований в рамках архитектурного шаблона. Шаблон разделяет уровни приложения: UI screens/widgets/actions, backend API, backend services, data models, storage/mock data, validation tests и существующие integration/skeleton files.

Модель должна:

- прочитать требования и architecture kit;
- составить план реализации по правилам kit-а;
- сама проверить план по этим правилам перед записью JSON;
- реализовать только утвержденный план;
- исправлять ошибки реализации только внутри разрешенных файлов.

Python-код не должен становиться вторым архитектурным planner-ом. Он организует pipeline, передает контекст модели, проверяет технические границы и собирает результаты.

## Где живут правила

Главные правила разработки и архитектуры лежат в активном kit-е:

```text
prototype-kits/react-python-json-browser/
  architecture-contract.yaml      machine-readable contract: artifact types, roots, operations, validation capabilities
  generation-rules.yaml           naming and scheme-to-file mapping
  instructions/architecture.md    human-readable layer rules and skeleton/integration rules
  instructions/planning-rules.md  planner checklist and output rules
  instructions/coding-rules.md    implementation coding rules
  instructions/validation-rules.md validation and UI anchor rules
  prompts/                        phase prompts that reference these rules
  examples/                       small examples, not ready-made project code
  template/                       minimal skeleton workspace
```

`architecture-contract.yaml` и `generation-rules.yaml` — не место для бизнес-логики. Они описывают архитектурные уровни, допустимые корни, операции и naming. Предметные решения должны приходить из требований и плана модели.

В workspace канонический путь для markdown-инструкций — `instructions/...`. Pipeline также может материализовать read-only compatibility mirror этих инструкций под `prototype/input/instructions/...`, чтобы старые или упрямые agent traces не давали шумные failed reads. Этот mirror является baseline metadata, а не generated output.

## Роль Python-кода

Python pipeline отвечает за:

- подготовку workspace и синхронизацию kit context;
- запуск OpenCode phases;
- проверку наличия и формата обязательных JSON outputs;
- минимальные machine-readable safety checks: безопасные относительные пути, forbidden paths, allowed roots, dependency boundary;
- сбор git diff и сравнение с утвержденным `file_plan.json`;
- статические проверки результата кода, например `data-prototype-id` anchors;
- запуск `task validate`;
- traceability, reports, diagnostics, usage logs.

Python pipeline не должен:

- придумывать имена новых feature-файлов или тестов;
- исправлять `artifact_type`, если модель выбрала неверный архитектурный слой;
- превращать `create` в `modify` по содержательному смыслу плана;
- добавлять скрытые архитектурные исключения под конкретный ответ модели;
- переносить правила разработки из kit-а в Python-код.

Допустимая нормализация Python — только техническая: canonical paths, default для необязательного поля, сортировка/запись JSON, совместимость старого имени поля с новым. Содержательные решения остаются на стороне модели и правил kit-а.

## Активный kit

Используется один kit:

```text
prototype-kits/react-python-json-browser/
```

Это React + Python/FastAPI-compatible + JSON mock storage kit с browser/e2e validation через Playwright. Отдельный lightweight kit сейчас не поддерживается, чтобы не держать две расходящиеся копии правил и prompt-ов.

## Проверенный запуск после clone

Запускать нужно с greenfield baseline, а не сразу с инкрементального slice.

Порядок:

```text
SLICE-001 basic notes app
→ SLICE-003 confirm delete
→ SLICE-004 note count summary
```

Baseline:

```bash
cd ~/opencode/codegenerator2

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

Инкрементальные slice запускать только от successful baseline через `--from-run`.

## Основные директории

```text
architecture-profiles/       Общие архитектурные профили.
prototype-kits/              Активный kit, template, prompts, validation contracts.
prototype_pipeline/          Python package основного pipeline.
tools/                       CLI entrypoints и вспомогательные tools.
samples/                     Входные сценарии и примеры slice.
runs/                        Runtime-директории запусков; в git хранится только .gitkeep.
```

## Роли этапов

- `prepare_run_from_scenario.py` — Python, готовит workspace из sample и optional previous run.
- `plan` — OpenCode, пишет `plan_proposal.json` и `validation_plan_proposal.json`.
- `validate_plan.py` — Python, проверяет формат и machine-readable safety boundary; не чинит архитектурный смысл плана. При успехе пишет `file_plan.json`, `validation_plan.json`.
- `plan-review` — OpenCode, пишет `plan_review.json`.
- `implementation` — OpenCode, меняет только файлы из `file_plan.json`.
- `collect_changes.py` — Python, проверяет git diff против `file_plan.json`.
- `run_ui_static_checks.py` — Python, проверяет `data-prototype-id` anchors по прямым `scheme_elements` каждого измененного UI-файла из `file_plan.json`. Checker должен собирать все blockers за один проход и считать стабильными только literal anchors: прямые JSX attributes или простые JSX literal alternatives, например `editing ? 'action.edit-note' : 'action.create-note'`.
- `run_validation.py` — thin Python CLI wrapper for validation; staged execution, reporting, and workspace restore live under `tools/validation_runner/`.
- `repair` — OpenCode, только при repairable failure и `--allow-repair`.
- `build_code_traceability.py` — Python, строит traceability.
- `scenario_result.py` — Python, собирает отчетный контракт.

OpenCode может запускать отдельные диагностические команды во время implementation/repair, но официальный validation status задает только pipeline stage `Run validation`. Диагностика должна быть неинтерактивной: не использовать Playwright `--debug`, `--ui`, `codegen`, `show-trace` или headed mode.

Во время repair не запускать повторные широкие diagnostic loops. Runner может остановить фазу, если агент многократно запускает дорогие команды вроде `npm run test:e2e`, `playwright test` или широкие `pytest`-циклы. Если workspace уже изменён, это controlled handoff: pipeline выполнит collect_changes, UI static и validation, а не потеряет попытку как простую ошибку. Делайте точечную правку по уже собранным логам и доверяйте post-repair validation.

Если после implementation упали boundary или UI static checks, pipeline перед repair всё равно запускает staged validation как диагностический сбор. Repair должен видеть все уже наблюдаемые failures, а не чинить только первый слой ошибок. При `--allow-repair` pipeline по умолчанию допускает две repair-попытки (`--max-repair-attempts=2`): первая может устранить root backend/test failure, вторая — независимые ошибки, которые остались после повторной validation.

Перед каждой repair-попыткой pipeline пишет `prototype/output/repair_context.json`. Агент должен читать его как компактный вход: там есть root/downstream failures, boundary/ui_static blockers, хвосты validation logs, relevant paths и краткая история предыдущих repair. Диагностика должна помогать получить рабочий код в рамках правил, а не только объяснить, почему текущий код не работает.

`tools/run_opencode_phase.py` дополнительно выставляет неинтерактивные env-переменные и добавляет workspace-local shim для `npm`/`npx`/`playwright`, чтобы блокировать интерактивные Playwright режимы. Не переносить эту защиту в generated code и не считать shim частью prototype output.

## Правила доработки

- Не возвращать legacy `expected_files.json` / `traceability_plan.json`.
- Не добавлять business logic, имена файлов, имена тестов или предметные правила в Python pipeline.
- Python pipeline проверяет контракты и границы; функциональное решение предлагает агент.
- Dependency/package changes допустимы только через явный file plan, контрактно разрешённый package/config file и краткое обоснование. Не добавлять зависимости скрыто из implementation/repair.
- `runs/` — runtime output. Не коммитить run-директории, логи, usage, dist, workspace.
- `samples/` — коммитить только компактные входные сценарии.
- `prototype-kits/*/template/` — не коммитить `node_modules`, build outputs, Playwright reports.
- Документация проекта ведется на русском языке и должна оставаться связной, без накопления мелких version notes.
- После патчей указывать измененные файлы, новые файлы, удаленные файлы и команды проверки.

## Phase reports

Для передачи результата между фазами использовать только файлы, требуемые prompt-ами: `plan_proposal.json`, `validation_plan_proposal.json`, `plan_review.json`, `implementation_report.json`, `change_manifest.json`, `repair_report.json`. Stdout-сводки не заменяют обязательные report files.

## Типовые причины repair

Repair пока часто чинит не архитектуру, а тестовый harness и согласование тестов с реализацией: API prefix/routes, изоляцию JSON mock storage, Playwright selectors, runtime-unique e2e data и неверные ожидания тестов. Повторяющиеся случаи лучше переводить в kit instructions/examples, а не в новые Python-checker blockers.

Если repair внёс изменения, но агент не записал `repair_report.json`, pipeline может создать fallback-отчёт и всё равно выполнить post-repair проверки. Если repair внёс изменения, failed diagnostic tool calls также могут быть оставлены как warnings, чтобы post-repair boundary/validation стали источником истины. Такой fallback нужен только для устойчивости pipeline; содержательная оценка идёт по изменениям и результатам validation.

## Проверка после изменений

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

## Следующий функциональный шаг

После стабилизации sequence `SLICE-001 → SLICE-003 → SLICE-004` следующий шаг — accepted baseline / promotion flow:

```text
successful run → accepted current prototype state → next slice uses it automatically
```

### Self-check command discipline

Agent-run commands are diagnostics only; pipeline validation remains the source of truth. Do not use raw `node --check` on `.jsx` files or Playwright ESM specs. Do not change package files just to satisfy such ad-hoc checks. Browser tests should exercise the UI/public API instead of reading backend mock-storage files directly.


## OpenCode self-check limits

- Do not run full pipeline validation from OpenCode phases. The pipeline owns boundary, ui_static, and validation. Repair should use provided validation logs and only narrow diagnostics when they directly verify a small change.
- Do not patch implementation source files from tests to simulate configuration. Prefer injection or dependency replacement patterns that keep generated tests isolated without mutating source files.


## Staged validation

`tools/run_validation.py` owns canonical validation. For the `validate` task it runs install, smoke, backend pytest, frontend build, and browser/e2e as separate stages, records `stages` / `failed_stages` in `validation_result.json`, and restores semantic workspace files between stages so runtime JSON mock-data mutations and accidentally created semantic files do not contaminate later checks. It also marks downstream failures with `blocked_by_failed_stages`, `root_failed_stages`, and `downstream_failed_stages`; repair should prioritize root failed stages first and treat downstream browser/e2e failures as context while upstream backend/build failures remain unresolved. OpenCode repair should read all failed stages but should not call `tools/run_validation.py` itself.

## Kit implementation patterns

For recurring implementation shapes, prefer kit-level patterns over adding more prompt rules. The react-python-json-browser kit provides `instructions/implementation-patterns.md` as an index from artifact types to focused patterns, for example FastAPI JSON CRUD and React browser CRUD/list/search flows. Patterns are guidance only: they do not override `file_plan.json` and do not grant permission to create extra files.



## Контроль покрытия требований

Валидация плана проверяет покрытие первичных требований. Каждый id из `implementation_slice.requirements` должен быть связан хотя бы с одним planned implementation file и хотя бы с одной validation check. Это не даёт получить зелёный запуск, в котором одно из требований молча исчезло из traceability. Coverage может быть прямым или выводиться из `scheme_model` и `screen_internal` ownership: если screen file владеет action через `design_delta.owning_artifact`, этот file покрывает requirement action-а.

### Browser/e2e scope

Keep browser/e2e validation lean. For one coherent CRUD/list/search screen, prefer one compact Playwright spec linked to multiple requirements over many independent specs. Put edge cases and most negative cases in backend pytest unless the requirement is specifically about browser UI behavior. For create/edit UIs, avoid ambiguous Playwright selectors: distinguish the opener from the submitter, put scheme action anchors on the control that performs the action, and scope submit button locators inside the form.
