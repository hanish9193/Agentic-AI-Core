import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs/promises';
import * as path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: { executionId: string } }
) {
  try {
    const { executionId } = params;
    const tracePath = path.join(
      process.cwd(),
      'public',
      'artifacts',
      executionId,
      'trace',
      'trace.zip'
    );

    const fileBuffer = await fs.readFile(tracePath);
    return new Response(fileBuffer, {
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="trace-${executionId}.zip"`,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: 'Trace not found' }, { status: 404 });
  }
}
