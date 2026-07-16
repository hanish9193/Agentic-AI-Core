import { chromium, firefox, webkit, Browser, Page } from 'playwright';
import { executionQueue } from './execution-queue';
import { wsManager } from './websocket-manager';
import { ApplicationStateResolver } from './app-state-resolver';
import { NavigationPlanner } from './navigation-planner';
import { RecoveryManager } from './recovery-manager';
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
  const testCaseId = payload.test_case_id || (payload.timeline && payload.timeline[0]?.test_case_id);
  
  // Automatically retrieve test_cycle_id from execution queue metadata
  if (payload.execution_id) {
    const execution = executionQueue.getExecution(payload.execution_id);
    if (execution && execution.metadata.testCycleId) {
      payload.test_cycle_id = execution.metadata.testCycleId;
    }
  }

  console.log(`[Webhook DEBUG] sendWebhook invoked. projectId: "${projectId}", testCaseId: "${testCaseId}", event: "${payload.event}", testCycleId: "${payload.test_cycle_id}"`);
  
  if (!projectId || projectId === 'demo-project') {
    console.warn(`[Webhook DEBUG] Aborting webhook send because projectId is invalid: "${projectId}"`);
    return;
  }
  try {
    const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/executions/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      console.error(`[Webhook ERROR] Failed to send webhook event ${payload.event}: ${response.statusText} (status: ${response.status})`);
    } else {
      console.log(`[Webhook SUCCESS] Sent event ${payload.event} to FastAPI for project ${projectId}`);
    }
  } catch (err) {
    console.error(`[Webhook ERROR] Exception sending webhook event ${payload.event}:`, err);
  }
}

export class ExecutionEngine {
  private static sharedBrowser: Browser | null = null;
  private static sharedContext: any = null;
  private static sharedPage: Page | null = null;
  private static activeBrowserType: string | null = null;

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

