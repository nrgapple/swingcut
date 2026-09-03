import assert from "node:assert/strict";
import { chmod, mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import swingcutExtension, { backendExecutable, type RunnerContext } from "./index.ts";

interface RegisteredCommand {
  handler: (args: string, ctx: RunnerContext) => Promise<void>;
}

interface RegisteredTool {
  execute: (
    id: string,
    params: { album: string; mode?: "incremental" | "rebuild"; confirmed?: boolean },
    signal: AbortSignal | undefined,
    onUpdate: ((result: unknown) => void) | undefined,
    ctx: RunnerContext,
  ) => Promise<{ content: Array<{ type: string; text: string }>; details: Record<string, unknown> }>;
}

function inspection(album: string) {
  return JSON.stringify({
    schema_version: 1,
    album,
    video_count: 4,
    total_duration_s: 206.1,
    cloud_disclosure: "full-duration silent metadata-stripped 480px proxies only",
    estimated_gemini_cost_usd: "0.970010",
    repeat_detected: true,
    repeat_modes: ["incremental", "rebuild"],
    requires_confirmation: true,
  });
}

function runOutput() {
  return [
    JSON.stringify({
      schema_version: 1,
      event: "progress",
      run_id: "run_test",
      stage: "analyzing",
      message: "analyzing_media",
      completed: 1,
      total: 4,
      notice_code: null,
      occurred_at: "2026-09-03T00:00:00Z",
    }),
    JSON.stringify({
      run_id: "run_test",
      stage: "succeeded",
      failed_sources: 0,
      excluded_sources: 2,
    }),
  ].join("\n");
}

async function harness() {
  const root = await mkdtemp(join(tmpdir(), "swingcut-extension-test-"));
  process.env.SWINGCUT_INSTALL_ROOT = root;
  const packageInstall = join(root, "pi-package");
  process.env.SWINGCUT_PACKAGE_ROOT = packageInstall;
  await mkdir(join(packageInstall, "scripts"), { recursive: true });
  const executable = backendExecutable();
  await mkdir(join(executable, ".."), { recursive: true });
  await writeFile(executable, "#!/bin/sh\nexit 0\n");
  await chmod(executable, 0o755);

  const calls: Array<{ command: string; args: string[]; cwd?: string }> = [];
  const commands = new Map<string, RegisteredCommand>();
  const tools = new Map<string, RegisteredTool>();
  const pi = {
    exec: async (command: string, args: string[], options?: { cwd?: string }) => {
      calls.push({ command, args, cwd: options?.cwd });
      if (args[0] === "inspect") {
        return { stdout: inspection(args[2]!), stderr: "", code: 0, killed: false };
      }
      return { stdout: runOutput(), stderr: "", code: 0, killed: false };
    },
    registerCommand: (name: string, command: RegisteredCommand) => commands.set(name, command),
    registerTool: (tool: RegisteredTool & { name: string }) => tools.set(tool.name, tool),
  };
  swingcutExtension(pi as never);
  return { root, calls, commands, tools };
}

function context(cwd: string, hasUI: boolean, choice = "incremental — reuse exact valid analysis cache entries") {
  const notices: Array<{ message: string; level?: string }> = [];
  const confirmations: string[] = [];
  const ctx: RunnerContext = {
    cwd,
    hasUI,
    mode: hasUI ? "tui" : "print",
    ui: {
      select: async () => choice,
      confirm: async (_title, message) => {
        confirmations.push(message);
        return true;
      },
      notify: (message, level) => notices.push({ message, level }),
      setStatus: () => undefined,
    },
  };
  return { ctx, notices, confirmations };
}

test("registers setup, slash command, and natural-language tool", async () => {
  const { commands, tools } = await harness();
  assert.deepEqual([...commands.keys()].sort(), ["swingcut", "swingcut-setup"]);
  assert.ok(tools.has("swingcut_create"));
});

test("setup is repeatable and always uses the installed package source", async () => {
  const { root, calls, commands } = await harness();
  const { ctx, confirmations } = context("/tmp/setup-project", true);

  await commands.get("swingcut-setup")!.handler("", ctx);
  await commands.get("swingcut-setup")!.handler("", ctx);

  assert.equal(confirmations.length, 2);
  assert.ok(confirmations[0]!.includes(root));
  assert.equal(calls.length, 2);
  assert.ok(calls.every((call) => call.command === join(root, "pi-package", "scripts", "install-user-runtime.sh")));
  assert.ok(calls.every((call) => call.cwd === join(root, "pi-package")));
});

test("slash command works from an unrelated project using only the installed backend", async () => {
  const { root, calls, commands } = await harness();
  const project = await mkdtemp(join(tmpdir(), "unrelated-project-a-"));
  const { ctx, notices, confirmations } = context(project, true);

  await commands.get("swingcut")!.handler('"Exact Album"', ctx);

  assert.equal(calls.length, 2);
  assert.ok(calls.every((call) => call.command.startsWith(root)));
  assert.ok(calls.every((call) => call.cwd === root));
  assert.ok(calls.every((call) => !call.command.includes("/Projects/swingcut")));
  assert.deepEqual(calls[1]!.args.slice(0, 7), [
    "run",
    "--photos-album",
    "Exact Album",
    "--mode",
    "incremental",
    "--import-to-photos",
    "--confirmed",
  ]);
  assert.match(confirmations[0]!, /US\$0\.970010/);
  assert.match(confirmations[0]!, /Originals never leave this Mac/);
  assert.match(confirmations[0]!, /Existing Photos assets and albums are not changed/);
  assert.match(notices.at(-1)!.message, /completed successfully/);
});

test("tool works from a second unrelated project with explicit non-UI choices", async () => {
  const { root, calls, tools } = await harness();
  const project = await mkdtemp(join(tmpdir(), "unrelated-project-b-"));
  const { ctx } = context(project, false);

  const result = await tools.get("swingcut_create")!.execute(
    "call-1",
    { album: "Exact Album", mode: "rebuild", confirmed: true },
    undefined,
    undefined,
    ctx,
  );

  assert.ok(calls.every((call) => call.command.startsWith(root) && call.cwd === root));
  assert.equal(calls[1]!.args[4], "rebuild");
  assert.equal(result.details.stage, "succeeded");
  assert.equal(result.details.excluded_sources, 2);
  assert.ok(JSON.stringify(result).length < 4_000);
});

test("non-UI tool fails closed without explicit mode and confirmation", async () => {
  const { tools } = await harness();
  const { ctx } = context("/tmp/third-project", false);
  await assert.rejects(
    tools.get("swingcut_create")!.execute(
      "call-2",
      { album: "Exact Album" },
      undefined,
      undefined,
      ctx,
    ),
    /requires explicit mode and confirmed=true/,
  );
});
