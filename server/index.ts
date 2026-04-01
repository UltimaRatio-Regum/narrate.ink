import "dotenv/config";
import express, { type Request, Response, NextFunction } from "express";
import helmet from "helmet";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { startPythonBackend } from "./python-backend";
import { setupAuth } from "./auth";
import { logger, logTrace, logInfo, logWarn, logError, logHttp } from "./logger";

const app = express();
const httpServer = createServer(app);

logTrace("Express app created", { source: "express" });

app.use(helmet({ contentSecurityPolicy: false }));
logTrace("Helmet middleware registered", { source: "express" });

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

/** Compatibility shim — keeps existing callers working unchanged. */
export function log(message: string, source = "express") {
  logInfo(message, { source });
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      const meta: Record<string, unknown> = {
        source: "http",
        method: req.method,
        path,
        status: res.statusCode,
        duration_ms: duration,
      };
      if (capturedJsonResponse && res.statusCode >= 400) {
        meta.response = capturedJsonResponse;
      }
      const logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (res.statusCode >= 500) {
        logError(logLine, meta);
      } else if (res.statusCode >= 400) {
        logWarn(logLine, meta);
      } else {
        logHttp(logLine, meta);
      }
    }
  });

  next();
});

(async () => {
  logTrace("Bootstrap sequence starting", { source: "express" });

  if (process.env.SKIP_PYTHON_SPAWN === "1") {
    logInfo("SKIP_PYTHON_SPAWN is set, assuming Python backend is managed externally", { source: "python" });
  } else {
    logTrace("Spawning Python FastAPI backend", { source: "python" });
    try {
      await startPythonBackend();
      logInfo("Python backend started successfully", { source: "python" });
    } catch (err) {
      logWarn(`Python backend failed to start: ${err}`, { source: "python" });
      logInfo("Continuing without Python backend", { source: "express" });
    }
  }

  logTrace("Registering express.json + urlencoded middleware", { source: "express" });
  app.use(express.json());
  app.use(express.urlencoded({ extended: false }));

  logTrace("Setting up auth", { source: "express" });
  await setupAuth(app);

  logTrace("Registering routes", { source: "express" });
  await registerRoutes(httpServer, app);

  app.use((err: any, _req: Request, res: Response, next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    logError("Internal Server Error", { source: "express", status, message, stack: err.stack });

    if (res.headersSent) {
      return next(err);
    }

    return res.status(status).json({ message });
  });

  if (process.env.NODE_ENV === "production") {
    logTrace("Serving static assets (production)", { source: "express" });
    serveStatic(app);
  } else {
    logTrace("Setting up Vite dev middleware", { source: "express" });
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      logInfo(`narrate.ink server listening on port ${port}`, { source: "express", port });
    },
  );
})();
