'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Execution } from '@/lib/execution-queue';
import { BrowserViewer } from '@/components/browser-viewer';
import { ExecutionTimeline } from '@/components/execution-timeline';
import { ArtifactPreview } from '@/components/artifact-preview';
import { ResultsSummary } from '@/components/results-summary';
import { Button } from '@/components/ui/button';
import { ChevronLeft, Download } from 'lucide-react';

export default function ExecutionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const executionId = params.id as string;

  const [execution, setExecution] = useState<Execution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'results' | 'browser' | 'timeline' | 'artifacts'>('results');

  const fetchExecution = useCallback(async () => {
    try {
      const response = await fetch(`/api/status?id=${executionId}`);
      if (!response.ok) {
        // If not in queue, try to load from artifacts API
        const artifactsResponse = await fetch(`/api/artifacts/${executionId}`);
        if (!artifactsResponse.ok) {
          throw new Error('Execution not found');
        }
        const artifactsData = await artifactsResponse.json();
        // Create a minimal execution object from artifacts data
        setExecution({
          metadata: {
            executionId,
            status: 'completed',
            started: new Date().toISOString(),
            duration: 0,
            browser: 'chromium',
          },
          artifacts: {
            screenshots: artifactsData.screenshots || [],
          },
          timeline: [],
          error: null,
        } as any);
        return;
      }
      const data = await response.json();
      setExecution(data);
    } catch (error) {
      console.error('[ExecutionDetail] Fetch error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [executionId]);

  useEffect(() => {
    fetchExecution();

    // Subscribe to SSE updates
    const eventSource = new EventSource(`/api/stream?id=${executionId}`);

    eventSource.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'update' || message.type === 'status' || message.type === 'complete') {
          fetchExecution();
        }
      } catch (error) {
        console.error('[ExecutionDetail] SSE error:', error);
      }
    });

    eventSource.addEventListener('error', () => {
      eventSource.close();
    });

    return () => {
      eventSource.close();
    };
  }, [executionId, fetchExecution]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white text-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p>Loading execution...</p>
        </div>
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="min-h-screen bg-white text-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Execution not found</p>
          <Button onClick={() => router.push('/')} variant="outline">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const isRunning = execution.metadata.status === 'running';
  const isPaused = execution.metadata.status === 'paused';

  const handleStatusChange = async (action: string) => {
    try {
      const response = await fetch(`/api/status?id=${executionId}&action=${action}`, {
        method: 'PUT',
      });

      if (response.ok) {
        fetchExecution();
      }
    } catch (error) {
      console.error('[ExecutionDetail] Action error:', error);
    }
  };

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => router.push('/')}
              className="text-gray-600"
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold">Execution {executionId.slice(0, 8)}</h1>
              <p className="text-gray-600 text-sm mt-1">
                Status: <span className="font-mono text-blue-600">{execution.metadata.status}</span>
              </p>
            </div>
          </div>
          <a
            href={`/api/artifacts/${executionId}/report`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white"
          >
            <Download className="w-4 h-4" />
            Report
          </a>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg p-4 border border-gray-300 shadow-sm">
            <p className="text-gray-600 text-sm">Status</p>
            <p className="text-lg font-semibold text-blue-600">
              {execution.metadata.status}
            </p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-300 shadow-sm">
            <p className="text-gray-600 text-sm">Started</p>
            <p className="text-lg font-semibold text-gray-900">
              {new Date(execution.metadata.started).toLocaleTimeString()}
            </p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-300 shadow-sm">
            <p className="text-gray-600 text-sm">Duration</p>
            <p className="text-lg font-semibold text-gray-900">
              {execution.metadata.duration ? `${execution.metadata.duration.toFixed(2)}s` : '-'}
            </p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-300 shadow-sm">
            <p className="text-gray-600 text-sm">Browser</p>
            <p className="text-lg font-semibold text-gray-900 capitalize">{execution.metadata.browser}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-300">
          {(['results', 'browser', 'timeline', 'artifacts'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 border-b-2 capitalize font-medium transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-gray-900'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg border border-gray-300 p-6 shadow-sm">
          {activeTab === 'results' && (
            <ResultsSummary
              status={execution.metadata.status as any}
              duration={execution.metadata.duration || 0}
              screenshots={execution.artifacts?.screenshots || []}
              timelineEvents={(execution.timeline || []).map((evt: any) => ({
                event: evt.event || '',
                time: evt.timestamp || 0,
                type: evt.type,
              }))}
              executionId={executionId}
            />
          )}

          {activeTab === 'browser' && (
            <div className="h-96">
              <BrowserViewer
                executionId={executionId}
                isRunning={isRunning}
                isPaused={isPaused}
                onPause={() => handleStatusChange('pause')}
                onResume={() => handleStatusChange('resume')}
                onRestart={() => handleStatusChange('restart')}
              />
            </div>
          )}

          {activeTab === 'timeline' && (
            <ExecutionTimeline
              events={execution.timeline}
              isLoading={isRunning}
            />
          )}

          {activeTab === 'artifacts' && (
            <ArtifactPreview
              executionId={executionId}
              artifacts={execution.artifacts}
            />
          )}
        </div>

        {/* Error Display */}
        {execution.error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-300 rounded-lg">
            <p className="text-red-900 font-semibold mb-2">Execution Error</p>
            <p className="text-red-800 text-sm break-all">{execution.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
