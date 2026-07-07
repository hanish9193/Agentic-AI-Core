import { chromium, firefox, webkit, Browser, Page } from 'playwright';
import { executionQueue } from './execution-queue';
import { wsManager } from './websocket-manager';
import * as fs from 'fs/promises';
import * as path from 'path';

interface ExecutionRunnerOptions {
  executionId: string;
  script: string;
  artifactDir: string;
  recordVideo?: boolean;
  recordTrace?: boolean;
}

export class ExecutionEngine {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private screenshotInterval: NodeJS.Timeout | null = null;
  private isPaused = false;

  async validateScript(script: string): Promise<{ valid: boolean; error?: string }> {
    try {
      // Basic validation - check for malicious patterns
      const dangerousPatterns = [
        /require\s*\(\s*['"](fs|child_process|os|path)['"]/,
        /import\s+.*\s+from\s+['"](fs|child_process|os|path)['"]/,
        /eval\s*\(/,
        /Function\s*\(/,
      ];

      for (const pattern of dangerousPatterns) {
        if (pattern.test(script)) {
          return { valid: false, error: 'Script contains dangerous patterns' };
        }
      }

      // Try to parse as valid JavaScript by wrapping in async function
      // This allows top-level await in user scripts
      const wrappedScript = `
        return (async ({ page, browser, context, screenshot, addLog, addTimelineEvent }) => {
          ${script}
        })
      `;
      new Function(wrappedScript);
      return { valid: true };
    } catch (error: any) {
      return { valid: false, error: error.message };
    }
  }

  async run(options: ExecutionRunnerOptions): Promise<void> {
    const { executionId, script, artifactDir, recordVideo = true, recordTrace = true } = options;

    try {
      // Create artifact directory
      await fs.mkdir(artifactDir, { recursive: true });

      // Create subdirectories
      const screenshotDir = path.join(artifactDir, 'screenshots');
      const videoDir = path.join(artifactDir, 'video');
      const traceDir = path.join(artifactDir, 'trace');

      await fs.mkdir(screenshotDir, { recursive: true });
      if (recordVideo) await fs.mkdir(videoDir, { recursive: true });
      if (recordTrace) await fs.mkdir(traceDir, { recursive: true });

      // Get browser from execution metadata
      const execution = executionQueue.getExecution(executionId);
      if (!execution) throw new Error('Execution not found');

      const browserType = execution.metadata.browser || 'chromium';

      // Launch browser
      executionQueue.addTimelineEvent(executionId, 'Launching browser', 'info');
      wsManager.broadcast({
        type: 'update',
        executionId,
        data: { status: 'launching_browser' },
        timestamp: new Date().toISOString(),
      });

      const launchOptions: any = {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
      };

      // In sandboxed environments, only chromium works
      let browser;
      try {
        browser = await chromium.launch(launchOptions);
      } catch (launchError: any) {
        executionQueue.addTimelineEvent(executionId, `Browser launch failed: ${launchError.message}`, 'error');
        throw launchError;
      }

      // Create context and page
      const context = recordTrace
        ? await browser.newContext({ recordVideo: recordVideo ? { dir: videoDir } : undefined })
        : await browser.newContext();

      if (recordTrace) {
        await context.tracing.start({ screenshots: true, snapshots: true });
      }

      const page = await context.newPage();
      this.page = page;

      executionQueue.addTimelineEvent(executionId, 'Browser opened successfully', 'success');
      wsManager.broadcast({
        type: 'status',
        executionId,
        data: { status: 'running', currentEvent: 'Browser opened' },
        timestamp: new Date().toISOString(),
      });

      // Start screenshot capture
      this.startScreenshotCapture(executionId, page, screenshotDir);

      // Setup console listener
      page.on('console', (msg) => {
        executionQueue.addConsole(executionId, `[${msg.type()}] ${msg.text()}`);
      });

      // Setup error listener
      page.on('pageerror', (error) => {
        executionQueue.addConsole(executionId, `[error] ${error.message}`);
      });

      // Create execution context with page utilities
      const executionContext = {
        page,
        browser,
        context,
        screenshot: async (name?: string) => {
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
          const filename = `${name || 'screenshot'}-${timestamp}.png`;
          const filepath = path.join(screenshotDir, filename);
          await page.screenshot({ path: filepath });
          executionQueue.addScreenshot(executionId, filename);
          return filepath;
        },
        addLog: (message: string) => {
          executionQueue.addLog(executionId, message);
        },
        addTimelineEvent: (event: string, type?: string) => {
          executionQueue.addTimelineEvent(executionId, event, type as any);
        },
      };

      // Execute user script with context - wrap in async function to support top-level await
      const wrappedScript = `
        return (async ({ page, browser, context, screenshot, addLog, addTimelineEvent }) => {
          ${script}
        })
      `;
      const userFunction = new Function(wrappedScript);
      const asyncFunc = userFunction();
      await asyncFunc(executionContext);

      // Save trace
      if (recordTrace) {
        const tracePath = path.join(traceDir, 'trace.zip');
        await context.tracing.stop({ path: tracePath });
        executionQueue.setArtifact(executionId, 'trace', 'trace.zip');
      }

      // Generate HTML report
      await this.generateHTMLReport(executionId, artifactDir, screenshotDir);

      // Cleanup
      await page.close();
      await context.close();
      await browser.close();

      executionQueue.completeExecution(executionId);
      wsManager.broadcast({
        type: 'complete',
        executionId,
        data: {
          status: 'completed',
          duration: executionQueue.getExecution(executionId)?.metadata.duration,
        },
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      executionQueue.setError(executionId, error.message);
      wsManager.broadcast({
        type: 'error',
        executionId,
        data: { error: error.message },
        timestamp: new Date().toISOString(),
      });

      // Cleanup
      if (this.page) await this.page.close().catch(() => {});
      if (this.browser) await this.browser.close().catch(() => {});
    } finally {
      if (this.screenshotInterval) clearInterval(this.screenshotInterval);
    }
  }

  private startScreenshotCapture(executionId: string, page: Page, screenshotDir: string): void {
    let captureCount = 0;
    this.screenshotInterval = setInterval(async () => {
      if (this.isPaused) return;

      try {
        const timestamp = String(captureCount).padStart(5, '0');
        const filename = `live-${timestamp}.png`;
        const filepath = path.join(screenshotDir, filename);

        await page.screenshot({ path: filepath });
        captureCount++;

        wsManager.broadcast({
          type: 'screenshot',
          executionId,
          data: { filename, url: `/api/artifacts/${executionId}/screenshot/${filename}` },
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        // Page might be closed, ignore
      }
    }, 200); // Capture every 200ms
  }

  private async generateHTMLReport(
    executionId: string,
    artifactDir: string,
    screenshotDir: string
  ): Promise<void> {
    try {
      const execution = executionQueue.getExecution(executionId);
      if (!execution) return;

      const screenshots = await fs.readdir(screenshotDir).catch(() => []);

      const html = `<!DOCTYPE html>
<html>
<head>
  <title>Execution Report - ${executionId}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
    .header { background: #2d3748; color: white; padding: 20px; border-radius: 8px; }
    .section { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .timeline { list-style: none; padding: 0; }
    .timeline li { padding: 10px; border-left: 3px solid #e2e8f0; margin-left: 20px; position: relative; }
    .timeline li.success { border-left-color: #48bb78; }
    .timeline li.error { border-left-color: #f56565; }
    .timeline li.info { border-left-color: #4299e1; }
    .time { color: #718096; font-size: 0.9em; }
    img { max-width: 100%; border-radius: 4px; margin: 10px 0; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Execution Report</h1>
    <p>ID: ${executionId}</p>
    <p>Status: ${execution.metadata.status}</p>
    <p>Duration: ${execution.metadata.duration?.toFixed(2)}s</p>
  </div>

  <div class="section">
    <h2>Timeline</h2>
    <ul class="timeline">
      ${execution.timeline
        .map(
          (event) => `
        <li class="${event.type}">
          <span class="time">${event.timestamp.split('T')[1].split('.')[0]} (${event.time.toFixed(2)}s)</span>
          <strong>${event.event}</strong>
          ${event.details ? `<p>${event.details}</p>` : ''}
        </li>
      `
        )
        .join('')}
    </ul>
  </div>

  <div class="section">
    <h2>Screenshots (${screenshots.length})</h2>
    ${screenshots.map((file) => `<img src="screenshots/${file}" alt="${file}" />`).join('')}
  </div>
</body>
</html>`;

      const reportPath = path.join(artifactDir, 'report.html');
      await fs.writeFile(reportPath, html);
      executionQueue.setArtifact(executionId, 'htmlReport', 'report.html');
    } catch (error) {
      console.error('[ExecutionEngine] Error generating HTML report:', error);
    }
  }

  pause(): void {
    this.isPaused = true;
  }

  resume(): void {
    this.isPaused = false;
  }

  async stop(): Promise<void> {
    if (this.screenshotInterval) clearInterval(this.screenshotInterval);
    if (this.page) await this.page.close().catch(() => {});
    if (this.browser) await this.browser.close().catch(() => {});
  }
}
