'use client';

import { Execution, ExecutionStatus } from '@/lib/execution-queue';
import { Button } from '@/components/ui/button';
import { Play, Pause, X, RotateCw } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface ExecutionListProps {
  executions: Execution[];
  queue: string[];
  current: string | null;
  onStatusChange: (executionId: string, action: string) => void;
}

function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 border border-green-300';
    case 'running':
      return 'bg-blue-100 text-blue-800 border border-blue-300';
    case 'paused':
      return 'bg-yellow-100 text-yellow-800 border border-yellow-300';
    case 'failed':
      return 'bg-red-100 text-red-800 border border-red-300';
    case 'stopped':
      return 'bg-gray-100 text-gray-800 border border-gray-300';
    case 'queued':
    default:
      return 'bg-purple-100 text-purple-800 border border-purple-300';
  }
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${mins}m ${secs}s`;
}

export function ExecutionList({
  executions,
  queue,
  current,
  onStatusChange,
}: ExecutionListProps) {
  const router = useRouter();

  return (
    <div className="bg-white rounded-lg border border-gray-300 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-300">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-900">
                Execution ID
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-900">
                Status
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-900">
                Duration
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-900">
                Started
              </th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {executions.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No executions yet
                </td>
              </tr>
            ) : (
              executions.map((execution) => (
                <tr
                  key={execution.metadata.executionId}
                  className="border-b border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() =>
                    router.push(`/execution/${execution.metadata.executionId}`)
                  }
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">
                    {execution.metadata.executionId.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        execution.metadata.status
                      )}`}
                    >
                      {execution.metadata.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    {formatDuration(execution.metadata.duration)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(execution.metadata.started).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div
                      className="flex gap-2 justify-end"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {execution.metadata.status === 'running' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            onStatusChange(execution.metadata.executionId, 'pause')
                          }
                        >
                          <Pause className="w-4 h-4" />
                        </Button>
                      )}
                      {execution.metadata.status === 'paused' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            onStatusChange(execution.metadata.executionId, 'resume')
                          }
                        >
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                      {(execution.metadata.status === 'running' ||
                        execution.metadata.status === 'paused' ||
                        execution.metadata.status === 'queued') && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            onStatusChange(execution.metadata.executionId, 'stop')
                          }
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
