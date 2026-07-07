'use client';

import { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BrowserViewerProps {
  executionId: string;
  isRunning: boolean;
  isPaused: boolean;
  onPause?: () => void;
  onResume?: () => void;
  onRestart?: () => void;
}

export function BrowserViewer({
  executionId,
  isRunning,
  isPaused,
  onPause,
  onResume,
  onRestart,
}: BrowserViewerProps) {
  const [currentScreenshot, setCurrentScreenshot] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // Fetch list of available screenshots
    const fetchScreenshots = async () => {
      try {
        const response = await fetch(`/api/artifacts/${executionId}`);
        if (!response.ok) return;
        const data = await response.json();
        if (data.allScreenshots && data.allScreenshots.length > 0) {
          setScreenshots(data.allScreenshots);
          setCurrentScreenshot(data.allScreenshots[data.allScreenshots.length - 1]);
          setCurrentIndex(data.allScreenshots.length - 1);
          setIsLoading(false);
        }
      } catch (error) {
        console.error('[Browser Viewer] Fetch error:', error);
        setIsLoading(false);
      }
    };

    if (!isRunning) {
      // If not running, fetch completed screenshots once
      fetchScreenshots();
      return;
    }

    // During execution: poll for new screenshots every 500ms to show live updates
    setIsLoading(true);
    const pollInterval = setInterval(fetchScreenshots, 500);

    return () => {
      clearInterval(pollInterval);
    };
  }, [executionId, isRunning]);

  return (
    <div className="h-full flex flex-col bg-gray-50 rounded-lg overflow-hidden">
      <div className="bg-gray-100 border-b border-gray-300 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-500' : 'bg-gray-400'}`} />
          <span className="text-sm text-gray-600 font-mono">{executionId.slice(0, 8)}</span>
        </div>
        <div className="flex gap-2">
          {isRunning && !isPaused && (
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-600"
              onClick={onPause}
            >
              <Pause className="w-4 h-4" />
            </Button>
          )}
          {isPaused && (
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-600"
              onClick={onResume}
            >
              <Play className="w-4 h-4" />
            </Button>
          )}
          {!isRunning && (
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-600"
              onClick={onRestart}
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 bg-white flex items-center justify-center overflow-auto relative">
        {isLoading && isRunning ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-500 text-sm">Capturing screenshot...</p>
          </div>
        ) : currentScreenshot ? (
          <img
            src={currentScreenshot}
            alt="Browser view"
            className="max-w-full max-h-full object-contain"
          />
        ) : (
          <div className="text-center text-gray-500">
            <p>No screenshot available</p>
            {!isRunning && <p className="text-xs mt-2">Execution not running</p>}
          </div>
        )}
      </div>
    </div>
  );
}
