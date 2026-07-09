# Pipeline phase output rules

Use these rules for OpenCode phases in this pipeline.

- The durable outputs of a phase are the JSON files explicitly required by that phase prompt. Stdout summaries are not pipeline artifacts.
- The approved file plan, `implementation_report.json`, `change_manifest.json`, and `repair_report.json` are the structured progress and change records.
- Keep report files concise, valid JSON, and directly tied to the current slice.
- If a required report cannot be written because of a real blocker, write the closest valid report with the blocker recorded instead of ending with only a text explanation.
- Optional self-check commands run by the agent are diagnostics only. The pipeline's own boundary, ui_static, and validation phases remain the source of truth.
- Official validation is staged by the pipeline: install, smoke, backend pytest, frontend build, and browser/e2e are collected in one validation_result so repair can see all currently known failures. Staged output also marks downstream failures whose diagnostics may depend on an earlier failed stage; repair should prioritize root failed stages first.
- Do not run the full pipeline validation script (`tools/run_validation.py`) from OpenCode phases. It duplicates the pipeline, can be slow, and can confuse repair with partially restored or mutated workspaces. Use the validation logs already provided to repair prompts; use only focused diagnostics when they directly verify a small repair.
- Avoid ad-hoc diagnostics that are known to be incompatible with the kit, such as raw `node --check` on JSX files or Playwright ESM specs.
