export const AGENT_SERVER_URL = (
  import.meta.env.VITE_AGENT_SERVER_URL || 'http://localhost:8000'
).replace(/\/$/, '');

export async function postJson<T = any>(
  path: string,
  body?: any,
  options?: RequestInit
): Promise<T> {
  const url = `${AGENT_SERVER_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    throw new Error(`API POST ${path} failed with status ${res.status}: ${errorText}`);
  }

  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}
