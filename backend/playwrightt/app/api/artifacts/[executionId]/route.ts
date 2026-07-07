import { NextRequest, NextResponse } from 'next/server';
import { executionQueue } from '@/lib/execution-queue';
import * as fs from 'fs/promises';
import * as path from 'path';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ executionId: string }> }
) {
  try {
    const params = await context.params;
    const { executionId } = params;

    // First try to get from execution queue
    const execution = executionQueue.getExecution(executionId);
    if (execution) {
      return NextResponse.json({
        executionId,
        artifacts: execution.artifacts,
        metadata: execution.metadata,
      });
    }

    // If execution not in queue, try to read screenshots from disk
    const screenshotsDir = path.join(
      process.cwd(),
      'public',
      'artifacts',
      executionId,
      'screenshots'
    );

    try {
      const files = await fs.readdir(screenshotsDir);
      // Filter for named screenshots (not live-XXXXX.png)
      const namedScreenshots = files
        .filter(f => f.endsWith('.png') && !f.startsWith('live-'))
        .sort();

      const allScreenshots = files.filter(f => f.endsWith('.png')).sort();
      const screenshotUrls = namedScreenshots.map(
        f => `/api/artifacts/${executionId}/screenshot/${f}`
      );
      const allScreenshotUrls = allScreenshots.map(
        f => `/api/artifacts/${executionId}/screenshot/${f}`
      );

      return NextResponse.json({
        executionId,
        screenshots: screenshotUrls,
        allScreenshots: allScreenshotUrls,
      });
    } catch (err) {
      return NextResponse.json({ error: 'Execution not found' }, { status: 404 });
    }
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
