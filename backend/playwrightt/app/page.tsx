'use client';

import { useState, useCallback, useEffect } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { ExecutionList } from '@/components/execution-list';
import { LiveBrowserPreview } from '@/components/live-browser-preview';
import { Play, Code2, Globe } from 'lucide-react';
import { Execution } from '@/lib/execution-queue';

const SAMPLE_SCRIPT = `// Tricentis Vehicle Insurance Application Test
// This test navigates to the Tricentis app and fills out a vehicle form

// Navigate to the Tricentis application
await page.goto('https://sampleapp.tricentis.com/101/app.php', { waitUntil: 'networkidle' });
addLog('Navigated to Tricentis Vehicle Insurance Application');
addTimelineEvent('Website loaded', 'success');

// Take a screenshot of the initial state
await screenshot('01-initial-state');

// Select a vehicle make from the dropdown
const makeDropdown = await page.$('[name="Make"]');
if (makeDropdown) {
  await makeDropdown.click();
  await page.waitForTimeout(300);
  await page.selectOption('[name="Make"]', 'BMW');
  addLog('Selected BMW as vehicle make');
  addTimelineEvent('Vehicle make selected', 'success');
}

// Take another screenshot after selection
await screenshot('02-after-make-selection');

// Verify the selection was made
const selectedMake = await page.inputValue('[name="Make"]');
addLog(\`Selected make value: \${selectedMake}\`);

// Check if the model dropdown has been populated
try {
  await page.waitForSelector('[name="Model"] option:nth-child(2)', { timeout: 3000 });
  addTimelineEvent('Model dropdown populated', 'success');
  addLog('Model options are now available');
} catch (error) {
  addLog('Model dropdown not populated: ' + error.message);
  addTimelineEvent('Model population delayed', 'warning');
}

// Take final screenshot
await screenshot('03-final-state');
addTimelineEvent('Test completed successfully', 'success');
addLog('All test steps completed');
`;

export default function Home() {
  const [script, setScript] = useState(SAMPLE_SCRIPT);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [queue, setQueue] = useState<string[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Handle script execution
  const handleExecute = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script,
          projectId: 'demo-project',
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

      // Refresh executions
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
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Code2 className="w-8 h-8 text-blue-600" />
            <h1 className="text-4xl font-bold">Playwright Execution Engine</h1>
          </div>
          <p className="text-gray-600">
            Execute browser automation scripts with real-time monitoring and artifact collection
          </p>
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
                Script
              </h2>
              <Textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                className="min-h-64 font-mono text-sm bg-gray-50 border-gray-300 text-gray-900"
                placeholder="Enter your Playwright script..."
              />
              <Button
                onClick={handleExecute}
                disabled={isLoading || !script.trim()}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                {isLoading ? 'Starting...' : 'Execute Script'}
              </Button>

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
