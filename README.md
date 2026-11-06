# Codex + Claude Code project template

A reusable starter kit for software projects using OpenAI Codex and Claude Code. It contains
shared agent skills, harness-specific agent definitions and hooks, optional OpenSpec commands,
development workflow templates, and local checks for keeping the two configurations aligned.

## Adopt this template

1. Copy the repository into a new project.
2. Rename `AGENTS.template.md` to `AGENTS.md` and `CLAUDE.template.md` to `CLAUDE.md`. Fill in the
   project context, stack, commands, and repository structure in `AGENTS.md`; keep shared rules
   there and Claude-specific guidance in `CLAUDE.md`.
3. Copy `.claude/settings.template.json` to `.claude/settings.json`, then adjust permissions and
   local commands. Review `.codex/hooks.template.json` alongside `.codex/hooks.json` and keep them
   aligned if the active hooks change. In Codex, trust the project hooks and review them with
   `/hooks` before relying on them.
4. Copy `docs/guides/TESTING.template.md` to `docs/guides/TESTING.md` and, if adopting OpenSpec,
   `docs/guides/OPENSPEC.template.md` to `docs/guides/OPENSPEC.md`; tailor each guide.
5. Keep skills in `skills/` and their symlinks in `.claude/skills/` and `.agents/skills/`.
6. Remove workflows, agents, hooks, or skills that the project will not use. Replace every
   `<placeholder>` before relying on a template.

## Layout

- `.claude/` — Claude Code settings, commands, agents, and skill links.
- `.codex/` — Codex hooks, agents, and OpenSpec skills.
- `.agents/skills/` — Codex discovery links to the shared skill source.
- `skills/` — shared skills and third-party notices.
- `docs/` — optional workflows, prompt starters, and project guide templates.
- `scripts/` — hook implementations and consistency checks.
- `openspec/` — OpenSpec configuration template and workspace directories.

## Local checks

Run the relevant script directly when changing the toolkit:

```bash
scripts/bash/check_skill_symlinks.sh
scripts/bash/check_hook_parity.sh
scripts/bash/check_agent_parity.sh
```

This repository is a template, not an example application; add the target project's source code,
tests, dependency files, CI configuration, and deployment setup when adopting it.
