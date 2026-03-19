import { spawn, ChildProcess } from "child_process";
import { log } from "./index";
import path from "path";

let pythonProcess: ChildProcess | null = null;

export async function startPythonBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    const backendDir = path.join(process.cwd(), "backend");
    const venvPython = path.join(process.cwd(), ".venv", "bin", "python");
    const pythonBin = require("fs").existsSync(venvPython) ? venvPython : "python";

    log("Starting Python FastAPI backend...", "python");

    pythonProcess = spawn(pythonBin, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], {
      cwd: backendDir,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });
    
    pythonProcess.stdout?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) {
        log(output, "python");
      }
    });
    
    pythonProcess.stderr?.on("data", (data) => {
      const output = data.toString().trim();
      if (output) {
        log(output, "python-err");
      }
    });
    
    pythonProcess.on("error", (err) => {
      log(`Failed to start Python backend: ${err.message}`, "python-err");
      reject(err);
    });
    
    pythonProcess.on("exit", (code) => {
      log(`Python backend exited with code ${code}`, "python");
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
    log("Stopping Python backend...", "python");
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
