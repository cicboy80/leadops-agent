import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

async function proxyRequest(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join('/');
  const url = new URL(`/api/${path}`, BACKEND_URL);

  // Forward query params
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();
  for (const [key, value] of req.headers.entries()) {
    if (['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) continue;
    headers.set(key, value);
  }

  // Inject API key server-side so it never reaches the browser
  const apiKey = process.env.API_KEY || 'dev-api-key-change-me';
  headers.set('X-API-Key', apiKey);

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const contentType = req.headers.get('content-type') || '';
    if (contentType.includes('multipart/form-data')) {
      // Forward binary body as-is (file uploads)
      fetchOptions.body = await req.arrayBuffer();
      // Keep the original content-type with boundary
      headers.set('content-type', contentType);
    } else {
      fetchOptions.body = await req.text();
    }
  }

  const response = await fetch(url.toString(), fetchOptions);

  const responseHeaders = new Headers();
  for (const [key, value] of response.headers.entries()) {
    if (['transfer-encoding', 'content-encoding'].includes(key.toLowerCase())) continue;
    responseHeaders.set(key, value);
  }

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params);
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params);
}
export async function PUT(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params);
}
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params);
}
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params);
}
