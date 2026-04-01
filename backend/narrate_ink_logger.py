"""
narrate_ink_logger.py — Application-wide logging configuration (loguru).

Log levels (lowest → highest severity):
  TRACE    (5)  — Extremely verbose: every startup step, every migration check,
                  function entry/exit during init.  First-run init emits heavily
                  at this level so the exact sequence is always reproducible.
  DEBUG   (10)  — Operational detail useful during development.
  INFO    (20)  — Normal milestones: server started, DB connected, admin seeded.
  SUCCESS (25)  — Explicit success confirmations (loguru built-in).
  WARNING (30)  — Recoverable issues: fallback to SQLite, orphaned records, etc.
  ERROR   (40)  — Operation failures that don't crash the process.
  CRITICAL(50)  — Fatal conditions; usually followed by process exit.

Sinks
─────
Always active:
  • Console  — coloured, human-readable.  Level controlled by LOG_LEVEL env var
               (default DEBUG in dev / INFO in production).
  • File     — logs/narrateink.log, JSON lines, rotated at 10 MB, kept 7 days.
               Always captures TRACE and above so nothing is lost.
  • File     — logs/narrateink-errors.log, JSON lines, ERROR and above only.

Optional (activated by environment variables — see comments below):
  • PostgreSQL — set LOG_POSTGRES_URL=postgresql://user:pass@host/db
  • MariaDB    — set LOG_MARIADB_DSN=mysql+mysqlconnector://user:pass@host/db
  • syslog-ng  — set LOG_SYSLOG_HOST=hostname  (default port 514 UDP)
  • Email      — set LOG_SMTP_HOST, LOG_SMTP_TO, LOG_SMTP_FROM

Interception
────────────
A stdlib logging.Handler bridge is installed so every existing
  logger = logging.getLogger(__name__)
  logger.info("...")
call across the codebase — plus uvicorn, SQLAlchemy, httpx, etc. — is routed
through loguru transparently.  No other file needs to change.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
import sys
from pathlib import Path

from loguru import logger


# ── tracecall decorator ────────────────────────────────────────────────────────

def _fmt_arg(name: str, value: object) -> str | None:
    """Return a single 'name=repr' string, or None to omit the parameter."""
    type_name = type(value).__name__

    # DB session — never useful in a trace line
    if type_name in ("Session", "scoped_session", "sessionmaker"):
        return None

    # FastAPI / Starlette Request
    if type_name == "Request" or (
        hasattr(value, "method") and hasattr(value, "url") and hasattr(value, "headers")
    ):
        return f"{name}={value.method} {value.url.path}"  # type: ignore[union-attr]

    # UploadFile
    if type_name == "UploadFile" or (
        hasattr(value, "filename") and hasattr(value, "read") and hasattr(value, "content_type")
    ):
        return f"{name}={getattr(value, 'filename', '?')!r}"

    # Raw bytes / bytearray — log size, not content
    if isinstance(value, (bytes, bytearray)):
        return f"{name}={len(value)} bytes"

    # Lists, tuples, sets — log count
    if isinstance(value, (list, tuple, set, frozenset)):
        return f"{name}=[{len(value)} items]"  # type: ignore[arg-type]

    # Dicts — log key count
    if isinstance(value, dict):
        return f"{name}={{{len(value)} keys}}"

    # Long strings — truncate
    if isinstance(value, str) and len(value) > 120:
        return f"{name}={value[:120]!r}…"

    return f"{name}={value!r}"


def tracecall(func):
    """Decorator: emit a TRACE log on every call with the function name and
    all bound arguments (formatted for readability).  Handles both regular
    and async functions transparently."""

    sig = inspect.signature(func)

    def _build_msg(*args, **kwargs) -> str:
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            parts = [
                fmt
                for name, val in bound.arguments.items()
                if (fmt := _fmt_arg(name, val)) is not None
            ]
            args_str = ", ".join(parts)
        except Exception:
            args_str = "…"
        return f"{func.__qualname__}({args_str})"

    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def _async_wrapper(*args, **kwargs):
            logger.trace(_build_msg(*args, **kwargs))
            return await func(*args, **kwargs)
        return _async_wrapper

    @functools.wraps(func)
    def _sync_wrapper(*args, **kwargs):
        logger.trace(_build_msg(*args, **kwargs))
        return func(*args, **kwargs)

    return _sync_wrapper


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_dir() -> Path:
    p = Path(os.environ.get("LOG_DIR", "logs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


class _StdlibInterceptHandler(logging.Handler):
    """Bridge: route every stdlib logging record into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk the call stack to find the true caller (skip logging internals).
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure loguru sinks and intercept stdlib logging.  Call once at startup."""

    log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    log_dir   = _log_dir()

    # Remove loguru's default stderr handler before adding our own.
    logger.remove()

    # ── Console sink ──────────────────────────────────────────────────────────
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=True,
    )

    # ── Full log file (JSON, every level, non-blocking) ───────────────────────
    logger.add(
        log_dir / "narrateink.log",
        level="TRACE",
        rotation="10 MB",
        retention="7 days",
        compression="gz",
        serialize=True,     # JSON lines — easy to ingest into any log system
        backtrace=True,
        diagnose=False,     # keep sensitive values out of serialised output
        enqueue=True,       # write in a background thread
    )

    # ── Error log file (human-readable, ERROR and above) ─────────────────────
    logger.add(
        log_dir / "narrateink-errors.log",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} — {message}\n{exception}",
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    # ── Optional sinks ─────────────────────────────────────────────────────────
    if pg_url := os.environ.get("LOG_POSTGRES_URL"):
        _add_postgres_sink(pg_url)

    if mariadb_dsn := os.environ.get("LOG_MARIADB_DSN"):
        _add_mariadb_sink(mariadb_dsn)

    if syslog_host := os.environ.get("LOG_SYSLOG_HOST"):
        _add_syslog_sink(syslog_host, int(os.environ.get("LOG_SYSLOG_PORT", "514")))

    if os.environ.get("LOG_SMTP_HOST") and os.environ.get("LOG_SMTP_TO"):
        _add_email_sink()

    # ── Intercept stdlib logging ───────────────────────────────────────────────
    # force=True replaces any existing basicConfig handlers.
    logging.basicConfig(handlers=[_StdlibInterceptHandler()], level=0, force=True)
    # Remove propagation from noisy libraries so they only go through our handler.
    for lib_name in (
        "uvicorn", "uvicorn.access", "uvicorn.error",
        "sqlalchemy.engine", "sqlalchemy.pool",
        "httpx", "asyncio", "multipart",
    ):
        lib_logger = logging.getLogger(lib_name)
        lib_logger.handlers  = [_StdlibInterceptHandler()]
        lib_logger.propagate = False

    logger.info(
        "narrate.ink logging ready — console_level={} log_dir={}",
        log_level, log_dir.resolve(),
    )


# ── Optional sink implementations ─────────────────────────────────────────────

def _add_postgres_sink(db_url: str) -> None:
    """
    Log WARNING and above to a PostgreSQL table.

    Table is auto-created:
        CREATE TABLE IF NOT EXISTS app_logs (
            id          SERIAL PRIMARY KEY,
            logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            level       VARCHAR(10)  NOT NULL,
            logger_name TEXT,
            message     TEXT         NOT NULL,
            record_json JSONB
        );

    Requires: psycopg2-binary (already in requirements.txt).
    Activate: LOG_POSTGRES_URL=postgresql://user:pass@host:5432/dbname
    """
    import psycopg2  # type: ignore

    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS app_logs (
        id          SERIAL PRIMARY KEY,
        logged_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        level       VARCHAR(10)  NOT NULL,
        logger_name TEXT,
        message     TEXT         NOT NULL,
        record_json JSONB
    );
    """

    def _sink(message) -> None:
        record = message.record
        try:
            conn = psycopg2.connect(db_url)
            with conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app_logs (level, logger_name, message, record_json) "
                    "VALUES (%s, %s, %s, %s::jsonb)",
                    (record["level"].name, record["name"], record["message"], str(message)),
                )
            conn.close()
        except Exception as exc:
            print(f"[narrate_ink_logger] postgres sink error: {exc}", file=sys.stderr)

    try:
        conn = psycopg2.connect(db_url)
        with conn, conn.cursor() as cur:
            cur.execute(CREATE_TABLE)
        conn.close()
        logger.add(_sink, level="WARNING", enqueue=True)
        logger.debug("PostgreSQL log sink active — {}", db_url.split("@")[-1])
    except Exception as exc:
        logger.warning("Could not initialise PostgreSQL log sink: {}", exc)


