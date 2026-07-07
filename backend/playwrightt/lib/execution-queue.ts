import { v4 as uuidv4 } from 'uuid';

export type ExecutionStatus = 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';

export interface TimelineEvent {
  timestamp: string;
  time: number;
  event: string;
  details?: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

export interface ExecutionMetadata {
  executionId: string;
  projectId?: string;
  requirementId?: string;
  scenarioIds?: string[];
  testCaseIds?: string[];
  browser: string;
  status: ExecutionStatus;
  started: string;
  finished?: string;
  duration?: number;
}

export interface ExecutionArtifacts {
  screenshots: string[];
  video?: string;
  trace?: string;
  htmlReport?: string;
  jsonReport?: string;
  logs: string[];
  console: string[];
}

export interface Execution {
  metadata: ExecutionMetadata;
  script: string;
  timeline: TimelineEvent[];
  artifacts: ExecutionArtifacts;
  error?: string;
}

class ExecutionQueueManager {
  private executions: Map<string, Execution> = new Map();
  private queue: string[] = [];
  private currentExecutionId: string | null = null;
  private maxConcurrent: number = 1;
  private pausedExecutions: Set<string> = new Set();

  createExecution(script: string, metadata?: Partial<ExecutionMetadata>): string {
    const executionId = uuidv4();
    const now = new Date().toISOString();

    const execution: Execution = {
      metadata: {
        executionId,
        projectId: metadata?.projectId,
        requirementId: metadata?.requirementId,
        scenarioIds: metadata?.scenarioIds,
        testCaseIds: metadata?.testCaseIds,
        browser: metadata?.browser || 'chromium',
        status: 'queued',
        started: now,
      },
      script,
      timeline: [
        {
          timestamp: now,
          time: 0,
          event: 'Execution Queued',
          type: 'info',
        },
      ],
      artifacts: {
        screenshots: [],
        logs: [],
        console: [],
      },
    };

    this.executions.set(executionId, execution);
    this.queue.push(executionId);

    return executionId;
  }

  getExecution(executionId: string): Execution | undefined {
    return this.executions.get(executionId);
  }

  getAllExecutions(): Execution[] {
    return Array.from(this.executions.values());
  }

  getQueue(): string[] {
    return this.queue;
  }

  addTimelineEvent(
    executionId: string,
    event: string,
    type: 'info' | 'success' | 'warning' | 'error' = 'info',
    details?: string
  ): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    const started = new Date(execution.metadata.started).getTime();
    const now = new Date().getTime();
    const elapsed = (now - started) / 1000;

    execution.timeline.push({
      timestamp: new Date().toISOString(),
      time: elapsed,
      event,
      details,
      type,
    });
  }

  setStatus(executionId: string, status: ExecutionStatus): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.metadata.status = status;

    if (status === 'completed' || status === 'failed' || status === 'stopped') {
      execution.metadata.finished = new Date().toISOString();
      const started = new Date(execution.metadata.started).getTime();
      const finished = new Date(execution.metadata.finished).getTime();
      execution.metadata.duration = (finished - started) / 1000;
    }

    this.addTimelineEvent(executionId, `Status: ${status}`, 'info');
  }

  pauseExecution(executionId: string): void {
    const execution = this.executions.get(executionId);
    if (!execution || execution.metadata.status !== 'running') return;

    this.pausedExecutions.add(executionId);
    this.setStatus(executionId, 'paused');
  }

  resumeExecution(executionId: string): void {
    const execution = this.executions.get(executionId);
    if (!execution || execution.metadata.status !== 'paused') return;

    this.pausedExecutions.delete(executionId);
    this.setStatus(executionId, 'running');
  }

  stopExecution(executionId: string): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    this.pausedExecutions.delete(executionId);
    this.setStatus(executionId, 'stopped');
  }

  addScreenshot(executionId: string, screenshotPath: string): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.artifacts.screenshots.push(screenshotPath);
    this.addTimelineEvent(executionId, 'Screenshot Captured', 'success', screenshotPath);
  }

  setArtifact(
    executionId: string,
    key: 'video' | 'trace' | 'htmlReport' | 'jsonReport',
    value: string
  ): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.artifacts[key] = value;
    this.addTimelineEvent(executionId, `${key} Generated`, 'success');
  }

  addLog(executionId: string, log: string): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.artifacts.logs.push(log);
  }

  addConsole(executionId: string, message: string): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.artifacts.console.push(message);
  }

  setError(executionId: string, error: string): void {
    const execution = this.executions.get(executionId);
    if (!execution) return;

    execution.error = error;
    this.addTimelineEvent(executionId, 'Error Occurred', 'error', error);
    this.setStatus(executionId, 'failed');
  }

  startNextExecution(): string | null {
    if (this.currentExecutionId) return null;
    if (this.queue.length === 0) return null;

    const executionId = this.queue.shift();
    if (!executionId) return null;

    const execution = this.executions.get(executionId);
    if (execution) {
      this.currentExecutionId = executionId;
      this.setStatus(executionId, 'running');
      this.addTimelineEvent(executionId, 'Browser Started', 'success');
    }

    return executionId;
  }

  completeExecution(executionId: string): void {
    if (this.currentExecutionId === executionId) {
      this.currentExecutionId = null;
    }
    this.setStatus(executionId, 'completed');
  }

  getCurrentExecution(): string | null {
    return this.currentExecutionId;
  }
}

// Global singleton instance
export const executionQueue = new ExecutionQueueManager();
