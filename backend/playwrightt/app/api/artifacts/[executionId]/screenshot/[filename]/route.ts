import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs/promises';
import * as path from 'path';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ executionId: string; filename: string }> }
) {
  try {
    const params = await context.params;
    const { executionId, filename } = params;
    const artifactPath = path.join(
      process.cwd(),
      'public',
      'artifacts',
      executionId,
      'screenshots',
      filename
    );

    const fileBuffer = await fs.readFile(artifactPath);
    return new Response(fileBuffer, {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: 'Screenshot not found' }, { status: 404 });
  }
}
