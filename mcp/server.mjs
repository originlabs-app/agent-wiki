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
const WIKI = path.join(ROOT, "wiki");
const RAW = path.join(ROOT, "raw");
const LOG = path.join(WIKI, "log.md");
const INDEX = path.join(WIKI, "index.md");
const CLI = path.join(ROOT, "cli", "wikictl");

function ensurePaths() {
  fs.mkdirSync(path.join(WIKI, "projects"), { recursive: true });
  fs.mkdirSync(RAW, { recursive: true });
}

function readFileSafe(filePath) {
  return fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : "";
}

function appendLog(agent, op, description) {
  ensurePaths();
  if (!fs.existsSync(LOG)) {
    fs.writeFileSync(
      LOG,
      [
        "---",
        "type: wiki-log",
        "created: 2026-04-05",
        "---",
        "",
        "# Wiki Log",
        "",
        "Append-only. One entry per operation.",
      ].join("\n") + "\n",
    );
  }
  const date = new Date().toISOString().slice(0, 10);
  fs.appendFileSync(LOG, `\n## [${date}] ${agent} | ${op} | ${description}\n`);
  return `logged: ${agent} | ${op}`;
}

function runCli(args) {
  const result = spawnSync(CLI, args, {
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

function listProjects() {
  ensurePaths();
  const dir = path.join(WIKI, "projects");
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
      description: "Return a short health summary of the local knowledge base.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "read_index",
      description: "Read wiki/index.md.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "list_projects",
      description: "List project wiki pages.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "read_project",
      description: "Read a project wiki page.",
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
  ensurePaths();
  const { name, arguments: args = {} } = request.params;

  if (name === "status") {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              root: ROOT,
              wikiProjectPages: listProjects().length,
              rawFiles: fs.readdirSync(RAW).length,
              index: fs.existsSync(INDEX),
              log: fs.existsSync(LOG),
            },
            null,
            2,
          ),
        },
      ],
    };
  }

  if (name === "read_index") {
    return {
      content: [{ type: "text", text: readFileSafe(INDEX) }],
    };
  }

  if (name === "list_projects") {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(listProjects(), null, 2),
        },
      ],
    };
  }

  if (name === "read_project") {
    const fileName = `${String(args.name).replace(/[^A-Za-z0-9._-]/g, "")}.md`;
    const filePath = path.join(WIKI, "projects", fileName);
    return {
      content: [{ type: "text", text: readFileSafe(filePath) }],
    };
  }

  if (name === "append_log") {
    const result = appendLog(args.agent, args.op, args.description);
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
    const result = runCli(["query", args.query]);
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
