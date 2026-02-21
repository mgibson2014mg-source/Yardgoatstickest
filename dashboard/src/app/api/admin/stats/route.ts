import { NextRequest, NextResponse } from 'next/server';
import { getAdminStats, getSyncStatus } from '@/lib/db';

export async function GET(request: NextRequest) {
  // Simple MVP security check
  const { searchParams } = new URL(request.url);
  const key = searchParams.get('key');
  
  if (process.env.ADMIN_KEY && key !== process.env.ADMIN_KEY) {
    return NextResponse.json({ success: false, error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const stats = getAdminStats();
    const lastSync = getSyncStatus();

    return NextResponse.json({
      success: true,
      stats,
      lastSync,
    });
  } catch (error) {
    console.error('Admin API Error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch admin stats' },
      { status: 500 }
    );
  }
}
