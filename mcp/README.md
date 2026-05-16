# @mnemonic-ai/mcp

MCP server for [Mnemonic](https://github.com/Nirvana3339/mnemonic-sdks) — gives Claude Desktop, Cursor, and any MCP-compatible host persistent memory via two tools:

- **`mnemonic_recall`** — fetch relevant lessons before a task
- **`mnemonic_capture`** — record what happened after a task

## Setup

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mnemonic": {
      "command": "npx",
      "args": ["-y", "@mnemonic-ai/mcp"],
      "env": {
        "MNEMONIC_API_KEY": "mnemo_sk_...",
        "MNEMONIC_AGENT_ID": "claude-desktop"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MNEMONIC_API_KEY` | ✅ | Your Mnemonic API key |
| `MNEMONIC_AGENT_ID` | ✅ | Identifier for this agent |
| `MNEMONIC_BASE_URL` | ❌ | Override API base URL |
| `MNEMONIC_TOP_K` | ❌ | Max lessons to retrieve (default 5) |

## Tools

### `mnemonic_recall`

Call **before** any non-trivial task. Returns root causes, fix steps, and validation from similar past situations.

```
task: "fix React context rerender storm"
context: {"framework": "react", "runtime": "production"}
```

### `mnemonic_capture`

Call **after** every task — success or failure. Mnemonic learns from it.

```
task: "fix React context rerender storm"
output: "Split context providers, memoized values — resolved"
success: true
actions: [{"type": "code_edit", "target": "AppContext.tsx", "result": "split"}]
```
