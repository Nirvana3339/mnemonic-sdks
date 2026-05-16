# Mnemonic SDKs

Official SDKs and integrations for [Mnemonic](https://mnemonic-production.up.railway.app) — persistent cognitive infrastructure for AI agents.

## Packages

| Package | Description | Install |
|---|---|---|
| `mnemonic-sdk` (Python) | Python SDK | `pip install mnemonic-sdk` |
| `@mnemonic-ai/sdk` (JS/TS) | JavaScript/TypeScript SDK | `npm install @mnemonic-ai/sdk` |
| `@mnemonic-ai/mcp` | MCP server for Claude Desktop & Cursor | `npx @mnemonic-ai/mcp` |

## Quick Start

### Python

```python
from mnemonic import Mnemonic

m = Mnemonic(api_key="mnemo_sk_...")

# Before your agent runs
memory = m.recall(
    agent_id="my-agent",
    task="fix React context rerender storm",
    context={"framework": "react", "runtime": "production"},
)

for lesson in memory["lessons"]:
    print(lesson["problem_signature"], "→", lesson["root_cause"])
    print("Fix:", lesson["solution_steps"])

# After your agent runs
m.capture(
    agent_id="my-agent",
    task="fix React context rerender storm",
    actions=[{"type": "code_edit", "target": "AppContext.tsx", "result": "split providers"}],
    output="Resolved — split context providers and memoized values",
    success=True,
)
```

### JavaScript / TypeScript

```typescript
import { Mnemonic } from '@mnemonic-ai/sdk';

const m = new Mnemonic({ apiKey: 'mnemo_sk_...' });

const memory = await m.recall({
  agentId: 'my-agent',
  task: 'fix React context rerender storm',
  context: { framework: 'react', runtime: 'production' },
});

await m.capture({
  agentId: 'my-agent',
  task: 'fix React context rerender storm',
  actions: [{ type: 'code_edit', target: 'AppContext.tsx', result: 'split providers' }],
  output: 'Resolved — split context, memoized values',
  success: true,
});
```

### MCP (Claude Desktop / Cursor)

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

Claude will automatically call `mnemonic_recall` before tasks and `mnemonic_capture` after.

## API Reference

Full docs at [mnemonic-production.up.railway.app/docs](https://mnemonic-production.up.railway.app/docs)
