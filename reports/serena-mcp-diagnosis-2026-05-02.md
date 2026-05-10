# Serena MCP Diagnosis - 2026-05-02

## Symptom

- Codex Serena tool call failed immediately with `Transport closed`.
- Repro tool: `serena/check_onboarding_performed`.

## Evidence

- Codex config path: `/Users/hujia/.codex/config.toml`.
- Current Codex Serena route uses:
  - `command = "uvx"`
  - `--context ide-assistant`
  - `--project /Users/hujia/Desktop/RedditSignalScanner`
  - `--transport stdio`
  - `startup_timeout_sec = 60.0`
- Serena global config and project config exist and include `RedditSignalScanner`.
- Project config path: `.serena/project.yml`.
- Latest Serena log checked:
  - `/Users/hujia/.serena/logs/2026-05-02/mcp_20260502-235808_47656.txt`
- Manual self-check with the Codex command did not complete MCP initialization within 12 seconds.

## Current Root Cause Hypothesis

Serena itself is installed and has worked before, but the active Codex MCP transport is stale or closed. The Codex route is also behind the working Claude route:

- Codex still uses deprecated context `ide-assistant`.
- Claude uses `claude-code`.
- Codex uses PATH-based `uvx`; Claude uses `/Users/hujia/.local/bin/uvx`.

This is a tool-connection/runtime issue, not a RedditSignalScanner business-code issue.

## Recommended Fix

Align Codex Serena config with the working Claude config:

- Change context from `ide-assistant` to `claude-code`.
- Use absolute `uvx` path: `/Users/hujia/.local/bin/uvx`.
- Keep `--project /Users/hujia/Desktop/RedditSignalScanner`.
- Keep `--transport stdio`.
- Restart Codex after config change so the MCP transport is recreated.

## Applied

Updated `/Users/hujia/.codex/config.toml`:

- `command` changed from `uvx` to `/Users/hujia/.local/bin/uvx`.
- `--context` changed from `ide-assistant` to `claude-code`.
- `startup_timeout_sec` changed from `60.0` to `600.0`.

After the edit, the current in-memory Codex tool transport still returns `Transport closed`, so this session needs a Codex restart or MCP reconnect to validate the fixed route.
