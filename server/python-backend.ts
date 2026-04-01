import { spawn, ChildProcess } from "child_process";
import { log } from "./index";
import { logTrace, logInfo, logWarn, logError } from "./logger";
import path from "path";

let pythonProcess: ChildProcess | null = null;

export async function startPythonBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    const backendDir = path.join(process.cwd(), "backend");
    const venvPython = path.join(process.cwd(), ".venv", "bin", "python");
    const pythonBin = require("fs").existsSync(venvPython) ? venvPython : "python";

    logTrace("Resolved Python binary", { source: "python", pythonBin, backendDir });
    logInfo("Starting Python FastAPI backend...", { source: "python" });

    pythonProcess = spawn(pythonBin, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], {
      cwd: backendDir,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });

    pythonProcess.stdout?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) {
        logInfo(output, { source: "python" });
      }
    });

    pythonProcess.stderr?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) {
        // Python logs INFO/DEBUG to stderr via uvicorn — route appropriately
        if (/error|exception|traceback/i.test(output)) {
          logError(output, { source: "python" });
        } else if (/warn/i.test(output)) {
          logWarn(output, { source: "python" });
        } else {
          logInfo(output, { source: "python" });
        }
      }
    });

    pythonProcess.on("error", (err) => {
      logError(`Failed to start Python backend: ${err.message}`, { source: "python", err: err.message });
      reject(err);
    });

    pythonProcess.on("exit", (code) => {
      if (code === 0 || code === null) {
        logInfo(`Python backend exited with code ${code}`, { source: "python", code });
      } else {
        logWarn(`Python backend exited with code ${code}`, { source: "python", code });
      }
      pythonProcess = null;
    });
    
    // Wait for the backend to be ready
    const checkHealth = async (retries = 20): Promise<boolean> => {
      for (let i = 0; i < retries; i++) {
        try {
          const response = await fetch("http://127.0.0.1:8000/health");
          if (response.ok) {
            log("Python backend is ready", "python");
            return true;
          }
        } catch {
          // Backend not ready yet
        }
        await new Promise((r) => setTimeout(r, 500));
      }
      return false;
    };
    
    checkHealth().then((ready) => {
      if (ready) {
        resolve();
      } else {
        reject(new Error("Python backend failed to start"));
      }
    });
  });
}

export function stopPythonBackend(): void {
  if (pythonProcess) {
    logInfo("Stopping Python backend...", { source: "python" });
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// Cleanup on process exit
process.on("exit", stopPythonBackend);
process.on("SIGINT", () => {
  stopPythonBackend();
  process.exit();
});
process.on("SIGTERM", () => {
  stopPythonBackend();
  process.exit();
});