def _add_mariadb_sink(dsn: str) -> None:
    """
    Log WARNING and above to a MariaDB/MySQL table.

    Requires: mysql-connector-python  (pip install mysql-connector-python)
    Activate: LOG_MARIADB_DSN=user:pass@host:3306/dbname
    """
    try:
        import mysql.connector  # type: ignore
    except ImportError:
        logger.warning(
            "LOG_MARIADB_DSN is set but mysql-connector-python is not installed — "
            "run `pip install mysql-connector-python` to enable the MariaDB log sink"
        )
        return

    # DSN format: user:pass@host:port/dbname
    import re
    m = re.match(r"(.+):(.+)@(.+):(\d+)/(.+)", dsn)
    if not m:
        logger.warning("LOG_MARIADB_DSN format invalid — expected user:pass@host:port/dbname")
        return
    user, password, host, port, database = m.groups()

    def _sink(message) -> None:
        record = message.record
        try:
            conn = mysql.connector.connect(
                user=user, password=password, host=host, port=int(port), database=database
            )
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO app_logs (level, logger_name, message) VALUES (%s, %s, %s)",
                (record["level"].name, record["name"], record["message"]),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            print(f"[narrate_ink_logger] mariadb sink error: {exc}", file=sys.stderr)

    logger.add(_sink, level="WARNING", enqueue=True)
    logger.debug("MariaDB log sink active — {}:{}/{}", host, port, database)


