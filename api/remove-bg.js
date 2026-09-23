export const config = { runtime: 'edge' };

export default async function handler(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const apiKey = process.env.REMOVE_BG_API_KEY;
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'REMOVE_BG_API_KEY not set in Vercel environment variables' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  let formData;
  try {
    formData = await request.formData();
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Invalid form data' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const imageFile = formData.get('image_file');
  if (!imageFile) {
    return new Response(JSON.stringify({ error: 'No image_file provided' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const outForm = new FormData();
  outForm.append('image_file', imageFile);
  outForm.append('size', 'auto');

  const resp = await fetch('https://api.remove.bg/v1.0/removebg', {
    method: 'POST',
    headers: { 'X-Api-Key': apiKey },
    body: outForm,
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ errors: [{ title: resp.statusText }] }));
    const msg = body?.errors?.[0]?.title || 'remove.bg request failed';
    return new Response(JSON.stringify({ error: msg }), {
      status: resp.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const resultBuffer = await resp.arrayBuffer();
  return new Response(resultBuffer, {
    headers: {
      'Content-Type': 'image/png',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
