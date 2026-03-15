# AGENTS.md

This file defines repository-level working rules for AI coding agents used in this project, including Claude Code, Codex, and similar tools.

## Scope

- This file applies to the entire repository.
- If a tool supports repository instructions, it should treat this file as the primary collaboration guide.
- If `CLAUDE.md`, `README.md`, or other docs also exist, prefer this file when instructions overlap.

## Collaboration Priority

When making changes, follow this priority order:

1. User's current request
2. This `AGENTS.md`
3. Existing code and tests
4. Secondary docs such as `README.md`, `docs/`, or tool-specific notes

If two sources conflict, do not guess silently. Keep the change minimal and align with the most local, most explicit rule.

## Change Boundaries

- Do not refactor unrelated files while solving a focused task.
- Do not rename fields, methods, or files unless the task requires it.
- Do not mix business-logic changes, prompt rewrites, and broad cleanup in one pass.
- Prefer small, isolated edits that are easy to review and revert.

## Source Of Truth

For contact collection logic, use the following hierarchy:

1. Business rules documented in `docs/contact_collection.md`
2. Core decision logic in `src/services/contact_collection_service.py`
3. State fields in `src/models/user_profile.py`
4. Tests in `tests/`

Do not introduce a second state machine for contact collection in another file unless explicitly requested.

## Contact Collection Rules

When working on phone/wechat collection:

- Treat `ContactCollectionService` as the core decision layer.
- Treat `UserProfile` as the state carrier, not the place for duplicated business branching.
- Keep phone and wechat ask-count limits consistent with current business rules.
- Keep Hong Kong and non-Hong Kong handling explicit and testable.
- If changing contact collection behavior, update tests in the same task.

Relevant files:

- `src/services/contact_collection_service.py`
- `src/models/user_profile.py`
- `tests/test_contact_collection_service.py`
- `tests/test_contact_collection_scenarios.py`
- `tests/integration/test_contact_collection_integration.py`
- `docs/contact_collection.md`

## Testing Rules

- Before changing contact collection logic, read the relevant service and test files first.
- After changing contact collection logic, run the related tests if the environment allows it.
- Prefer assertions on action, state, and branching outcome over brittle assertions on exact AI wording.
- If a test checks prompt text, keep it limited to intent-level keywords unless exact wording is the requirement.

Recommended test layers:

- `tests/test_contact_collection_service.py`: core unit tests for branching and limits
- `tests/test_contact_collection_scenarios.py`: scenario regression tests
- `tests/integration/test_contact_collection_integration.py`: end-to-end or AI-linked behavior checks

## Prompt And AI Response Changes

- Do not casually rewrite prompt templates when fixing pure logic bugs.
- Do not change prompt tone and business behavior in the same edit unless required.
- If modifying prompt templates, preserve the intended action:
  - ask phone
  - persuade phone
  - ask wechat
  - persuade wechat
  - end conversation
  - continue collecting other fields

## Safe Working Style

- Prefer minimal diffs.
- Preserve existing public interfaces unless the task requires a change.
- Do not remove existing tests unless they are clearly obsolete and replaced in the same task.
- Do not "clean up" failing tests by weakening business coverage without explaining why.

## Notes For Multi-Agent Use

- Claude Code and Codex should both follow this file.
- If one agent has already modified a file for the current task, the next agent should read that file before editing it again.
- Avoid parallel edits to the same business-logic files by different agents.
- If the repository is in a partially changed state, do not overwrite unrelated user changes.

## Preferred Task Flow

For non-trivial changes in this repository:

1. Read the relevant service, model, and tests
2. Identify the smallest correct change
3. Edit only the necessary files
4. Run focused tests
5. Update the relevant documentation when user-visible behavior, prompt behavior, test workflow, or entry behavior changes
6. Report what changed, what was verified, and any remaining gaps

## Documentation Sync Rule

- Do not rely on memory alone to keep docs in sync with code.
- If a change affects user-visible behavior, prompt rules, business branching, test workflow, or entry behavior, update the relevant `docs/*.md` files in the same task by default.
- If no existing document is a good fit, add a short new markdown note instead of leaving the behavior undocumented.
- If the code change is purely internal and does not affect observable behavior, a doc update is optional.
- When reporting completion, mention which docs were updated, or explicitly state that no doc update was needed.

## What Not To Do

- Do not invent undocumented business rules.
- Do not spread contact collection branching across controllers, prompts, and models without a clear reason.
- Do not rely only on manual reasoning when targeted automated tests already exist.
- Do not treat prompt text as the only source of business truth.
