---
name: gama-code-reviewer
description: Review and validate GAML/GAMA models (agent-based simulations of any domain — traffic, epidemiology, economics, ecology, etc.) before submitting them or before using them as the basis for results in a paper. Use this skill whenever there is a .gaml file to check for compilation errors, logic errors, or to cross-check the code against an abstract/model description. Especially useful for reviewing student/capstone projects built with GAMA, or before re-running batches of scenarios for research.
---

# GAMA Code Reviewer

This skill defines a 4-step process for automatically checking a GAML model:
run a compile-check, run it, compare the code against a checklist of common
errors, and report with concrete line citations.

## Process

### Step 1 — Compile-check (fast, no full simulation)
Call `validate_gaml_syntax(gaml_path, experiment_name)` with the path to the
`.gaml` file and the name of one experiment defined in the model (read the file
first to find one). The tool uses `gama-headless -xml`, which forces GAMA to
compile the model without running a full simulation. If the result is FAIL,
stop and report immediately — no need to continue.

Note: GAMA headless only reports *that* compilation failed, not the exact line,
so on FAIL you should `Read` the `.gaml` file to locate the error yourself.

### Step 2 — Read the code and compare against the checklist (see below)
Read the whole relevant `.gaml` file with `Read`. For each checklist item,
record: violated or not, line number, and the relevant code snippet.

### Step 3 — Run it (batch mode) if Steps 1–2 found no serious errors
Call `run_gama_headless` with the model's main experiment. Watch stderr for
runtime errors (division by zero, empty agent lists, index out of bounds in
networks/graphs).

### Step 4 — Auto-fix (syntax only) or propose fixes (logic)

Treat the two error classes differently:

**Syntax errors (compile errors from Step 1) — SAFE to auto-fix and loop:**
1. Read the error message (file, line, type).
2. Use `Edit` to fix it directly.
3. Re-run `validate_gaml_syntax`.
4. Loop at most `max_iterations = 5` times. If it still fails after 5, stop and
   report to the user instead of guessing further.
5. Before the first edit, make a backup (e.g. commit with git, or copy the file)
   so the change can be reverted.

**Logic/data errors (found in Step 2 — checklist) — do NOT auto-fix.** Only:
1. State the location and why it violates the checklist.
2. Propose a fix (e.g. "the formula on line 142 mixes units; likely missing a
   conversion factor").
3. Stop and wait for the user before touching the file.

Rationale: syntax errors have an objective pass/fail criterion (does it compile),
so auto-looping is safe. Logic errors (revenue formulas, geometry, coefficients)
have no mechanical criterion for "fixed correctly" — the agent can only make the
code *run*, not guarantee it is scientifically right. Blind looping on those can
produce results that look fine but are wrong.

### Step 5 — Report
Always output the report in the "Report format" below — no free-form prose — so
reviews are comparable across runs.

## Checklist of common errors

Generic checklist for GAMA/ABM models. Extend it when you find a new error type.

1. **Abstract/description does not match the code** — Read the model description
   (header comment, or an accompanying README/abstract) and compare it against
   the actual logic in the `global` section. Classic example: the abstract says
   "model with X agents" but the code creates a different agent type, or
   describes a decision mechanism that does not exist in the code.

2. **`sin()` / `cos()` unit bug (degrees vs radians)** — GAML trigonometric
   functions take arguments in **degrees**, not radians. A very common bug is
   writing `sin(t * #pi)` (radian thinking), which makes periodic terms
   oscillate ~57x too slowly (period blown up by 180/π). If a model uses sin/cos
   for time-varying demand/congestion/seasonality, check the units — to get a
   period of P steps use `sin(cycle / P * 360)`.

3. **Geometry / coordinate errors** — Check `point`, `geometry`, and `graph`
   definitions. Common problems: the endpoints of a route don't match the nodes
   in the network graph (agents get "stuck" or route length is wrong), or mixed
   coordinate units (degrees vs metres, different EPSG/CRS).

4. **Financial / economic formula errors (revenue, toll, cost)** — For
   BOT/PPP or economic models, check currency units (e.g. VND vs thousand-VND),
   whether values are correctly multiplied by traffic volume per time step, and
   whether summing over steps double-counts.

5. **Parameter consistency across experiments/scenarios** — If the model has
   several `experiment`s (e.g. to run different scenarios), check that shared
   parameters (value-of-time, α, β, capacity, ...) are set consistently and no
   experiment forgets to override a default.

6. **Instantaneous vs rolling-average charts** — If the model draws time series
   of flow/counts, check whether it uses a proper rolling average / ring buffer.
   Plotting instantaneous values where an average is intended produces "blocky",
   jumpy charts.

7. **Runtime-safety patterns** — Division guarded against zero, list/graph index
   access guarded against out-of-bounds, `do die` ordering vs. subsequent
   attribute access, agent lists that may be empty before `first`/`one_of`.

> When reviewing a new model, if you find an error type not listed above, add a
> new item to this checklist (edit this SKILL.md) so future reviews catch it.

## Report format

```
## Review result: <file/model name>

### 1. Compile-check
[PASS / FAIL] — <details if FAIL>

### 2. Checklist
| # | Item | Result | Line | Note |
|---|------|--------|------|------|
| 1 | Abstract vs code        | OK / VIOLATION | ... | ... |
| 2 | sin/cos units           | OK / VIOLATION | ... | ... |
| 3 | Geometry/coordinates    | OK / VIOLATION | ... | ... |
| 4 | Financial formulas      | OK / VIOLATION | ... | ... |
| 5 | Parameter consistency   | OK / VIOLATION | ... | ... |
| 6 | Rolling-average charts  | OK / VIOLATION | ... | ... |
| 7 | Runtime safety          | OK / VIOLATION | ... | ... |

### 3. Auto-fix (if any)
- Syntax errors auto-fixed: <list, #iterations, where is the backup>
- Logic errors needing review: <list of proposals, not yet applied>

### 4. Test run
[PASS / FAIL / SKIPPED] — <runtime error log if any>

### 5. Conclusion
<1-2 sentences: is the model ready to be used as an official result?>
```

## Tools (defined elsewhere; the agent only calls them)

- `validate_gaml_syntax(gaml_path: str, experiment_name: str)` — compile-check a
  model via `gama-headless -xml`
- `run_gama_headless(gaml_path: str, experiment_name: str, verbose: bool)` — run
  batch mode
- `Read`, `Grep` — built-in Claude Agent SDK tools for reading/searching code
