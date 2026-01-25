import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { createProxyMiddleware } from "http-proxy-middleware";

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://127.0.0.1:8000";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  const apiProxy = createProxyMiddleware({
    target: PYTHON_BACKEND_URL,
    changeOrigin: true,
    pathRewrite: undefined, // Don't rewrite paths - keep /api prefix
    logger: console,
    on: {
      error: (err, req, res) => {
        console.error('Proxy error:', err.message);
        if (res && 'writeHead' in res && !res.headersSent) {
          (res as any).writeHead(502, { 'Content-Type': 'application/json' });
          (res as any).end(JSON.stringify({ 
            error: 'Backend service unavailable',
            message: 'Please ensure the Python backend is running on port 8000'
          }));
        }
      },
    },
  });

  app.use('/api', apiProxy);
  
  app.use('/uploads', createProxyMiddleware({
    target: PYTHON_BACKEND_URL,
    changeOrigin: true,
  }));

  return httpServer;
}
