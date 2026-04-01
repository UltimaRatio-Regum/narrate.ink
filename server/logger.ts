/**
 * server/logger.ts — Application-wide logging configuration (winston).
 *
 * Log levels (lowest → highest severity):
 *   trace    (10) — Extremely verbose: every startup step, every lifecycle event.
 *   debug    (20) — Operational detail useful during development.
 *   verbose  (30) — Moderate detail; notable but not actionable.
 *   http     (40) — HTTP request/response cycle.
 *   info     (50) — Normal milestones: server started, backend ready.
 *   warn     (60) — Recoverable issues.
 *   error    (70) — Operation failures.
 *   fatal    (80) — Fatal conditions; usually followed by process.exit().
 *
 * Transports
 * ──────────
 * Always active:
 *   • Console  — coloured, human-readable.  Level controlled by LOG_LEVEL env var
 *                (default "debug" in dev / "info" in production).
 *   • File     — logs/narrateink.log, JSON lines, all levels.
 *   • File     — logs/narrateink-errors.log, warn and above only.
 *
 * Optional (activated by environment variables):
 *   • syslog   — set LOG_SYSLOG_HOST=hostname  (default port 514)
 *   • Email    — set LOG_SMTP_HOST, LOG_SMTP_TO, LOG_SMTP_FROM
 *
 * Usage
 * ─────
 *   import { logger } from "./logger";
 *   logger.info("Server started", { port: 5000 });
 *   logger.trace("Entering setupVite");
 *   logger.fatal("Unrecoverable error", { err });
 */

import winston from "winston";
import path from "path";
import fs from "fs";

// ── Custom levels ─────────────────────────────────────────────────────────────

const customLevels = {
  levels: {
    fatal:   0,
    error:   1,
    warn:    2,
    info:    3,
    http:    4,
    verbose: 5,
    debug:   6,
    trace:   7,
  },
  colors: {
    fatal:   "red bold",
    error:   "red",
    warn:    "yellow",
    info:    "green",
    http:    "magenta",
    verbose: "cyan",
    debug:   "blue",
    trace:   "white",
  },
};

winston.addColors(customLevels.colors);

// ── Log directory ─────────────────────────────────────────────────────────────

const LOG_DIR = process.env.LOG_DIR ?? path.join(process.cwd(), "logs");
fs.mkdirSync(LOG_DIR, { recursive: true });

// ── Formats ───────────────────────────────────────────────────────────────────

const consoleFormat = winston.format.combine(
  winston.format.colorize({ all: true }),
  winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss.SSS" }),
  winston.format.printf(({ timestamp, level, message, source, ...meta }) => {
    const src = source ? ` [${source}]` : "";
    const extra = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : "";
    return `${timestamp} | ${level}${src} — ${message}${extra}`;
  }),
);

const fileFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
);

// ── Transports ────────────────────────────────────────────────────────────────

const logLevel = (process.env.LOG_LEVEL ?? (process.env.NODE_ENV === "production" ? "info" : "debug")).toLowerCase();

const transports: winston.transport[] = [
  new winston.transports.Console({
    level: logLevel,
    format: consoleFormat,
  }),
  new winston.transports.File({
    filename: path.join(LOG_DIR, "narrateink.log"),
    level: "trace",
    format: fileFormat,
    maxsize: 10 * 1024 * 1024,   // 10 MB
    maxFiles: 7,
    tailable: true,
  }),
  new winston.transports.File({
    filename: path.join(LOG_DIR, "narrateink-errors.log"),
    level: "warn",
    format: fileFormat,
    maxsize: 10 * 1024 * 1024,
    maxFiles: 30,
    tailable: true,
  }),
];

// ── Optional: syslog ──────────────────────────────────────────────────────────

if (process.env.LOG_SYSLOG_HOST) {
  try {
    // Requires: npm install winston-syslog
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Syslog } = require("winston-syslog");
    transports.push(
      new Syslog({
        host: process.env.LOG_SYSLOG_HOST,
        port: parseInt(process.env.LOG_SYSLOG_PORT ?? "514", 10),
        protocol: "udp4",
        app_name: "narrateink",
        level: "warn",
      }),
    );
    console.log(`[logger] syslog transport active → ${process.env.LOG_SYSLOG_HOST}`);
  } catch {
    console.warn("[logger] LOG_SYSLOG_HOST set but winston-syslog not installed — run: npm install winston-syslog");
  }
}

// ── Optional: email ───────────────────────────────────────────────────────────

if (process.env.LOG_SMTP_HOST && process.env.LOG_SMTP_TO) {
  try {
    // Requires: npm install winston-mail
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Mail } = require("winston-mail");
    transports.push(
      new Mail({
        host: process.env.LOG_SMTP_HOST,
        port: parseInt(process.env.LOG_SMTP_PORT ?? "587", 10),
        username: process.env.LOG_SMTP_USER ?? "",
        password: process.env.LOG_SMTP_PASS ?? "",
        to: process.env.LOG_SMTP_TO,
        from: process.env.LOG_SMTP_FROM ?? process.env.LOG_SMTP_TO,
        subject: "[narrate.ink] {{level}}: {{message}}",
        level: "fatal",
        ssl: false,
      }),
    );
    console.log(`[logger] email transport active → ${process.env.LOG_SMTP_TO}`);
  } catch {
    console.warn("[logger] LOG_SMTP_HOST set but winston-mail not installed — run: npm install winston-mail");
  }
}

// ── Logger instance ───────────────────────────────────────────────────────────

export const logger = winston.createLogger({
  levels: customLevels.levels,
  transports,
  exitOnError: false,
});

// ── Typed helpers (avoids having to cast level everywhere) ────────────────────

type LogMeta = Record<string, unknown>;

export function logTrace(message: string, meta?: LogMeta)   { logger.log("trace",   message, meta); }
export function logDebug(message: string, meta?: LogMeta)   { logger.log("debug",   message, meta); }
export function logVerbose(message: string, meta?: LogMeta) { logger.log("verbose", message, meta); }
export function logHttp(message: string, meta?: LogMeta)    { logger.log("http",    message, meta); }
export function logInfo(message: string, meta?: LogMeta)    { logger.log("info",    message, meta); }
export function logWarn(message: string, meta?: LogMeta)    { logger.log("warn",    message, meta); }
export function logError(message: string, meta?: LogMeta)   { logger.log("error",   message, meta); }
export function logFatal(message: string, meta?: LogMeta)   { logger.log("fatal",   message, meta); }

logger.log("info", "narrate.ink server logger ready", {
  source: "logger",
  console_level: logLevel,
  log_dir: LOG_DIR,
});
