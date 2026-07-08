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

async function sendWebhook(projectId: string | undefined, payload: any) {
  // Only send webhooks if projectId is valid and not the default demo-project
  if (!projectId || projectId === 'demo-project') return;
  try {
    const response = await fetch(`http://localhost:8000/api/v1/projects/${projectId}/executions/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      console.error(`[Webhook] Failed to send webhook event ${payload.event}: ${response.statusText}`);
    }
  } catch (err) {
    console.error(`[Webhook] Error sending webhook event ${payload.event}:`, err);
  }
}

export class ExecutionEngine {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private screenshotInterval: NodeJS.Timeout | null = null;
  private isPaused = false;

  async validateScript(script: string): Promise<{ valid: boolean; error?: string }> {
    try {
      const dangerousPatterns = [
        /require\s*\(\s*['"](fs|child_process|os|path)['"]/,
        /import\s+.*\s+from\s+['"](fs|child_process|os|path)['"]/,
        /(?<![\$a-zA-Z0-9_])eval\s*\(/,
        /Function\s*\(/,
      ];

      for (const pattern of dangerousPatterns) {
        if (pattern.test(script)) {
          return { valid: false, error: 'Script contains dangerous patterns' };
        }
      }

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

    // Get browser and metadata from execution
    const execution = executionQueue.getExecution(executionId);
    if (!execution) throw new Error('Execution not found');

    const projectId = execution.metadata.projectId;
    const testCaseId = execution.metadata.testCaseIds?.[0];
    const browserType = execution.metadata.browser || 'chromium';

    try {
      // 1. Trigger Started Webhook
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'started',
        status: 'running'
      });

      // Create artifact directory
      await fs.mkdir(artifactDir, { recursive: true });

      // Create subdirectories
      const screenshotDir = path.join(artifactDir, 'screenshots');
      const videoDir = path.join(artifactDir, 'video');
      const traceDir = path.join(artifactDir, 'trace');

      await fs.mkdir(screenshotDir, { recursive: true });
      if (recordVideo) await fs.mkdir(videoDir, { recursive: true });
      if (recordTrace) await fs.mkdir(traceDir, { recursive: true });

      // Launch browser
      executionQueue.addTimelineEvent(executionId, 'Launching browser', 'info');
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'updated',
        status: 'running',
        timeline_event: { event: 'Launching browser', type: 'info' }
      });

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
        this.browser = browser;
      } catch (launchError: any) {
        executionQueue.addTimelineEvent(executionId, `Browser launch failed: ${launchError.message}`, 'error');
        await sendWebhook(projectId, {
          execution_id: executionId,
          test_case_id: testCaseId,
          event: 'updated',
          status: 'running',
          timeline_event: { event: `Browser launch failed: ${launchError.message}`, type: 'error' }
        });
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
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'updated',
        status: 'running',
        timeline_event: { event: 'Browser opened successfully', type: 'success' }
      });

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
        const text = `[${msg.type()}] ${msg.text()}`;
        executionQueue.addConsole(executionId, text);
        sendWebhook(projectId, {
          execution_id: executionId,
          test_case_id: testCaseId,
          event: 'updated',
          status: 'running',
          log_line: text
        });
      });

      // Setup error listener
      page.on('pageerror', (err) => {
        const text = `[error] ${err.message}`;
        executionQueue.addConsole(executionId, text);
        sendWebhook(projectId, {
          execution_id: executionId,
          test_case_id: testCaseId,
          event: 'updated',
          status: 'running',
          log_line: text
        });
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

          // Webhook update for screenshot capture
          await sendWebhook(projectId, {
            execution_id: executionId,
            test_case_id: testCaseId,
            event: 'updated',
            status: 'running',
            live_screenshot: path.join(artifactDir, 'screenshots', filename)
          });

          return filepath;
        },
        addLog: (message: string) => {
          executionQueue.addLog(executionId, message);
          sendWebhook(projectId, {
            execution_id: executionId,
            test_case_id: testCaseId,
            event: 'updated',
            status: 'running',
            log_line: message
          });
        },
        addTimelineEvent: (event: string, type?: string) => {
          executionQueue.addTimelineEvent(executionId, event, type as any);
          sendWebhook(projectId, {
            execution_id: executionId,
            test_case_id: testCaseId,
            event: 'updated',
            status: 'running',
            timeline_event: { event, type }
          });
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
      
      const finalExecution = executionQueue.getExecution(executionId);
      const screenshotFilename = finalExecution?.artifacts.screenshots.length 
        ? finalExecution.artifacts.screenshots[finalExecution.artifacts.screenshots.length - 1] 
        : null;

      // 3. Trigger Completed Webhook
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'completed',
        status: 'passed',
        duration_seconds: finalExecution?.metadata.duration || 0,
        screenshot_path: screenshotFilename ? path.join(artifactDir, 'screenshots', screenshotFilename) : null,
        video_path: finalExecution?.artifacts.video ? path.join(artifactDir, 'video', finalExecution.artifacts.video) : null,
        trace_path: finalExecution?.artifacts.trace ? path.join(artifactDir, 'trace', finalExecution.artifacts.trace) : null,
        error_message: null,
        timeline: finalExecution?.timeline || [],
        screenshots: finalExecution?.artifacts.screenshots || []
      });

      wsManager.broadcast({
        type: 'complete',
        executionId,
        data: {
          status: 'completed',
          duration: finalExecution?.metadata.duration,
        },
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      executionQueue.setError(executionId, error.message);
      
      const finalExecution = executionQueue.getExecution(executionId);
      const screenshotFilename = finalExecution?.artifacts.screenshots.length 
        ? finalExecution.artifacts.screenshots[finalExecution.artifacts.screenshots.length - 1] 
        : null;

      // 3. Trigger Completed Webhook (failed run)
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'completed',
        status: 'failed',
        duration_seconds: finalExecution?.metadata.duration || 0,
        screenshot_path: screenshotFilename ? path.join(artifactDir, 'screenshots', screenshotFilename) : null,
        video_path: finalExecution?.artifacts.video ? path.join(artifactDir, 'video', finalExecution.artifacts.video) : null,
        trace_path: finalExecution?.artifacts.trace ? path.join(artifactDir, 'trace', finalExecution.artifacts.trace) : null,
        error_message: error.message,
        timeline: finalExecution?.timeline || [],
        screenshots: finalExecution?.artifacts.screenshots || []
      });

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
    ${screenshots.map((file) => `<img src="screenshot/${file}" alt="${file}" />`).join('')}
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
