# GAMA Code Agent

A local AI agent, powered by **Claude** (via the [Claude Agent SDK](https://docs.anthropic.com/en/api/agent-sdk/overview)),
that reviews, compile-checks, and auto-fixes [GAMA](https://gama-platform.org/)
**GAML** models. Built for people who write GAMA agent-based simulations.

It runs on your machine and talks to your own GAMA install in headless mode, so
your models stay local. Only the code the agent reads goes to the Claude API for
reasoning.

## Demo

![Example review session](docs/demo.svg)

*Illustrative example of the report format. The findings shown (a real
degrees-vs-radians `sin()` unit bug in a Binary-Logit traffic model) come from an
actual review run.*

## What it does

Point it at a `.gaml` file and it runs a fixed 4-step review
(defined in [`.claude/skills/gama-code-reviewer/SKILL.md`](.claude/skills/gama-code-reviewer/SKILL.md)):

1. **Compile-check** the model with GAMA headless. No full simulation.
2. **Read the code** against a checklist of common GAML/ABM mistakes: `sin`/`cos`
   unit bugs, geometry/CRS errors, financial-formula unit errors, parameter
   drift between scenarios, instantaneous-vs-rolling-average charts, runtime
   safety, and abstract-vs-code mismatches.
3. **Run** the main experiment in batch mode to catch runtime errors.
4. **Fix or propose.** Syntax errors it auto-fixes and re-validates (up to 5
   tries). Logic/data errors it only PROPOSES, because there's no mechanical way
   to know a logic fix is scientifically right, and a blind edit can produce
   results that look fine but aren't.

You get a structured report at the end, same shape every run so you can compare.

## Safety

The agent can edit files, so the guardrails live in code (`agent.py`, in a
`can_use_tool` callback), not just in the prompt:

- Bash is restricted to `git` only. Every other shell command is blocked.
- Write/Edit can only touch the folder of the `.gaml` you pass in. Nothing else.
- `permission_mode="default"`, so there's no "approve everything" mode.
- Syntax fixes are automatic; logic fixes are proposal-only.
- `max_turns=40` stops runaway loops.

Keep your GAML project under git and commit before running, so you can
`git diff` / `git checkout` anything the agent changed.

## Requirements

- Python >= 3.10 (standard CPython, see the OS guides for why MSYS/mingw Python
  won't work on Windows)
- Node.js >= 20 (the SDK bundles the Claude Code CLI)
- A GAMA install with the `headless` launcher
- An `ANTHROPIC_API_KEY` ([get one](https://console.anthropic.com/))

## Quickstart

Full per-OS steps: [Windows](docs/SETUP_WINDOWS.md) · [macOS](docs/SETUP_MACOS.md).

Short version:

```bash
# 1. install
python -m venv .venv
#    Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. configure: copy .env.example -> .env and fill both values
#    ANTHROPIC_API_KEY=sk-ant-...
#    GAMA_HEADLESS_DIR=<your GAMA .../headless folder>

# 3. run
python agent.py path/to/your/model.gaml
```

## Project structure

```
gama-code-agent/
├── agent.py                  # entry point: orchestration + guardrails
├── tools/
│   └── gama_tools.py         # MCP tools wrapping gama-headless (cross-platform)
├── .claude/
│   └── skills/
│       └── gama-code-reviewer/
│           └── SKILL.md      # the review process + checklist (edit to customize)
├── docs/
│   ├── SETUP_WINDOWS.md
│   └── SETUP_MACOS.md
├── requirements.txt
├── .env.example
└── LICENSE
```

## How it works

- The two GAMA tools are exposed to Claude as an in-process MCP server
  (`create_sdk_mcp_server`), so there's no extra process or port.
- Compile-checking uses `gama-headless -xml`, not `-validate`. `-validate` only
  checks GAMA's built-in library and ignores your file; `-xml` forces GAMA to
  compile your model (exit 0 + XML written = PASS).
- On Windows, `gama-headless.bat` needs an absolute path and cwd on the
  `headless` folder, or it reports "not recognized". On macOS/Linux the `.sh`
  runs via `bash`.
- The skill loads through `setting_sources=["project"]`, which reads
  `.claude/skills/`. That's why it lives under `.claude/`.

## Customizing

Edit [`.claude/skills/gama-code-reviewer/SKILL.md`](.claude/skills/gama-code-reviewer/SKILL.md)
to fit the models and bugs you deal with. No need to touch the Python, the agent
re-reads the skill every run.

## License

MIT, see [LICENSE](LICENSE).
