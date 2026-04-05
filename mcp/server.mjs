import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const CLI = path.join(ROOT, "cli", "wikictl");

function parseCliContext(argv) {
  const cliContext = [];

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--instance" || arg === "--config") {
      const value = argv[i + 1];
      if (value) {
        cliContext.push(arg, value);
        i += 1;
      }
    }
  }

  return cliContext;
}

const CLI_CONTEXT = parseCliContext(process.argv.slice(2));

function runCli(args) {
  const result = spawnSync(CLI, [...CLI_CONTEXT, ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env: process.env,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || `wikictl ${args.join(" ")}`).trim());
  }

  return (result.stdout || "").trim();
}

function parseKeyValue(text) {
  return text.split("\n").reduce((acc, line) => {
    const idx = line.indexOf("=");
    if (idx === -1) {
      return acc;
    }
    const key = line.slice(0, idx);
    const value = line.slice(idx + 1);
    acc[key] = value;
    return acc;
  }, {});
}

function resolvePaths() {
  return parseKeyValue(runCli(["paths"]));
}

function readFileSafe(filePath) {
  return fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : "";
}

function listProjects() {
  const paths = resolvePaths();
  const dir = path.join(paths.wiki_root, "projects");

  if (!fs.existsSync(dir)) {
    return [];
  }

  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .map((name) => ({
      name,
      path: path.join("wiki", "projects", name),
    }));
}

const server = new Server(
  {
    name: "agent-wiki",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "status",
      description: "Return a short health summary of the active knowledge base.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "read_index",
      description: "Read wiki/index.md from the active instance.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "list_projects",
      description: "List project wiki pages from the active instance.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "read_project",
      description: "Read a project wiki page from the active instance.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string" },
        },
        required: ["name"],
      },
    },
    {
      name: "append_log",
      description: "Append one line to wiki/log.md.",
      inputSchema: {
        type: "object",
        properties: {
          agent: { type: "string" },
          op: { type: "string" },
          description: { type: "string" },
        },
        required: ["agent", "op", "description"],
      },
    },
    {
      name: "ingest",
      description: "Register source files against a project page.",
      inputSchema: {
        type: "object",
        properties: {
          project: { type: "string" },
          sources: {
            type: "array",
            items: { type: "string" },
            minItems: 1,
          },
        },
        required: ["project", "sources"],
      },
    },
    {
      name: "query",
      description: "Search the wiki and raw sources.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string" },
        },
        required: ["query"],
      },
    },
    {
      name: "heal",
      description: "Rebuild the wiki index from project pages.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  if (name === "status") {
    return {
      content: [{ type: "text", text: runCli(["status"]) }],
    };
  }

  if (name === "read_index") {
    const paths = resolvePaths();
    return {
      content: [{ type: "text", text: readFileSafe(paths.index) }],
    };
  }

  if (name === "list_projects") {
    return {
      content: [{ type: "text", text: JSON.stringify(listProjects(), null, 2) }],
    };
  }

  if (name === "read_project") {
    const paths = resolvePaths();
    const fileName = `${String(args.name).replace(/[^A-Za-z0-9._-]/g, "")}.md`;
    const filePath = path.join(paths.wiki_root, "projects", fileName);
    return {
      content: [{ type: "text", text: readFileSafe(filePath) }],
    };
  }

  if (name === "append_log") {
    const result = runCli(["log", args.agent, args.op, args.description]);
    return {
      content: [{ type: "text", text: result }],
    };
  }

  if (name === "ingest") {
    const sources = Array.isArray(args.sources) ? args.sources : [];
    const result = runCli(["ingest", args.project, ...sources]);
    return {
      content: [{ type: "text", text: result }],
    };
  }

  if (name === "query") {
    const queryArgs = String(args.query).split(/\s+/).filter(Boolean);
    const result = runCli(["query", ...queryArgs]);
    return {
      content: [{ type: "text", text: result }],
    };
  }

  if (name === "heal") {
    const result = runCli(["heal"]);
    return {
      content: [{ type: "text", text: result }],
    };
  }

  throw new Error(`Unknown tool: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
