'use client';

import { useState, useCallback, useEffect, Suspense } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { ExecutionList } from '@/components/execution-list';
import { LiveBrowserPreview } from '@/components/live-browser-preview';
import { Play, Code2, Globe, Save, Sun, Moon } from 'lucide-react';
import { Execution } from '@/lib/execution-queue';

const SAMPLE_SCRIPT = `// Tricentis Vehicle Insurance Application Test
// This test navigates to the Tricentis app, fills out the Enter Vehicle Data form completely and moves to the next page.

// Navigate to the Tricentis application
await page.goto('https://sampleapp.tricentis.com/101/app.php', { waitUntil: 'networkidle' });
addLog('Navigated to Tricentis Vehicle Insurance Application');
addTimelineEvent('Website loaded', 'success');

// Take a screenshot of the initial state
await screenshot('01-initial-state');

// Select Make
await page.selectOption('#make', 'BMW');
addLog('Selected BMW as vehicle make');
addTimelineEvent('Vehicle make selected', 'success');

// Wait for Model dropdown to populate and select Model
await page.waitForSelector('#model option:nth-child(2)', { state: 'attached', timeout: 3000 });
await page.selectOption('#model', 'Scooter');
addLog('Selected Scooter as vehicle model');
addTimelineEvent('Vehicle model selected', 'success');

// Fill Cylinder Capacity
await page.fill('#cylindercapacity', '150');
addLog('Entered Cylinder Capacity: 150');

// Fill Engine Performance
await page.fill('#engineperformance', '90');
addLog('Entered Engine Performance: 90');

// Fill Date of Manufacture
await page.fill('#dateofmanufacture', '06/01/2024');
addLog('Entered Date of Manufacture: 06/01/2024');

// Select Number of Seats
if (await page.isVisible('#numberofseatsmotorcycle')) {
  await page.selectOption('#numberofseatsmotorcycle', '2');
} else {
  await page.selectOption('#numberofseats', '2');
}
addLog('Selected 2 seats');

// Select Fuel Type
await page.selectOption('#fuel', 'Petrol');
addLog('Selected Petrol as fuel type');

// Fill List Price
await page.fill('#listprice', '25000');
addLog('Entered List Price: 25000');

// Fill License Plate Number
await page.fill('#licenseplatenumber', 'BMW-101');
addLog('Entered License Plate Number: BMW-101');

// Fill Annual Mileage
await page.fill('#annualmileage', '12000');
addLog('Entered Annual Mileage: 12000');
addTimelineEvent('Form fields filled', 'success');

// Take screenshot before proceeding
await screenshot('02-form-filled');

// Click Next
const nextBtn = await page.$('#nextenterinsurantdata');
if (nextBtn) {
  await nextBtn.click();
  addLog('Clicked Next (Enter Insurant Data)');
  addTimelineEvent('Clicked Next', 'success');
  await page.waitForTimeout(1000);
}

// Take final screenshot of insurant data page
await screenshot('03-insurant-data-page');
addTimelineEvent('Test completed successfully', 'success');
addLog('All test steps completed');
`;

