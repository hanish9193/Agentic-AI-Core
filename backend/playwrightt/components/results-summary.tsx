'use client';

import { CheckCircle, AlertCircle, Clock, Image } from 'lucide-react';

interface ResultsSummaryProps {
  status: 'completed' | 'running' | 'failed';
  duration: number;
  screenshots: string[];
  timelineEvents: Array<{ event: string; time: number; type?: string }>;
  executionId: string;
}

export function ResultsSummary({
  status,
  duration,
  screenshots,
  timelineEvents,
  executionId,
}: ResultsSummaryProps) {
  const isPassed = status === 'completed';
  const statusColor = isPassed ? 'text-green-600' : 'text-red-600';
  const statusBgColor = isPassed ? 'bg-green-50' : 'bg-red-50';
  const statusBorder = isPassed ? 'border-green-200' : 'border-red-200';

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className={`${statusBgColor} border ${statusBorder} rounded-lg p-6`}>
        <div className="flex items-start gap-4">
          {isPassed ? (
            <CheckCircle className={`w-8 h-8 ${statusColor} flex-shrink-0 mt-1`} />
          ) : (
            <AlertCircle className={`w-8 h-8 ${statusColor} flex-shrink-0 mt-1`} />
          )}
          <div className="flex-1">
            <h2 className={`text-2xl font-bold ${statusColor} mb-1`}>
              {isPassed ? 'PASSED' : 'FAILED'}
            </h2>
            <p className="text-gray-600">Execution {executionId.slice(0, 8)}</p>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-300 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-600">Duration</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{duration.toFixed(2)}s</p>
        </div>

        <div className="bg-white border border-gray-300 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Image className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-600">Screenshots</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{screenshots.length}</p>
        </div>

        <div className="bg-white border border-gray-300 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-gray-600">Events</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{timelineEvents.length}</p>
        </div>
      </div>

      {/* Screenshots Gallery */}
      {screenshots.length > 0 && (
        <div className="bg-white border border-gray-300 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Screenshots ({screenshots.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {screenshots.map((screenshotUrl, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50 hover:shadow-md transition-shadow"
              >
                <div className="aspect-video bg-gray-200 flex items-center justify-center">
                  <img
                    src={screenshotUrl.startsWith('/') || screenshotUrl.startsWith('http') ? screenshotUrl : `/api/artifacts/${executionId}/screenshot/${screenshotUrl}`}
                    alt={`Screenshot ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="p-2 bg-white">
                  <p className="text-xs text-gray-600">
                    Screenshot {index + 1}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline Summary */}
      {timelineEvents.length > 0 && (
        <div className="bg-white border border-gray-300 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Execution Timeline
          </h3>
          <div className="space-y-2">
            {timelineEvents.slice(-5).map((event, index) => (
              <div
                key={index}
                className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0"
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      event.type === 'error'
                        ? 'bg-red-500'
                        : event.type === 'warning'
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                  />
                  <span className="text-sm text-gray-700">{event.event}</span>
                </div>
                <span className="text-xs text-gray-500 font-mono">
                  +{typeof event.time === 'number' ? event.time.toFixed(2) : event.time}s
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
