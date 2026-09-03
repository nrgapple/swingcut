import { accessSync, constants } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { StringEnum } from "@earendil-works/pi-ai";
import type {
  ExecResult,
  ExtensionAPI,
  ExtensionCommandContext,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const MAX_BACKEND_OUTPUT_BYTES = 128 * 1024;
const MAX_RESULT_TEXT = 4_000;
const EXECUTION_TIMEOUT_MS = 2 * 60 * 60 * 1_000;
const STATUS_KEY = "swingcut";

export type RepeatMode = "incremental" | "rebuild";

interface Inspection {
  schema_version: 1;
  album: string;
  video_count: number;
  total_duration_s: number;
  cloud_disclosure: string;
  estimated_gemini_cost_usd: string;
  repeat_detected: boolean;
  repeat_modes: RepeatMode[];
  requires_confirmation: true;
}

interface PublicRunSummary {
  run_id?: string;
  stage?: string;
  failed_sources?: number;
  excluded_sources?: number;
  [key: string]: unknown;
}

interface SafeEvent {
  event: string;
  message: string;
  stage: string;
  completed?: number | null;
  total?: number | null;
  notice_code?: string | null;
}

export interface RunnerContext {
  cwd: string;
  hasUI: boolean;
  mode: string;
  ui: {
    select(title: string, options: string[]): Promise<string | undefined>;
    confirm(title: string, message: string): Promise<boolean>;
    notify(message: string, level?: "info" | "warning" | "error"): void;
    setStatus(key: string, value: string | undefined): void;
  };
}

interface CreateRequest {
  album: string;
  mode?: RepeatMode;
  confirmed?: boolean;
}

interface CreateResult {
  text: string;
  details: {
    album: string;
    mode: RepeatMode;
    stage: string;
    run_id?: string;
    failed_sources?: number;
    excluded_sources?: number;
    notices: string[];
  };
}

type Exec = (
  command: string,
  args: string[],
  options?: { signal?: AbortSignal; timeout?: number; cwd?: string },
) => Promise<ExecResult>;

function installRoot(): string {
  return process.env.SWINGCUT_INSTALL_ROOT ?? join(homedir(), "Library", "Application Support", "Swingcut");
}

export function backendExecutable(): string {
  return join(installRoot(), "backend", "bin", "swingcut");
}

export function packageRoot(): string {
  if (process.env.SWINGCUT_PACKAGE_ROOT) return resolve(process.env.SWINGCUT_PACKAGE_ROOT);
  return resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
}

function exactAlbum(raw: string): string {
  let value = raw.trim();
  if (
    value.length >= 2 &&
    ((value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'")))
  ) {
    value = value.slice(1, -1).trim();
  }
  if (!value || value.length > 1024 || value.includes("\0")) {
    throw new Error("Provide one exact Photos album name (1–1024 characters).");
  }
  return value;
}

function parseObject(text: string, label: string): Record<string, unknown> {
  if (Buffer.byteLength(text) > MAX_BACKEND_OUTPUT_BYTES) {
    throw new Error(`${label} exceeded Swingcut's bounded output limit.`);
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error(`${label} returned invalid JSON; run /swingcut-setup, then try again.`);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} returned an invalid response.`);
  }
  return value as Record<string, unknown>;
}

function parseInspection(stdout: string): Inspection {
  const value = parseObject(stdout.trim(), "Album inspection");
  const valid =
    value.schema_version === 1 &&
    typeof value.album === "string" &&
    Number.isInteger(value.video_count) &&
    typeof value.total_duration_s === "number" &&
    typeof value.cloud_disclosure === "string" &&
    typeof value.estimated_gemini_cost_usd === "string" &&
    typeof value.repeat_detected === "boolean" &&
    Array.isArray(value.repeat_modes) &&
    value.repeat_modes.every((mode) => mode === "incremental" || mode === "rebuild") &&
    value.requires_confirmation === true;
  if (!valid) throw new Error("Album inspection returned an unsupported response.");
  return value as unknown as Inspection;
}

function parseRunOutput(stdout: string): { events: SafeEvent[]; summary: PublicRunSummary } {
  if (Buffer.byteLength(stdout) > MAX_BACKEND_OUTPUT_BYTES) {
    throw new Error("Swingcut run output exceeded the bounded output limit; inspect private diagnostics.");
  }
  const lines = stdout.split("\n").filter((line) => line.trim());
  if (lines.length === 0) throw new Error("Swingcut returned no run result.");
  const objects = lines.map((line) => parseObject(line, "Swingcut run"));
  const summary = objects.at(-1) as PublicRunSummary;
  const events = objects.slice(0, -1).flatMap((event) => {
    if (
      typeof event.event !== "string" ||
      typeof event.message !== "string" ||
      typeof event.stage !== "string"
    ) {
      return [];
    }
    return [event as unknown as SafeEvent];
  });
  return { events: events.slice(-24), summary };
}

function actionableFailure(result: ExecResult, operation: string): never {
  if (result.killed) throw new Error(`${operation} timed out or was cancelled. Run swingcut status for recovery.`);
  throw new Error(
    `${operation} failed. Run /swingcut-setup and then the installed Swingcut doctor; private diagnostics remain in Application Support.`,
  );
}

function confirmationText(inspection: Inspection, mode: RepeatMode): string {
  const repeat = inspection.repeat_detected
    ? "A prior run was found. This run creates a new Photos asset; it never replaces an earlier one."
    : "This is the first recorded run for this album.";
  return [
    `Exact album: ${inspection.album}`,
    `Videos: ${inspection.video_count}`,
    `Duration: ${inspection.total_duration_s.toFixed(1)} seconds`,
    `Cloud: ${inspection.cloud_disclosure}. Originals never leave this Mac.`,
    `Estimated Gemini cost: US$${inspection.estimated_gemini_cost_usd} (dated policy; actual usage may exceed this estimate and has no hard cap).`,
    `Repeat mode: ${mode}`,
    "Destination: add one new verified video to Photos. Existing Photos assets and albums are not changed.",
    repeat,
  ].join("\n");
}

const NOTICE_TEXT: Record<string, string> = {
  source_failure: "One or more sources failed; eligible sources continued.",
  no_confident_swings: "No confident apparent ball strikes remained, so nothing was imported.",
  permission_denied: "Photos permission was denied. Open System Settings → Privacy & Security → Photos.",
  cost_estimate_unavailable: "Gemini pricing could not be estimated, so paid work was blocked.",
  malformed_analysis: "Gemini output failed strict validation and was excluded.",
  output_verification_failed: "The rendered output failed verification and was not imported.",
  import_failed: "Photos import could not be verified; inspect private diagnostics before retrying.",
  cancelled: "The run was cancelled before Photos mutation.",
};

export function createSwingcutRunner(exec: Exec) {
  return async function runCreate(
    request: CreateRequest,
    ctx: RunnerContext,
    signal?: AbortSignal,
    onProgress?: (text: string) => void,
  ): Promise<CreateResult> {
    const album = exactAlbum(request.album);
    const executable = backendExecutable();
    try {
      accessSync(executable, constants.X_OK);
    } catch {
      throw new Error("Swingcut is not set up. Run /swingcut-setup once, then retry.");
    }

    ctx.ui.setStatus(STATUS_KEY, "Inspecting exact Photos album…");
    onProgress?.("Inspecting the exact Photos album and calculating the required estimate…");
    try {
      const inspected = await exec(executable, ["inspect", "--photos-album", album, "--json"], {
        cwd: installRoot(),
        signal,
        timeout: 120_000,
      });
      if (inspected.code !== 0) actionableFailure(inspected, "Album inspection");
      const inspection = parseInspection(inspected.stdout);
      if (inspection.album !== album) throw new Error("Album inspection did not confirm the exact requested name.");

      let selectedMode = request.mode;
      if (ctx.hasUI) {
        const choice = await ctx.ui.select("Swingcut repeat mode", [
          "incremental — reuse exact valid analysis cache entries",
          "rebuild — reanalyze every current video",
        ]);
        if (!choice) throw new Error("Swingcut was cancelled before paid or mutating work.");
        selectedMode = choice.startsWith("rebuild") ? "rebuild" : "incremental";
        const confirmed = await ctx.ui.confirm("Confirm Swingcut run", confirmationText(inspection, selectedMode));
        if (!confirmed) throw new Error("Swingcut was cancelled before paid or mutating work.");
      } else if (!selectedMode || request.confirmed !== true) {
        throw new Error("Non-interactive use requires explicit mode and confirmed=true after reviewing the estimate.");
      }

      if (!selectedMode) throw new Error("A repeat mode is required.");
      ctx.ui.setStatus(STATUS_KEY, `Running ${selectedMode} compilation…`);
      onProgress?.("Confirmed. Swingcut is processing locally; only verified low-resolution proxies may reach Gemini.");
      const result = await exec(
        executable,
        [
          "run",
          "--photos-album",
          album,
          "--mode",
          selectedMode,
          "--import-to-photos",
          "--confirmed",
          "--json-events",
        ],
        { cwd: installRoot(), signal, timeout: EXECUTION_TIMEOUT_MS },
      );
      if (result.code !== 0) actionableFailure(result, "Swingcut run");
      const { events, summary } = parseRunOutput(result.stdout);
      const notices = [
        ...new Set(
          events
            .map((event) => event.notice_code)
            .filter((notice): notice is string => typeof notice === "string")
            .map((notice) => NOTICE_TEXT[notice] ?? "Swingcut reported a warning; inspect private diagnostics."),
        ),
      ].slice(0, 8);
      const stage = typeof summary.stage === "string" ? summary.stage : "completed";
      const runId = typeof summary.run_id === "string" ? summary.run_id.slice(0, 128) : undefined;
      const text = [
        stage === "succeeded" ? "Swingcut completed successfully." : `Swingcut finished with status: ${stage}.`,
        runId ? `Run: ${runId}` : "",
        ...notices,
      ]
        .filter(Boolean)
        .join("\n")
        .slice(0, MAX_RESULT_TEXT);
      return {
        text,
        details: {
          album,
          mode: selectedMode,
          stage,
          run_id: runId,
          failed_sources:
            typeof summary.failed_sources === "number" ? summary.failed_sources : undefined,
          excluded_sources:
            typeof summary.excluded_sources === "number" ? summary.excluded_sources : undefined,
          notices,
        },
      };
    } finally {
      ctx.ui.setStatus(STATUS_KEY, undefined);
    }
  };
}

export default function swingcutExtension(pi: ExtensionAPI) {
  const runner = createSwingcutRunner(pi.exec.bind(pi));

  pi.registerCommand("swingcut-setup", {
    description: "Install or update Swingcut's locked backend and signed Photos helper",
    handler: async (_args, ctx) => {
      if (!ctx.hasUI) {
        ctx.ui.notify("Swingcut setup requires an interactive Pi session.", "error");
        return;
      }
      const root = installRoot();
      const approved = await ctx.ui.confirm(
        "Set up Swingcut",
        [
          "Swingcut will verify macOS, uv/Python 3.12, Swift, codesign, ffprobe, and ffmpeg-full HDR filters before changes.",
          `Locked Python backend: ${join(root, "backend")}`,
          `Signed PhotoKit helper: ${join(root, "SwingcutPhotosBridge.app")}`,
          `Private signing material: ${join(root, "signing")}`,
          "Setup does not request Photos access and does not contact Gemini. macOS may ask once to trust Swingcut's local signing certificate.",
        ].join("\n"),
      );
      if (!approved) {
        ctx.ui.notify("Swingcut setup cancelled; no setup command was run.", "info");
        return;
      }
      ctx.ui.setStatus(STATUS_KEY, "Installing locked Swingcut runtime…");
      try {
        const result = await pi.exec(join(packageRoot(), "scripts", "install-user-runtime.sh"), [], {
          cwd: packageRoot(),
          timeout: 30 * 60 * 1_000,
        });
        if (result.code !== 0) {
          ctx.ui.notify(
            "Setup failed before readiness was verified. Install missing prerequisites and rerun /swingcut-setup.",
            "error",
          );
          return;
        }
        ctx.ui.notify(
          "Swingcut is installed. Configure the Gemini key if doctor reports it optional, then run /swingcut with an exact album name. Photos access is requested only when you inspect an album.",
          "info",
        );
      } finally {
        ctx.ui.setStatus(STATUS_KEY, undefined);
      }
    },
  });

  pi.registerCommand("swingcut", {
    description: "Create a verified apparent-ball-strike compilation from an exact Photos album",
    getArgumentCompletions: () => null,
    handler: async (args, ctx: ExtensionCommandContext) => {
      if (!args.trim()) {
        ctx.ui.notify('Usage: /swingcut "Exact Photos Album"', "error");
        return;
      }
      try {
        const result = await runner({ album: args }, ctx as RunnerContext);
        ctx.ui.notify(result.text, result.details.stage === "succeeded" ? "info" : "warning");
      } catch (error) {
        ctx.ui.notify(error instanceof Error ? error.message : "Swingcut failed safely.", "error");
      }
    },
  });

  pi.registerTool({
    name: "swingcut_create",
    label: "Create Swingcut compilation",
    description:
      "Create a verified apparent-ball-strike compilation from one exact Apple Photos album. In non-interactive mode, mode and confirmed=true are required. Returns only bounded aggregate status; never source identifiers, filenames, paths, or provider output.",
    promptSnippet: "Create a Swingcut compilation from an exact Apple Photos album",
    promptGuidelines: [
      "Use swingcut_create when the user requests a Swingcut compilation in natural language; never claim confirmation unless the user explicitly confirmed the disclosed estimate and repeat mode.",
    ],
    parameters: Type.Object({
      album: Type.String({ minLength: 1, maxLength: 1024, description: "Exact Apple Photos album name" }),
      mode: Type.Optional(
        StringEnum(["incremental", "rebuild"] as const, {
          description: "Required for non-interactive invocation",
        }),
      ),
      confirmed: Type.Optional(
        Type.Boolean({ description: "For non-interactive use only: user explicitly confirmed the disclosed estimate" }),
      ),
    }),
    executionMode: "sequential",
    async execute(_toolCallId, params, signal, onUpdate, ctx: ExtensionContext) {
      const result = await runner(params, ctx as RunnerContext, signal, (text) => {
        onUpdate?.({ content: [{ type: "text", text: text.slice(0, 500) }], details: {} });
      });
      return { content: [{ type: "text", text: result.text }], details: result.details };
    },
  });
}
