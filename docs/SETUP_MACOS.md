# Setup on macOS

Step-by-step guide to run the GAMA Code Agent on macOS (Intel or Apple Silicon).

## 1. Prerequisites

### Python
macOS ships with Python, but install a fresh **Python 3.11/3.12** to keep things
clean — via [python.org](https://www.python.org/downloads/macos/) or Homebrew:

```bash
brew install python@3.12
python3.12 --version
```

### Node.js
Install **Node.js ≥ 20 LTS** (the Claude Agent SDK bundles the Claude Code CLI):

```bash
brew install node
node --version
```

### GAMA
Install **GAMA** from [gama-platform.org](https://gama-platform.org/download).
It installs as an app bundle in `/Applications/Gama.app`.

Find the headless launcher (path can vary by version):

```bash
find /Applications/Gama.app -name "gama-headless.sh"
```

Typical result:
```
/Applications/Gama.app/Contents/headless/gama-headless.sh
```

The folder **containing** that script (`.../headless`) is your
`GAMA_HEADLESS_DIR`.

> If macOS Gatekeeper blocked GAMA on first launch, open it once via
> **right-click → Open**, or run:
> `xattr -dr com.apple.quarantine /Applications/Gama.app`

## 2. Get the code

```bash
git clone <your-repo-url> gama-code-agent
cd gama-code-agent
```

## 3. Create a virtual environment & install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```ini
ANTHROPIC_API_KEY=sk-ant-...
GAMA_HEADLESS_DIR=/Applications/Gama.app/Contents/headless
```

> Point it at the folder that contains `gama-headless.sh` (use the exact path
> the `find` command above returned).

## 5. (Recommended) Put your model under git

```bash
cd /path/to/your/gama/project
git init
git add -A
git commit -m "before agent review"
```

## 6. Run

```bash
cd /path/to/gama-code-agent
source .venv/bin/activate
python agent.py /path/to/your/model.gaml
```

The agent prints its reasoning, `[tool call: ...]` markers, and a final report.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot find gama-headless.sh in GAMA_HEADLESS_DIR` | Re-run the `find` command; set `GAMA_HEADLESS_DIR` to the folder that actually contains the script. |
| `Permission denied` running the script | The agent invokes it via `bash`, so this is usually a path issue, not a chmod one. You can also `chmod +x .../gama-headless.sh`. |
| GAMA won't start / Gatekeeper warning | `xattr -dr com.apple.quarantine /Applications/Gama.app`, then launch GAMA once manually. |
| Validate always says PASS even for broken models | Make sure you're on this version — it uses `-xml`, not `-validate` (which ignores your file). |
| `ANTHROPIC_API_KEY` not found | Check `.env` exists in the repo root and the key has no quotes/spaces. |