function PlaywrightWorkspaceContent() {
  const getBackendUrl = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      return `http://${hostname}:8000`;
    }
    return 'http://127.0.0.1:8000';
  };

  const [script, setScript] = useState(SAMPLE_SCRIPT);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [queue, setQueue] = useState<string[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projectId, setProjectId] = useState<string | null>(null);
  const [testCaseId, setTestCaseId] = useState<string | null>(null);
  const [testCaseTitle, setTestCaseTitle] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isFrozen, setIsFrozen] = useState(false);
  const [scenario, setScenario] = useState<{ id: string; scenario_name: string; description: string } | null>(null);
  const [uploadTestData, setUploadTestData] = useState(false);
  const [testDataText, setTestDataText] = useState("");

  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    // Default to dark theme to match portal
    document.documentElement.classList.add('dark');
  }, []);

  const toggleTheme = (e: React.MouseEvent<HTMLButtonElement>) => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    
    const changeTheme = () => {
      setTheme(nextTheme);
      if (typeof window !== 'undefined') {
        if (nextTheme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    };

    if (!(document as any).startViewTransition) {
      changeTheme();
      return;
    }

    const rect = e.currentTarget.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    );

    const transition = (document as any).startViewTransition(() => {
      changeTheme();
    });

    transition.ready.then(() => {
      document.documentElement.animate(
        {
          clipPath: [
            `circle(0px at ${x}px ${y}px)`,
            `circle(${endRadius}px at ${x}px ${y}px)`,
          ],
        },
        {
          duration: 400,
          easing: 'ease-out',
          pseudoElement: '::view-transition-new(root)',
        }
      );
    });
  };

  // Fetch executions
  const fetchExecutions = useCallback(async () => {
    try {
      const url = projectId 
        ? `/api/status?projectId=${projectId}`
        : '/api/status';
      const response = await fetch(url);
      if (!response.ok) {
        console.error('[Dashboard] Status response not ok:', response.status);
        return;
      }
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        setExecutions(data.executions || []);
        setQueue(data.queue || []);
        setCurrent(data.current);
      } catch (jsonErr) {
        console.error('[Dashboard] JSON parse error:', jsonErr, 'Response:', text.substring(0, 100));
      }
    } catch (err) {
      console.error('[Dashboard] Fetch error:', err);
    }
  }, [projectId]);

  // Fetch workspace details from FastAPI on load
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      let pId = params.get('project_id');
      let tcId = params.get('test_case_id');
      
      // Fallback to localStorage if parameters are not present in URL
      if (!pId) {
        pId = localStorage.getItem('project_id');
      } else {
        localStorage.setItem('project_id', pId);
      }
      
      if (!tcId) {
        tcId = localStorage.getItem('test_case_id');
      } else {
        localStorage.setItem('test_case_id', tcId);
      }

      const initializeWorkspace = async () => {
        // Step 1: If project ID is still missing, fetch the first project from FastAPI
        if (!pId) {
          try {
            const projectsRes = await fetch(`${getBackendUrl()}/api/v1/projects`);
            if (projectsRes.ok) {
              const projects = await projectsRes.json();
              if (Array.isArray(projects) && projects.length > 0) {
                pId = projects[0].id;
                localStorage.setItem('project_id', pId!);
                setProjectId(pId);
              }
            }
          } catch (err) {
            console.error("Failed to default projects list:", err);
          }
        } else {
          setProjectId(pId);
        }

        // Step 2: If we have a project ID but test case ID is still missing, fetch test cases for the project
        if (pId && !tcId) {
          try {
            const testcasesRes = await fetch(`${getBackendUrl()}/api/v1/projects/${pId}/testcases`);
            if (testcasesRes.ok) {
              const testcases = await testcasesRes.json();
              if (Array.isArray(testcases) && testcases.length > 0) {
                tcId = testcases[0].id;
                localStorage.setItem('test_case_id', tcId!);
                setTestCaseId(tcId);
              }
            }
          } catch (err) {
            console.error("Failed to default testcases list:", err);
          }
        } else {
          setTestCaseId(tcId);
        }

        // Step 3: Fetch workspace details if we have both IDs
        if (pId && tcId) {
          try {
            const res = await fetch(`${getBackendUrl()}/api/v1/playwright/workspace?project_id=${pId}&test_case_id=${tcId}`);
            if (!res.ok) throw new Error("Workspace details not found");
            const data = await res.json();
            
            if (data.playwright_script !== null && data.playwright_script !== undefined) {
              setScript(data.playwright_script);
            } else {
              setScript(SAMPLE_SCRIPT);
            }
            if (data.is_frozen !== undefined) {
              setIsFrozen(data.is_frozen);
            }
            if (data.scenario) {
              setScenario(data.scenario);
            }
            setTestCaseTitle(`Test Case: ${tcId.substring(0, 8)}`);
          } catch (err) {
            console.error("Error loading workspace data from FastAPI:", err);
            setError("Failed to load script context from the Enterprise Platform.");
          }
        }
      };

      initializeWorkspace();
    }
  }, []);

  // Load and poll executions history on component mount
  useEffect(() => {
    fetchExecutions();
    const poll = setInterval(fetchExecutions, 2000);
    return () => clearInterval(poll);
  }, [fetchExecutions]);

  const handleFreeze = async () => {
    if (!testCaseId) return;
    try {
      const response = await fetch(`${getBackendUrl()}/api/v1/playwright/freeze`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_case_id: testCaseId,
          is_frozen: true
        })
      });
      if (!response.ok) throw new Error("Failed to freeze script");
      setIsFrozen(true);
    } catch (err: any) {
      setError(`Freeze failed: ${err.message}`);
    }
  };

  // Save script back to FastAPI
  const handleSave = async () => {
    if (isFrozen) return;
    if (!projectId || !testCaseId) return;
    setIsSaving(true);
    setSaveSuccess(false);
    setError(null);
    try {
      const response = await fetch(`${getBackendUrl()}/api/v1/playwright/script`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          test_case_id: testCaseId,
          script
        })
      });
      if (!response.ok) {
        throw new Error("Failed to save script back to repository");
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err: any) {
      setError(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle script execution
  const handleExecute = async (overrideScript?: any) => {
    const isOverride = typeof overrideScript === 'string';
    const scriptToRun = isOverride ? overrideScript : script;
    setIsLoading(true);
    setError(null);

    try {
      // Auto-save script back to FastAPI before execution to keep it authoritative (if not frozen)
      if (projectId && testCaseId && !isFrozen && !isOverride) {
        await handleSave();
      }

      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script: scriptToRun,
          projectId: projectId || 'demo-project',
          testCaseIds: testCaseId ? [testCaseId] : [],
          browser: 'chromium',
          testData: uploadTestData ? testDataText : null
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to execute script');
      }

      const data = await response.json();

      if (data.error) {
        setError(data.error);
      }

      await fetchExecutions();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle status change
  const handleStatusChange = async (executionId: string, action: string) => {
    try {
      const response = await fetch(`/api/status?id=${executionId}&action=${action}`, {
        method: 'PUT',
      });

      if (!response.ok) {
        throw new Error('Failed to update execution');
      }

      await fetchExecutions();
    } catch (err) {
      console.error('[Dashboard] Status change error:', err);
    }
  };

  // Refresh on mount
  useEffect(() => {
    fetchExecutions();
    const interval = setInterval(fetchExecutions, 2000);
    return () => clearInterval(interval);
  }, [fetchExecutions]);

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Code2 className="w-8 h-8 text-blue-600" />
              <h1 className="text-4xl font-bold text-foreground">Playwright Workspace</h1>
            </div>
            <p className="text-muted-foreground">
              {testCaseTitle 
                ? `${testCaseTitle} — Persisted to the Enterprise Platform`
                : 'Author, verify, and run browser automation scripts'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={toggleTheme}
              variant="outline"
              size="icon"
              className="border-border text-foreground hover:bg-muted rounded-full w-10 h-10 flex items-center justify-center cursor-pointer"
              title="Toggle Theme"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
            {testCaseId && (
              <Button
                onClick={handleSave}
                disabled={isSaving || isLoading}
                variant="outline"
                className="border-border text-foreground hover:bg-muted"
              >
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </Button>
            )}
          </div>
        </div>

        {/* Live Browser Preview - Full Width Top Section */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Globe className="w-6 h-6 text-green-600" />
            <h2 className="text-2xl font-bold text-foreground">Live Browser Preview</h2>
          </div>
          <div className="h-96 bg-card rounded-lg border border-border overflow-hidden shadow-sm">
            <LiveBrowserPreview />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Script Editor */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-card rounded-lg border border-border p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-3 flex items-center justify-between text-foreground">
                <span className="flex items-center gap-2">
                  <Code2 className="w-5 h-5" />
                  Monaco Editor
                </span>
                {isFrozen && <span className="text-xs bg-red-500/10 border border-red-500/30 text-red-400 px-2 py-0.5 rounded flex items-center gap-1 font-normal">🔒 Locked</span>}
                {!isFrozen && testCaseId && (
                  <Button
                    onClick={handleFreeze}
                    variant="outline"
                    className="h-7 text-xs border-red-500/30 text-red-400 hover:bg-red-500/10"
                  >
                    Freeze Code
                  </Button>
                )}
              </h2>

              {scenario && (
                <div className="p-3 bg-muted/30 border border-border rounded text-sm mb-3">
                  <div className="font-semibold text-foreground mb-1 flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground uppercase font-normal">Scenario:</span>
                    {scenario.scenario_name}
                  </div>
                  <p className="text-muted-foreground text-xs">{scenario.description}</p>
                </div>
              )}
              
              <div className="border border-border rounded overflow-hidden">
                <Editor
                  height="400px"
                  defaultLanguage="typescript"
                  value={script}
                  onChange={(val) => setScript(val || '')}
                  theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    automaticLayout: true,
                    tabSize: 2,
                    readOnly: isFrozen
                  }}
                />
              </div>

              <div className="mt-4 border-t border-border pt-3">
                <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={uploadTestData}
                    onChange={(e) => setUploadTestData(e.target.checked)}
                    className="rounded border-border bg-card text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                  <span>Are you willing to upload test data?</span>
                </label>
                
                {uploadTestData && (
                  <div className="mt-2 space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        accept=".json,.csv,.txt"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onload = (evt) => {
                              setTestDataText(evt.target?.result as string || "");
                            };
                            reader.readAsText(file);
                          }
                        }}
                        className="text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-600/10 file:text-blue-400 hover:file:bg-blue-600/20 cursor-pointer"
                      />
                    </div>
                    <textarea
                      placeholder="Paste or upload test data (JSON, CSV or plain text) here before execution..."
                      value={testDataText}
                      onChange={(e) => setTestDataText(e.target.value)}
                      className="w-full h-24 p-2 bg-muted/30 border border-border rounded text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                )}
              </div>

              <div className="flex gap-2 mt-4">
                <Button
                  onClick={handleExecute}
                  disabled={isLoading || !script.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white cursor-pointer"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {isLoading ? 'Starting...' : 'Execute Script'}
                </Button>
              </div>

              {saveSuccess && (
                <div className="mt-4 p-2 bg-green-500/10 border border-green-500/30 rounded text-green-400 text-sm text-center">
                  Changes successfully saved to Enterprise Platform!
                </div>
              )}

              {error && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>

            {/* Status Summary */}
            <div className="bg-card rounded-lg border border-border p-4 shadow-sm">
              <h3 className="font-semibold mb-3 text-foreground">Status</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Executions</span>
                  <span className="font-mono text-foreground">{executions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Queued</span>
                  <span className="font-mono text-purple-600">{queue.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Running</span>
                  <span className="font-mono text-blue-600">
                    {current ? '1' : '0'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Completed</span>
                  <span className="font-mono text-green-600">
                    {executions.filter((e) => e?.metadata?.status === 'completed')
                      .length}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Execution List */}
          <div className="lg:col-span-2">
            <div className="bg-card rounded-lg border border-border p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-4 text-foreground">Recent Executions</h2>
              <ExecutionList
                executions={executions}
                queue={queue}
                current={current}
                onStatusChange={handleStatusChange}
                onRerun={(rerunScript) => {
                  setScript(rerunScript);
                  handleExecute(rerunScript);
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Loading Playwright Workspace...</div>}>
      <PlaywrightWorkspaceContent />
    </Suspense>
  );
}
