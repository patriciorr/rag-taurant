## Agent skills

### Issue tracker

Issues live in GitHub Issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical triage roles map directly to same-named labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Test validation

- Always run the complete relevant test suite, including tests marked `integration`; never exclude them solely because they require an external service.
- If an integration test cannot run because a dependency or service is unavailable, report the exact blocker and distinguish that from a passing test.