def _add_syslog_sink(host: str, port: int) -> None:
    """
    Forward WARNING and above to a syslog-ng (or any syslog) server over UDP.

    Activate: LOG_SYSLOG_HOST=hostname  (optional: LOG_SYSLOG_PORT=514)
    """
    import logging.handlers as _lh

    handler = _lh.SysLogHandler(address=(host, port))
    handler.setLevel(logging.WARNING)

    def _sink(message) -> None:
        record = message.record
        lvl = getattr(logging, record["level"].name, logging.WARNING)
        handler.handle(logging.makeLogRecord({"levelno": lvl, "msg": record["message"]}))

    logger.add(_sink, level="WARNING", enqueue=True)
    logger.debug("syslog-ng sink active — {}:{}", host, port)


def _add_email_sink() -> None:
    """
    Send CRITICAL-level events by email.

    Activate:
      LOG_SMTP_HOST=smtp.example.com
      LOG_SMTP_PORT=587            (default)
      LOG_SMTP_USER=user@example.com
      LOG_SMTP_PASS=secret
      LOG_SMTP_FROM=alerts@example.com
      LOG_SMTP_TO=oncall@example.com
    """
    import smtplib
    from email.mime.text import MIMEText

    smtp_host = os.environ["LOG_SMTP_HOST"]
    smtp_port = int(os.environ.get("LOG_SMTP_PORT", "587"))
    smtp_user = os.environ.get("LOG_SMTP_USER", "")
    smtp_pass = os.environ.get("LOG_SMTP_PASS", "")
    smtp_from = os.environ["LOG_SMTP_FROM"]
    smtp_to   = os.environ["LOG_SMTP_TO"]

    def _sink(message) -> None:
        record = message.record
        msg = MIMEText(str(message))
        msg["Subject"] = f"[narrate.ink] {record['level'].name}: {record['message'][:80]}"
        msg["From"]    = smtp_from
        msg["To"]      = smtp_to
        try:
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                if smtp_user:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_from, [smtp_to], msg.as_string())
        except Exception as exc:
            print(f"[narrate_ink_logger] email sink error: {exc}", file=sys.stderr)

    logger.add(_sink, level="CRITICAL", enqueue=True)
    logger.debug("Email log sink active — CRITICAL → {}", smtp_to)
