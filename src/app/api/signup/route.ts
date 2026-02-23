import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { name, phone, email } = await request.json();

    if (!name || (!phone && !email)) {
      return NextResponse.json({ success: false, error: 'Name and at least one contact method required' }, { status: 400 });
    }

    const githubToken = process.env.GITHUB_PAT;
    const repoOwner = process.env.GITHUB_OWNER; 
    const repoName = process.env.GITHUB_REPO;   

    if (!githubToken || !repoOwner || !repoName) {
      console.error('Missing GitHub configuration: PAT, Owner, or Repo');
      return NextResponse.json({ success: false, error: 'Server configuration error' }, { status: 500 });
    }

    const response = await fetch(
      `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/signup.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${githubToken}`,
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
          'User-Agent': 'NextJS-Signup-Bot',
        },
        body: JSON.stringify({
          ref: 'master', 
          inputs: { 
            name, 
            phone: phone || "", 
            email: email || "" 
          },
        }),
      }
    );

    if (response.ok || response.status === 204) {
      return NextResponse.json({ success: true, message: 'Signup processing' });
    } else {
      const errData = await response.text();
      console.error('GitHub API Error:', errData);
      return NextResponse.json({ success: false, error: 'Failed to trigger signup' }, { status: response.status });
    }
  } catch (error) {
    console.error('Signup Error:', error);
    return NextResponse.json({ success: false, error: 'Internal server error' }, { status: 500 });
  }
}