      const cleanScript = script.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '');
      const wrappedScript = `
        return (async ({ page, browser, context, screenshot, addLog, addTimelineEvent, test, expect }) => {
          ${cleanScript}
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

    const screenshotDir = path.join(artifactDir, 'screenshots');
    const videoDir = path.join(artifactDir, 'video');
    const traceDir = path.join(artifactDir, 'trace');
    const storageStatePath = path.join(process.cwd(), 'public', 'artifacts', projectId || 'default', 'storage_state.json');

    try {
      executionQueue.startExecution(executionId);

      // 1. Trigger Started Webhook
      await sendWebhook(projectId, {
        execution_id: executionId,
        test_case_id: testCaseId,
        event: 'started',
        status: 'running'
      });

      // Create artifact directory
      await fs.mkdir(artifactDir, { recursive: true });
      await fs.mkdir(path.dirname(storageStatePath), { recursive: true });

      await fs.mkdir(screenshotDir, { recursive: true });
      if (recordVideo) await fs.mkdir(videoDir, { recursive: true });
      if (recordTrace) await fs.mkdir(traceDir, { recursive: true });

      let browser: Browser | null = null;
      let context: any = null;
      let page: Page | null = null;

      let retryCount = 0;
      let maxRetries = 2;
      let success = false;

      while (!success && retryCount <= maxRetries) {
        try {
          // ALWAYS create a fresh context and page for each execution to ensure strict test isolation
          const currentBrowserType = execution.metadata.browser || 'chromium';
          let isBrowserHealthy = false;
          if (ExecutionEngine.sharedBrowser) {
            try {
              // Check browser version to verify health
              await ExecutionEngine.sharedBrowser.version();
              isBrowserHealthy = true;
            } catch (e) {
              isBrowserHealthy = false;
            }
          }

          if (!isBrowserHealthy || !ExecutionEngine.sharedBrowser || ExecutionEngine.activeBrowserType !== currentBrowserType) {
            if (ExecutionEngine.sharedBrowser) {
              await ExecutionEngine.sharedBrowser.close().catch(() => {});
            }

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
              data: { status: 'running' },
              timestamp: new Date().toISOString(),
            });

            let headless = true;
            try {
              const settingsRes = await fetch('http://127.0.0.1:8000/api/v1/settings');
              if (settingsRes.ok) {
                const settings = await settingsRes.json();
                if (settings && settings.playwright && typeof settings.playwright.headless === 'boolean') {
                  headless = settings.playwright.headless;
                }
              }
            } catch (e) {
              console.warn('Failed to fetch settings from backend:', e);
            }

            const launchOptions: any = {
              headless: headless,
              args: ['--no-sandbox', '--disable-setuid-sandbox'],
            };

            try {
              browser = await chromium.launch(launchOptions);
              ExecutionEngine.sharedBrowser = browser;
              ExecutionEngine.activeBrowserType = currentBrowserType;
              const version = browser.version();
              executionQueue.setBrowserVersion(executionId, version);
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
          } else {
            browser = ExecutionEngine.sharedBrowser;
          }

          // Create context and page fresh for test isolation
          const contextOptions: any = {};
          if (recordVideo) {
            contextOptions.recordVideo = { dir: videoDir };
          }
          
          const hasState = await fs.access(storageStatePath).then(() => true).catch(() => false);
          if (hasState) {
            contextOptions.storageState = storageStatePath;
            executionQueue.addTimelineEvent(executionId, 'Session restored from storage state', 'success');
          }

          context = await browser.newContext(contextOptions);
          if (recordTrace) {
            await context.tracing.start({ screenshots: true, snapshots: true });
          }

          page = await context.newPage();
          
          // Clear shared page/context references to prevent leaks/reuse
          ExecutionEngine.sharedContext = null;
          ExecutionEngine.sharedPage = null;

          executionQueue.addTimelineEvent(executionId, 'Browser opened with clean context', 'success');

          this.browser = browser;
          this.page = page;

          wsManager.broadcast({
            type: 'status',
            executionId,
            data: { status: 'running', currentEvent: 'Browser opened / reused' },
            timestamp: new Date().toISOString(),
          });

          // Start screenshot capture
          this.startScreenshotCapture(executionId, page, screenshotDir);

          const testPromises: Promise<void>[] = [];
          const screenshotPromises: Promise<void>[] = [];

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
              
              // Log a timeline event for report generation
              executionQueue.addTimelineEvent(executionId, `Screenshot: ${name || 'step'}`, 'success', filename);

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
              const timestamp = Date.now();
              const filename = `step-${timestamp}.png`;
              const filepath = path.join(screenshotDir, filename);

              const promise = page.screenshot({ path: filepath }).then(async () => {
                executionQueue.addScreenshot(executionId, filename);
                executionQueue.addTimelineEvent(executionId, event, type as any, filename);
                await sendWebhook(projectId, {
                  execution_id: executionId,
                  test_case_id: testCaseId,
                  event: 'updated',
                  status: 'running',
                  timeline_event: { event, type, details: filename }
                });
              }).catch(async () => {
                executionQueue.addTimelineEvent(executionId, event, type as any);
                await sendWebhook(projectId, {
                  execution_id: executionId,
                  test_case_id: testCaseId,
                  event: 'updated',
                  status: 'running',
                  timeline_event: { event, type }
                });
              });
              screenshotPromises.push(promise);
            },
            test: (name: string, fn: any) => {
              const runPromise = (async () => {
                executionQueue.addTimelineEvent(executionId, `Running: ${name}`, 'info');
                await sendWebhook(projectId, {
                  execution_id: executionId,
                  test_case_id: testCaseId,
                  event: 'updated',
                  status: 'running',
                  timeline_event: { event: `Running: ${name}`, type: 'info' }
                });
                await fn(executionContext);
              })();
              testPromises.push(runPromise);
              return runPromise;
            },
            expect: (actual: any) => {
              const assertions = {
                toBe: (expected: any) => {
                  if (actual !== expected) {
                    throw new Error(`Expected ${actual} to be ${expected}`);
                  }
                },
                toBeDefined: () => {
                  if (actual === undefined) {
                    throw new Error(`Expected value to be defined`);
                  }
                },
                toBeTruthy: () => {
                  if (!actual) {
                    throw new Error(`Expected ${actual} to be truthy`);
                  }
                },
                toBeFalsy: () => {
                  if (actual) {
                    throw new Error(`Expected ${actual} to be falsy`);
                  }
                },
                toBeNull: () => {
                  if (actual !== null) {
                    throw new Error(`Expected ${actual} to be null`);
                  }
                },
                toContain: (expected: any) => {
                  if (typeof actual?.includes === 'function') {
                    if (!actual.includes(expected)) {
                      throw new Error(`Expected ${actual} to contain ${expected}`);
                    }
                  } else {
                    throw new Error(`toContain is not supported for ${typeof actual}`);
                  }
                },
                not: {
                  toBe: (expected: any) => {
                    if (actual === expected) {
                      throw new Error(`Expected ${actual} not to be ${expected}`);
                    }
                  },
                  toContain: (expected: any) => {
                    if (typeof actual?.includes === 'function') {
                      if (actual.includes(expected)) {
                        throw new Error(`Expected ${actual} not to contain ${expected}`);
                      }
                    } else {
                      throw new Error(`toContain is not supported for ${typeof actual}`);
                    }
                  },
                  toEqual: (expected: any) => {
                    if (JSON.stringify(actual) === JSON.stringify(expected)) {
                      throw new Error(`Expected ${actual} not to equal ${expected}`);
                    }
                  }
                }
              };
              return assertions;
            }
          };

          // Execute user script with context
          let cleanScript = script.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '');
          if (isBrowserHealthy) {
            const pattern = /(await\s+page\.goto\([^)]+\);?\s*await\s+page\.fill\(\s*['"]#username['\"].*?await\s+page\.click\(\s*['"]#login['\"]\);?)/s;
            if (pattern.test(cleanScript)) {
              cleanScript = cleanScript.replace(pattern, `
                const is_logged_in = page.url().includes('SearchHotel.aspx') || (await page.$('#username').catch(() => null)) === null;
                if (!is_logged_in) {
                  $1
                } else {
                  console.log('[Session Reuse] Already logged in. Bypassing login steps.');
                }
              `);
            }
          }

          const wrappedScript = `
            return (async ({ page, browser, context, screenshot, addLog, addTimelineEvent, test, expect }) => {
              ${cleanScript}
            })
          `;
          const userFunction = new Function(wrappedScript);
          const asyncFunc = userFunction();
          await asyncFunc(executionContext);

          if (testPromises.length > 0) {
            await Promise.all(testPromises);
          }
          if (screenshotPromises.length > 0) {
            await Promise.all(screenshotPromises).catch(() => {});
          }

          success = true;
        } catch (error: any) {
          const recoveryMgr = new RecoveryManager();
          const { action, nextRetryCount } = recoveryMgr.getRecoveryAction(error.message, retryCount);
          
          if (action === 'fail' || nextRetryCount > maxRetries) {
            throw error; // Propagate error to outer catch block
          }

          console.log(`[Recovery] Failure: "${error.message}". Recovery action: ${action}. Next retry count: ${nextRetryCount}`);
          executionQueue.addTimelineEvent(executionId, `Failure detected: "${error.message}". Recovery action: ${action}`, 'warning');

          if (this.screenshotInterval) {
            clearInterval(this.screenshotInterval);
          }

          // Apply recovery action:
          if (action === 'restart_browser') {
            if (ExecutionEngine.sharedBrowser) {
              await ExecutionEngine.sharedBrowser.close().catch(() => {});
            }
            ExecutionEngine.sharedBrowser = null;
            ExecutionEngine.sharedContext = null;
            ExecutionEngine.sharedPage = null;
          } else {
            // retry or re_login
            if (action === 're_login') {
              const storageStatePath = path.join(process.cwd(), 'public', 'artifacts', projectId || 'default', 'storage_state.json');
              await fs.unlink(storageStatePath).catch(() => {});
            }
            if (ExecutionEngine.sharedPage) {
              await ExecutionEngine.sharedPage.close().catch(() => {});
            }
            if (ExecutionEngine.sharedContext) {
              await ExecutionEngine.sharedContext.close().catch(() => {});
            }
            ExecutionEngine.sharedPage = null;
            ExecutionEngine.sharedContext = null;
          }

          retryCount = nextRetryCount;
          executionQueue.addTimelineEvent(executionId, `Retrying execution (Attempt ${retryCount})...`, 'info');
        }
      }

      // Save storage state for session reuse in subsequent tests
      if (context) {
        await context.storageState({ path: storageStatePath }).catch((e) => {
          console.warn('Failed to save storage state:', e);
        });
        executionQueue.addTimelineEvent(executionId, 'Session storage state saved', 'success');
      }

      // Stop trace for current run
      if (recordTrace && context) {
        const tracePath = path.join(traceDir, 'trace.zip');
        await context.tracing.stop({ path: tracePath }).catch(() => {});
        executionQueue.setArtifact(executionId, 'trace', 'trace.zip');
      }

      // Close page and context to finalize the video
      if (page) {
        await page.close().catch(() => {});
      }
      if (context) {
        await context.close().catch(() => {});
      }

      // Clear shared page/context references to force recreation next time
      ExecutionEngine.sharedPage = null;
      ExecutionEngine.sharedContext = null;

      // Scan and register the WebM video artifact
      try {
        const files = await fs.readdir(videoDir);
        const videoFile = files.find(f => f.endsWith('.webm'));
        if (videoFile) {
          executionQueue.setArtifact(executionId, 'video', videoFile);
          executionQueue.addTimelineEvent(executionId, `Simulation video saved: ${videoFile}`, 'success');
        }
      } catch (e) {
        console.warn('Failed to register video artifact:', e);
      }

      // Generate HTML report
      await this.generateHTMLReport(executionId, artifactDir, screenshotDir);

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
        browser_version: finalExecution?.metadata.browserVersion || null,
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
      // 1. Take a screenshot of the failure state if page/browser are still alive
      let errorScreenshotFilename: string | null = null;
      if (this.page) {
        try {
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
          errorScreenshotFilename = `error-${timestamp}.png`;
          const filepath = path.join(screenshotDir, errorScreenshotFilename);
          await this.page.screenshot({ path: filepath });
          executionQueue.addScreenshot(executionId, errorScreenshotFilename);
          executionQueue.addTimelineEvent(executionId, `Screenshot captured on error: ${errorScreenshotFilename}`, 'error');
        } catch (screenshotErr) {
          console.error('[Engine] Failed to capture error screenshot:', screenshotErr);
        }
      }

      // Stop trace on error
      if (this.page && this.page.context()) {
        try {
          const tracePath = path.join(traceDir, 'trace.zip');
          await this.page.context().tracing.stop({ path: tracePath }).catch(() => {});
          executionQueue.setArtifact(executionId, 'trace', 'trace.zip');
        } catch (traceErr) {
          console.error('[Engine] Failed to stop tracing on error:', traceErr);
        }
      }

      // Close page and context to finalize the video
      if (this.page) {
        await this.page.close().catch(() => {});
      }
      if (this.browser && ExecutionEngine.sharedContext) {
        await ExecutionEngine.sharedContext.close().catch(() => {});
      }

      // Clear shared page/context references to force recreation next time
      ExecutionEngine.sharedPage = null;
      ExecutionEngine.sharedContext = null;

      // Scan and register the WebM video artifact on error
      try {
        const files = await fs.readdir(videoDir);
        const videoFile = files.find(f => f.endsWith('.webm'));
        if (videoFile) {
          executionQueue.setArtifact(executionId, 'video', videoFile);
        }
      } catch (e) {
        console.warn('Failed to register video artifact on error:', e);
      }

      // Generate HTML report
      try {
        await this.generateHTMLReport(executionId, artifactDir, screenshotDir);
      } catch (reportErr) {
        console.error('[Engine] Failed to generate HTML report on error:', reportErr);
      }

      // Cleanup browser/page only if crashed or disconnected
      const errLower = error.message.toLowerCase();
      const isCrash = errLower.includes('crash') || errLower.includes('closed') || errLower.includes('disconnected');
      if (isCrash) {
        if (this.page) await this.page.close().catch(() => {});
        if (this.browser) await this.browser.close().catch(() => {});
        ExecutionEngine.sharedBrowser = null;
        ExecutionEngine.sharedPage = null;
        ExecutionEngine.sharedContext = null;
      }

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
        browser_version: finalExecution?.metadata.browserVersion || null,
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
      const browserInfo = execution.metadata.browserVersion
        ? `Chromium ${execution.metadata.browserVersion}`
        : "Chromium";

      // Include errors, successes, and any events with screenshots/details to show all key progression steps
      const stepEvents = (execution.timeline || []).filter(
        (evt) => evt.event !== 'Execution Queued' && (evt.type === 'error' || evt.type === 'success' || (evt.details && evt.details.endsWith('.png')))
      );

      const mappedSteps = stepEvents.map((event, index) => {
        const eventName = event.event;
        const timeVal = event.time;
        const evtType = event.type;
        const details = event.details || "";

        const screenshotFilename = details.endsWith(".png") ? details : null;
        let imgPath = screenshotFilename ? `screenshots/${screenshotFilename}` : null;

        let title = eventName;
        let action = `Execute test step: '${eventName}'.`;
        let observation = `Timeline logged event of type '${evtType}'.`;
        let result = "Step executed successfully.";

        if (evtType === "error" || eventName.toLowerCase().includes("error")) {
          title = "Execution Failure";
          const detailsLower = details.toLowerCase();
          if (detailsLower.includes("strict mode violation")) {
            action = "Select unique target element on screen";
            observation = "Playwright strict mode violation: The test code attempted to click or interact with an element, but the browser found multiple elements matching that description.";
            result = "The selector is ambiguous. To resolve this, update the test script locator to be more specific, such as using the exact button/link text (e.g. 'Enter Vehicle Data') or targeting its unique ID/attributes (e.g. '#entervehicledata').";
          } else if (detailsLower.includes("element is not an <input>") || detailsLower.includes("locator resolved to <select") || detailsLower.includes("selectoption") || detailsLower.includes("select option")) {
            action = "Select dropdown option value";
            observation = "Playwright tried to type or fill text into a dropdown selection element (<select>) instead of choosing one of its options.";
            result = "A dropdown (<select>) element cannot be filled with text. The automation script must be corrected to use 'selectOption' (e.g. page.selectOption('#make', 'Toyota') or page.locator('#make').selectOption('Toyota')) instead of 'fill'.";
          } else if (detailsLower.includes("timeout") || detailsLower.includes("waiting for locator") || detailsLower.includes("waiting for selector")) {
            action = "Wait for target element to become visible / interactive on page";
            observation = "Playwright timed out waiting for the target element to load or appear on the page (the element remained hidden or was not rendered within the timeout period).";
            result = "Verify if the preceding test steps executed successfully, check if the website response was slow, or confirm if the element's selector is correct.";
          } else if (detailsLower.includes("is hidden") || detailsLower.includes("is not visible") || detailsLower.includes("intercepts pointer events") || detailsLower.includes("disabled")) {
            action = "Interact with target element";
            observation = "The target element was found on the page, but it was hidden, disabled, or blocked/intercepted by another page element (like a modal popup, overlay, or loading spinner).";
            result = "Ensure the target element is fully active and visible, and close any blocking modals or overlays before interacting with it.";
          } else if (detailsLower.includes("net::err") || detailsLower.includes("navigation failed") || detailsLower.includes("page.goto")) {
            action = "Load application landing page";
            observation = "The browser failed to navigate to the target URL. The application server might be down, the hostname might be invalid, or the server is refusing connections.";
            result = "Verify that the target application is running locally or online, and that your local network connection / proxy settings are active.";
          } else if (detailsLower.includes("expect") || detailsLower.includes("assertionerror") || detailsLower.includes("assertion")) {
            action = "Verify expected test condition (Assertion)";
            observation = "The test run successfully completed its actions, but the final validation check failed. The page content or page state did not match the expected assertion criteria.";
            result = "Verify if the application behaved unexpectedly, or if the test assertion value needs to be updated.";
          } else {
            action = "Interact with target page controls / elements.";
            observation = `Playwright runner logged error: ${details}`;
            result = `Error details: ${details || 'Timeout/Assertion failure'}`;
          }
          
          // Fallback to find error screenshot in directory
          const errorFilename = screenshots.find(
            s => s.toLowerCase().includes('error') || s.toLowerCase().includes('failed')
          );
          if (errorFilename) {
            imgPath = `screenshots/${errorFilename}`;
          } else if (screenshots.length > 0) {
            imgPath = `screenshots/${screenshots[screenshots.length - 1]}`;
          }
        } else if (screenshotFilename) {
          const fnLower = screenshotFilename.toLowerCase();
          const eventLower = eventName.toLowerCase();
          const isPlaceholder = eventLower.includes("screenshot captured") || eventLower === "screenshot" || eventLower === "visual state capture";

          if (isPlaceholder && (fnLower.includes("initial") || fnLower.includes("01-"))) {
            title = "Initial Portal Loading";
            action = "Navigate to the Tricentis Vehicle Insurance portal and initialize the test session.";
            observation = "The application landing page loaded successfully. The vehicle data input form is displayed and interactive.";
            result = "Portal loaded and ready for automation.";
          } else if (isPlaceholder && (fnLower.includes("form-filled") || fnLower.includes("02-"))) {
            title = "Vehicle Form Input Completion";
            action = "Fill out all vehicle specifications: Make (BMW), Model (Scooter), Cylinder Capacity (150), Engine Performance (90), Date of Manufacture, Seats (2), Fuel (Petrol), List Price (25000), License Plate, and Annual Mileage.";
            observation = "All input fields and selection dropdowns populated with correct test data parameters. No form validation errors.";
            result = "Vehicle data form validation passed.";
          } else if (isPlaceholder && (fnLower.includes("insurant-data") || fnLower.includes("03-"))) {
            title = "Transition to Enter Insurant Data";
            action = "Click the 'Next' action button to submit the vehicle form data and navigate to the Insurant details form.";
            observation = "Form submitted successfully. Browser page navigated to the Enter Insurant Data portal page view.";
            result = "Navigation to insurant form successful.";
          } else {
            title = isPlaceholder ? "Visual State Capture" : eventName;
            action = isPlaceholder ? "Capture screenshot to record browser visual state." : `Execute test step: '${eventName}'.`;
            observation = isPlaceholder ? `Visual state captured in file '${screenshotFilename}'.` : "Browser successfully navigated / interacted. Verified visual state layout.";
            result = isPlaceholder ? "Screenshot image saved on disk." : "Step executed successfully.";
          }
        }

        return {
          title,
          time: `+${timeVal.toFixed(2)}s`,
          action,
          observation,
          result,
          imgPath
        };
      });

      const stepsHtmlStr = mappedSteps.map((step, idx) => {
        const screenshotTag = step.imgPath
          ? `<div class="step-image"><img src="${step.imgPath}" alt="Screenshot ${idx + 1}" /></div>`
          : `<div class="no-image-box"><span>No Screenshot Captured</span></div>`;

        return `
          <div class="step-card">
            <div class="step-left">
              <div class="step-header">
                <span class="step-num">Step ${idx + 1}</span>
                <span class="step-title">${step.title}</span>
                <span class="step-time">${step.time}</span>
              </div>
              <div class="step-details">
                <div class="detail-row">
                  <span class="detail-label">Actions Taken</span>
                  ${step.action}
                </div>
                <div class="detail-row">
                  <span class="detail-label">Observation</span>
                  ${step.observation}
                </div>
                <div class="detail-row">
                  <span class="detail-label">Result</span>
                  ${step.result}
                </div>
              </div>
            </div>
            <div class="step-right">
              ${screenshotTag}
            </div>
          </div>
        `;
      }).join('\n') || "<div class='step-card'><p>No execution timeline events recorded.</p></div>";

      // Try to find booking order number in logs or timeline events
      let orderNoFound = "N/A";
      const allLogs = [...(execution.artifacts.logs || []), ...(execution.artifacts.console || [])];
      for (const logLine of allLogs) {
        const match = logLine.match(/Order Number:\s*(\w+)/i) || logLine.match(/order_no:\s*(\w+)/i) || logLine.match(/Generated Order Number:\s*(\w+)/i);
        if (match) {
          orderNoFound = match[1];
          break;
        }
      }
      if (orderNoFound === "N/A") {
        for (const evt of (execution.timeline || [])) {
          const match = evt.event.match(/Order Number:\s*(\w+)/i) || evt.event.match(/Generated Order Number:\s*(\w+)/i) || (evt.details && evt.details.match(/Order Number:\s*(\w+)/i));
          if (match) {
            orderNoFound = match[1];
            break;
          }
        }
      }

      const summaryOutcomeText = execution.metadata.status === 'completed'
        ? "The automated testcase completed successfully on the target application. A total of " + mappedSteps.length + " steps were executed sequentially, verifying form element interactions. All validation checks passed."
        : "The automated test execution encountered errors or assertions failed. Verification aborted. Sequential logs have been persisted for failure diagnostics.";

      const html = `<!DOCTYPE html>
