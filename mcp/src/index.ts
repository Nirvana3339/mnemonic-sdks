#!/usr/bin/env node
/**
 * Mnemonic MCP Server
 *
 * Exposes Mnemonic recall + capture as MCP tools so any MCP-compatible
 * host (Claude Desktop, Cursor, Continue, etc.) can give its agents
 * persistent memory automatically.
 *
 * Tools:
 *   mnemonic_recall  — fetch relevant lessons before a task
 *   mnemonic_capture — record what happened after a task
 *
 * Setup (Claude Desktop):
 *   Add to claude_desktop_config.json:
 *   {
 *     "mcpServers": {
 *       "mnemonic": {
 *         "command": "npx",
 *         "args": ["-y", "@mnemonic-ai/mcp"],
 *         "env": {
 *           "MNEMONIC_API_KEY": "mnemo_sk_...",
 *           "MNEMONIC_AGENT_ID": "your-agent-id"
 *         }
 *       }
 *     }
 *   }
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// ------------------------------------------------------------------ config
const API_KEY    = process.env.MNEMONIC_API_KEY || process.env.MNEMO_API_KEY || "";
const AGENT_ID   = process.env.MNEMONIC_AGENT_ID || "mcp-agent";
const BASE_URL   = (process.env.MNEMONIC_BASE_URL || "https://mnemonic-production.up.railway.app/api").replace(/\/$/, "");
const TOP_K      = parseInt(process.env.MNEMONIC_TOP_K || "5", 10);

if (!API_KEY) {
  console.error("[mnemonic-mcp] ERROR: MNEMONIC_API_KEY is not set.");
  process.exit(1);
}

// ------------------------------------------------------------------ http
async function mnemonicRequest(path: string, body: Record<string, any>): Promise<any> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
      "User-Agent": "mnemonic-mcp/0.1.0",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Mnemonic API ${res.status}: ${text}`);
  }

  return res.json();
}

// ------------------------------------------------------------------ format helpers
function formatLesson(lesson: any, index: number): string {
  const sig        = lesson.problem_signature || lesson.problemSignature;
  const rootCause  = lesson.root_cause        || lesson.rootCause;
  const steps      = lesson.solution_steps    || lesson.solutionSteps || [];
  const validation = lesson.validation_steps  || lesson.validationSteps || [];
  const score      = lesson.final_score       || lesson.finalScore || lesson.similarity || 0;

  let out = `[${index + 1}] score=${score.toFixed(2)}`;
  if (sig)       out += `  signature=${sig}`;
  if (rootCause) out += `\n    Root cause: ${rootCause}`;
  if (steps.length)      out += `\n    Fix: ${steps.join(" → ")}`;
  if (validation.length) out += `\n    Validate: ${validation.join(", ")}`;
  if (!sig && !rootCause) out += `\n    ${lesson.content}`;
  return out;
}

function formatRecallResponse(data: any, task: string): string {
  const lessons    = data.lessons    || [];
  const procedures = data.procedures || [];
  const warnings   = data.warnings   || [];

  if (lessons.length === 0 && procedures.length === 0) {
    return `No relevant lessons found for: "${task}"\nThis is a new task — Mnemonic will learn from it after capture.`;
  }

  const lines: string[] = [`Mnemonic recalled ${lessons.length} lesson(s) for: "${task}"\n`];

  if (lessons.length > 0) {
    lines.push("LESSONS:");
    lessons.forEach((l: any, i: number) => lines.push(formatLesson(l, i)));
  }

  if (procedures.length > 0) {
    lines.push("\nPROCEDURES:");
    procedures.forEach((p: any, i: number) => {
      lines.push(`[${i + 1}] ${p.name} (confidence=${p.confidence?.toFixed(2)})`);
      if (p.steps?.length) lines.push(`    Steps: ${p.steps.join(" → ")}`);
    });
  }

  if (warnings.length > 0) {
    lines.push(`\nWarnings: ${warnings.join(", ")}`);
  }

  return lines.join("\n");
}

// ------------------------------------------------------------------ server
const server = new Server(
  { name: "mnemonic", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// ------------------------------------------------------------------ tools list
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "mnemonic_recall",
      description:
        "Fetch relevant lessons and procedures from Mnemonic memory before performing a task. " +
        "Call this BEFORE starting any non-trivial task to benefit from past experience. " +
        "Returns root causes, fix steps, and validation procedures from similar past situations.",
      inputSchema: {
        type: "object",
        properties: {
          task: {
            type: "string",
            description: "Description of the task you are about to perform.",
          },
          context: {
            type: "object",
            description: "Optional environment metadata to improve retrieval accuracy. " +
              "E.g. {\"framework\": \"react\", \"language\": \"typescript\", \"runtime\": \"production\"}",
            additionalProperties: true,
          },
          limit: {
            type: "number",
            description: `Max lessons to retrieve (default ${TOP_K}).`,
          },
        },
        required: ["task"],
      },
    },
    {
      name: "mnemonic_capture",
      description:
        "Record what happened after completing a task so Mnemonic can learn from it. " +
        "Call this AFTER every task — success or failure. " +
        "Mnemonic uses this to build lessons that help future tasks.",
      inputSchema: {
        type: "object",
        properties: {
          task: {
            type: "string",
            description: "The task that was performed.",
          },
          output: {
            type: "string",
            description: "Summary of what the agent did and the final result.",
          },
          success: {
            type: "boolean",
            description: "Whether the task succeeded.",
          },
          actions: {
            type: "array",
            description: "List of actions taken. E.g. [{\"type\": \"tool_call\", \"target\": \"bash\", \"result\": \"ok\"}]",
            items: {
              type: "object",
              properties: {
                type:   { type: "string" },
                target: { type: "string" },
                result: { type: "string" },
              },
            },
          },
          time_taken_ms: {
            type: "number",
            description: "How long the task took in milliseconds (optional).",
          },
          retries: {
            type: "number",
            description: "Number of retries needed (default 0).",
          },
        },
        required: ["task", "output", "success"],
      },
    },
  ],
}));

// ------------------------------------------------------------------ tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "mnemonic_recall") {
    const task    = args?.task as string;
    const context = args?.context as Record<string, any> | undefined;
    const limit   = (args?.limit as number) || TOP_K;

    const payload: Record<string, any> = {
      agent_id: AGENT_ID,
      task,
      limit,
    };
    if (context) payload.context = context;

    try {
      const data = await mnemonicRequest("/v1/recall", payload);
      return {
        content: [{ type: "text", text: formatRecallResponse(data, task) }],
      };
    } catch (err: any) {
      return {
        content: [{ type: "text", text: `Mnemonic recall failed: ${err.message}` }],
        isError: true,
      };
    }
  }

  if (name === "mnemonic_capture") {
    const task       = args?.task as string;
    const output     = args?.output as string;
    const success    = args?.success as boolean;
    const actions    = (args?.actions as any[]) || [];
    const timeTaken  = args?.time_taken_ms as number | undefined;
    const retries    = (args?.retries as number) || 0;

    try {
      const data = await mnemonicRequest("/v1/events", {
        agent_id:   AGENT_ID,
        task,
        output,
        success,
        actions,
        time_taken: timeTaken,
        retries,
        metadata:   { source: "mcp" },
      });

      const status = success ? "✅ Success" : "⚠️ Failure";
      return {
        content: [{
          type: "text",
          text: `${status} captured. Mnemonic is learning from this task.\nevent_id: ${data.event_id || data.id || "queued"}`,
        }],
      };
    } catch (err: any) {
      return {
        content: [{ type: "text", text: `Mnemonic capture failed: ${err.message}` }],
        isError: true,
      };
    }
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

// ------------------------------------------------------------------ start
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`[mnemonic-mcp] Server running. agent_id=${AGENT_ID} base_url=${BASE_URL}`);
}

main().catch((err) => {
  console.error("[mnemonic-mcp] Fatal:", err);
  process.exit(1);
});
