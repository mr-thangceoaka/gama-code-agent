# Setup on macOS

How to run the GAMA Code Agent on macOS (Intel or Apple Silicon).

## 1. Prerequisites

### Python
macOS ships a Python, but grab a clean **3.11/3.12** anyway, from
[python.org](https://www.python.org/downloads/macos/) or Homebrew:

```bash
brew install python@3.12
python3.12 --version
```

### Node.js
Install **Node.js >= 20 LTS** (the SDK bundles the Claude Code CLI):

```bash
brew install node
node --version
```

### GAMA
Install **GAMA** from [gama-platform.org](https://gama-platform.org/download).
It goes into `/Applications/Gama.app`.

Find the launcher (path shifts between versions):

```bash
find /Applications/Gama.app -name "gama-headless.sh"
```

Usually:
```
/Applications/Gama.app/Contents/headless/gama-headless.sh
```

The folder that holds that script (`.../headless`) is your `GAMA_HEADLESS_DIR`.

> If Gatekeeper blocked GAMA on first launch, open it once with right-click ->
> Open, or run:
> `xattr -dr com.apple.quarantine /Applications/Gama.app`

## 2. Get the code

```bash
git clone <your-repo-url> gama-code-agent
cd gama-code-agent
```

## 3. Virtual env + install

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

Fill in `.env`:

```ini
ANTHROPIC_API_KEY=sk-ant-...
GAMA_HEADLESS_DIR=/Applications/Gama.app/Contents/headless
```

Use the exact path the `find` above returned (the folder with
`gama-headless.sh`).

## 5. Put your model under git (recommended)

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

It prints its reasoning, `[tool call: ...]` markers, and a final report.

## Troubleshooting

**`Cannot find gama-headless.sh in GAMA_HEADLESS_DIR`**
Re-run the `find` command and set `GAMA_HEADLESS_DIR` to the folder that actually
holds the script.

**`Permission denied` running the script**
The agent runs it via `bash`, so this is usually a path issue, not a chmod one.
You can still `chmod +x .../gama-headless.sh` if needed.

**GAMA won't start / Gatekeeper warning**
`xattr -dr com.apple.quarantine /Applications/Gama.app`, then launch GAMA once by
hand.

**Validate says PASS even for broken models**
Make sure you're on this version. It uses `-xml`, not `-validate` (which ignores
your file).

**`ANTHROPIC_API_KEY` not found**
Check `.env` sits in the repo root and the key has no quotes or spaces.