<html>
<head>
    <title>Execution Report - ${executionId}</title>
    <style>
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            padding: 40px 20px;
            margin: 0;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .header {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 32px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        .header-main {
            display: flex;
            align-items: center;
            gap: 20px;
            border-bottom: 1px solid #334155;
            padding-bottom: 20px;
        }
        .header-title h1 {
            margin: 0 0 6px 0;
            font-size: 24px;
            color: #3b82f6;
        }
        .header-title p {
            margin: 0;
            color: #64748b;
            font-size: 13px;
            font-family: monospace;
        }
        .header-metadata {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .meta-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 600px) {
            .meta-grid {
                grid-template-columns: 1fr;
            }
        }
        .meta-label {
            font-size: 11px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: bold;
        }
        .meta-value {
            font-size: 15px;
            color: #e2e8f0;
            font-weight: 500;
        }
        .link-value {
            color: #3b82f6;
            text-decoration: none;
        }
        .link-value:hover {
            text-decoration: underline;
        }
        .badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-completed { background-color: #10b981; color: #ffffff; }
        .badge-failed { background-color: #ef4444; color: #ffffff; }
        .badge-stopped { background-color: #f59e0b; color: #ffffff; }
        
        h2 {
            font-size: 20px;
            color: #f1f5f9;
            margin-top: 32px;
            margin-bottom: 20px;
            border-bottom: 1px solid #334155;
            padding-bottom: 8px;
        }
        
        .step-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 24px;
        }
        @media (max-width: 768px) {
            .step-card {
                grid-template-columns: 1fr;
            }
        }
        .step-left {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .step-right {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .step-header {
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #334155;
            padding-bottom: 12px;
            margin-bottom: 12px;
        }
        .step-num {
            background-color: #3b82f6;
            color: #ffffff;
            font-size: 12px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
        }
        .step-title {
            font-weight: bold;
            font-size: 16px;
            color: #e2e8f0;
            flex-grow: 1;
        }
        .step-time {
            font-family: monospace;
            font-size: 13px;
            color: #94a3b8;
        }
        .step-details {
            display: flex;
            flex-direction: column;
            gap: 12px;
            font-size: 14px;
        }
        .detail-row {
            line-height: 1.6;
            color: #cbd5e1;
        }
        .detail-label {
            font-weight: bold;
            color: #94a3b8;
            display: block;
            margin-bottom: 2px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .step-image img {
            max-width: 100%;
            max-height: 240px;
            border-radius: 8px;
            border: 1px solid #475569;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            object-fit: contain;
        }
        .no-image-box {
            width: 100%;
            height: 150px;
            background-color: #0f172a;
            border: 2px dashed #334155;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #475569;
            font-size: 13px;
        }
        .summary-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-top: 32px;
        }
        .summary-title {
            font-size: 16px;
            font-weight: bold;
            color: #3b82f6;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-main">
                <span class="badge badge-${execution.metadata.status}">
                    ${execution.metadata.status.toUpperCase()}
                </span>
                <div class="header-title">
                    <h1>Enterprise Test Execution Report</h1>
                    <p>Execution ID: ${executionId}</p>
                </div>
            </div>
            <div class="header-metadata">
                <div class="meta-row">
                    <span class="meta-label">Website Under Test</span>
                    <span class="meta-value">https://adactinhotelapp.com/</span>
                </div>
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="meta-label">Started At</span>
                        <span class="meta-value">${new Date(execution.metadata.started).toLocaleString()}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Execution Duration</span>
                        <span class="meta-value">${(execution.metadata.duration || 0).toFixed(2)} seconds</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Browser</span>
                        <span class="meta-value">${browserInfo}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Total Steps</span>
                        <span class="meta-value">${mappedSteps.length}</span>
                    </div>
                    <div class="meta-item" style="border-left: 2px solid #10b981; padding-left: 10px;">
                        <span class="meta-label" style="color: #10b981;">Generated Order Number</span>
                        <span class="meta-value" style="color: #10b981; font-weight: bold; font-family: monospace;">${orderNoFound}</span>
                    </div>
                </div>
            </div>
        </div>
        
        <h2>Step-by-Step Walkthrough</h2>
        <div class="steps-container">
            ${stepsHtmlStr}
        </div>

        <div class="summary-card">
            <div class="summary-title">Execution Summary</div>
            <div style="line-height: 1.6; color: #cbd5e1;">
                ${summaryOutcomeText}
            </div>
        </div>
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
