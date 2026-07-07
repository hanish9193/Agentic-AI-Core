import { NextRequest, NextResponse } from 'next/server';
import { executionQueue } from '@/lib/execution-queue';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (id) {
      // Get single execution
      const execution = executionQueue.getExecution(id);
      if (!execution) {
        return NextResponse.json(
          { error: 'Execution not found' },
          { status: 404 }
        );
      }
      return NextResponse.json(execution);
    } else {
      // Get all executions
      const executions = executionQueue.getAllExecutions();
      const queue = executionQueue.getQueue();
      return NextResponse.json({ 
        executions,
        queue,
        current: executionQueue.getCurrentExecution(),
      });
    }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    const action = searchParams.get('action');

    if (!id || !action) {
      return NextResponse.json(
        { error: 'Missing id or action' },
        { status: 400 }
      );
    }

    const execution = executionQueue.getExecution(id);
    if (!execution) {
      return NextResponse.json(
        { error: 'Execution not found' },
        { status: 404 }
      );
    }

    switch (action) {
      case 'pause':
        executionQueue.pauseExecution(id);
        break;
      case 'resume':
        executionQueue.resumeExecution(id);
        break;
      case 'stop':
        executionQueue.stopExecution(id);
        break;
      default:
        return NextResponse.json(
          { error: 'Invalid action' },
          { status: 400 }
        );
    }

    return NextResponse.json(execution);
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}
