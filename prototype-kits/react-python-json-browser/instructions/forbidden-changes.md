# Forbidden Changes

Do not modify:
- `prototype/input/`
- `.git/`
- `node_modules/`
- package lock files unless explicitly required
- technology stack configuration unless explicitly approved

Do not add:
- authentication
- external integrations
- database migrations
- deployment configuration

## Strict file boundary

Do not create, edit, rename, or delete any file unless it is listed in `prototype/input/file_plan.json`. If `file_plan.json` is absent, stop and report that the approved file plan is missing.

Respect file policies in the active file plan:
- `must_create`: create this file.
- `may_modify` / `modify_allowed`: modify only if needed.
- `no_change` / `may_read` / `read_only`: read only; do not edit.

Do not create helper files, API client files, utility files, index files, CSS files, config files, test files, package files, or lock files unless they are explicitly listed in the active file plan.

If a helper file seems necessary but is not listed in the active file plan, do not create it. Implement the behavior using the listed owned files and listed integration files, or report the limitation in `prototype/output/implementation_report.json`.
