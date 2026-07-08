'use client';

import { useState, useCallback, useEffect, Suspense } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { ExecutionList } from '@/components/execution-list';
import { LiveBrowserPreview } from '@/components/live-browser-preview';
import { Play, Code2, Globe, Save } from 'lucide-react';
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

  // Fetch executions
  const fetchExecutions = useCallback(async () => {
    try {
      const response = await fetch('/api/status');
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
  }, []);

  // Fetch workspace details from FastAPI on load
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const pId = params.get('project_id');
      const tcId = params.get('test_case_id');
      
      setProjectId(pId);
      setTestCaseId(tcId);

      if (pId && tcId) {
        fetch(`http://localhost:8000/api/v1/playwright/workspace?project_id=${pId}&test_case_id=${tcId}`)
          .then(res => {
            if (!res.ok) throw new Error("Workspace details not found");
            return res.json();
          })
          .then(data => {
            if (data.playwright_script !== null && data.playwright_script !== undefined) {
              setScript(data.playwright_script);
            } else {
              setScript(SAMPLE_SCRIPT);
            }
            setTestCaseTitle(`Test Case: ${tcId.substring(0, 8)}`);
          })
          .catch(err => {
            console.error("Error loading workspace data from FastAPI:", err);
            setError("Failed to load script context from the Enterprise Platform.");
          });
      }
    }
  }, []);

  // Save script back to FastAPI
  const handleSave = async () => {
    if (!projectId || !testCaseId) return;
    setIsSaving(true);
    setSaveSuccess(false);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/v1/playwright/script', {
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
  const handleExecute = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Auto-save script back to FastAPI before execution to keep it authoritative
      if (projectId && testCaseId) {
        await handleSave();
      }

      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script,
          projectId: projectId || 'demo-project',
          testCaseIds: testCaseId ? [testCaseId] : [],
          browser: 'chromium',
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
    <div className="min-h-screen bg-white text-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Code2 className="w-8 h-8 text-blue-600" />
              <h1 className="text-4xl font-bold">Playwright Workspace</h1>
            </div>
            <p className="text-gray-600">
              {testCaseTitle 
                ? `${testCaseTitle} — Persisted to the Enterprise Platform`
                : 'Author, verify, and run browser automation scripts'}
            </p>
          </div>
          {testCaseId && (
            <div className="flex gap-2">
              <Button
                onClick={handleSave}
                disabled={isSaving || isLoading}
                variant="outline"
                className="border-blue-600 text-blue-600 hover:bg-blue-50"
              >
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          )}
        </div>

        {/* Live Browser Preview - Full Width Top Section */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Globe className="w-6 h-6 text-green-600" />
            <h2 className="text-2xl font-bold">Live Browser Preview</h2>
          </div>
          <div className="h-96 bg-white rounded-lg border border-gray-300 overflow-hidden shadow-sm">
            <LiveBrowserPreview />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Script Editor */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-lg border border-gray-300 p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-3 flex items-center gap-2 text-gray-900">
                <Code2 className="w-5 h-5" />
                Monaco Editor
              </h2>
              
              <div className="border border-gray-300 rounded overflow-hidden">
                <Editor
                  height="400px"
                  defaultLanguage="typescript"
                  value={script}
                  onChange={(val) => setScript(val || '')}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    automaticLayout: true,
                    tabSize: 2,
                  }}
                />
              </div>

              <div className="flex gap-2 mt-4">
                <Button
                  onClick={handleExecute}
                  disabled={isLoading || !script.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {isLoading ? 'Starting...' : 'Execute Script'}
                </Button>
              </div>

              {saveSuccess && (
                <div className="mt-4 p-2 bg-green-50 border border-green-300 rounded text-green-800 text-sm text-center">
                  Changes successfully saved to Enterprise Platform!
                </div>
              )}

              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-300 rounded text-red-800 text-sm">
                  {error}
                </div>
              )}
            </div>

            {/* Status Summary */}
            <div className="bg-white rounded-lg border border-gray-300 p-4 shadow-sm">
              <h3 className="font-semibold mb-3 text-gray-900">Status</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Executions</span>
                  <span className="font-mono text-gray-900">{executions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Queued</span>
                  <span className="font-mono text-purple-600">{queue.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Running</span>
                  <span className="font-mono text-blue-600">
                    {current ? '1' : '0'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Completed</span>
                  <span className="font-mono text-green-600">
                    {executions.filter((e) => e.metadata.status === 'completed')
                      .length}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Execution List */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-gray-300 p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Recent Executions</h2>
              <ExecutionList
                executions={executions}
                queue={queue}
                current={current}
                onStatusChange={handleStatusChange}
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
