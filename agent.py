"""
GAMA Code Agent - entry point.

Run: python agent.py path/to/model.gaml

Flow: validate syntax -> read code against the checklist (in
.claude/skills/gama-code-reviewer/SKILL.md) -> auto-fix syntax errors if any
(loop up to MAX_SYNTAX_FIX_ITERATIONS) -> optionally run it -> report.

SAFETY: the agent can edit files, so keep your GAML project under git and commit
before running (then `git diff` / `git checkout` if you don't like a change).
can_use_tool below is the hard guardrail, not the prompt: Bash is git-only, and
Write/Edit can only touch the folder of the model you pass in.
"""

import asyncio
import os
import sys

# Load .env (ANTHROPIC_API_KEY, GAMA_HEADLESS_DIR) BEFORE importing tools, since
# gama_tools reads GAMA_HEADLESS_DIR at import time.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # dotenv is optional, you can just export the vars instead

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from tools.gama_tools import gama_tools_server

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_SYNTAX_FIX_ITERATIONS = 5


def make_can_use_tool(allowed_edit_root: str):
    # Permission callback: only let the agent edit inside the model's folder.
    async def can_use_tool(tool_name, input_data, context):
        # our own validate/run tools -> always fine
        if tool_name.startswith("mcp__gama-tools__"):
            return PermissionResultAllow()

        # Bash: git only (commit/diff/backup), block the rest
        if tool_name == "Bash":
            command = input_data.get("command", "")
            if command.strip().startswith("git ") or command.strip() == "git":
                return PermissionResultAllow()
            return PermissionResultDeny(message="Only `git` commands are allowed via Bash.")

        # Write/Edit: stay inside the model's directory, nothing outside
        if tool_name in ("Write", "Edit"):
            file_path = os.path.abspath(input_data.get("file_path", ""))
            if os.path.commonpath([file_path, allowed_edit_root]) == allowed_edit_root:
                return PermissionResultAllow()
            return PermissionResultDeny(
                message=f"Refusing to edit files outside the model directory: {allowed_edit_root}"
            )

        # reading is always safe
        if tool_name in ("Read", "Glob", "Grep"):
            return PermissionResultAllow()

        return PermissionResultDeny(message=f"Tool '{tool_name}' is not in the allow-list.")

    return can_use_tool


async def review_model(gaml_path: str):
    gaml_path = os.path.abspath(gaml_path)
    allowed_edit_root = os.path.dirname(gaml_path)  # the agent may only edit here

    options = ClaudeAgentOptions(
        cwd=PROJECT_ROOT,  # so the .claude/skills skill gets loaded
        mcp_servers={"gama-tools": gama_tools_server},
        allowed_tools=[
            "mcp__gama-tools__validate_gaml_syntax",
            "mcp__gama-tools__run_gama_headless",
            "Read",
            "Grep",
            "Glob",
            "Edit",
            "Bash",
        ],
        permission_mode="default",  # every Edit/Bash still goes through can_use_tool
        can_use_tool=make_can_use_tool(allowed_edit_root),
        max_turns=40,
        setting_sources=["project"],  # loads .claude/skills/gama-code-reviewer/SKILL.md
    )

    prompt = (
        f"Review the GAML model at: {gaml_path}\n"
        f"Follow the gama-code-reviewer skill exactly. Read the file first to find "
        f"an experiment name, then validate. "
        f"SYNTAX errors: you may auto-fix and loop up to "
        f"{MAX_SYNTAX_FIX_ITERATIONS} times. LOGIC/data errors (per the checklist): "
        f"only PROPOSE, don't edit the file, wait for the user. "
        f"End with the report in the skill's format."
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        print(f"\n[tool call: {block.name}]")
            elif isinstance(message, ResultMessage):
                print(f"\n--- Done: {message.subtype} ---")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python agent.py path/to/model.gaml")
        sys.exit(1)
    asyncio.run(review_model(sys.argv[1]))
