import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ZittoMind } from './index.js';

test('chat preserves context and sends bearer auth', async () => {
  const client = new ZittoMind({ token: 'secret', fetch: async (url, init) => {
    assert.equal(init.headers.Authorization, 'Bearer secret');
    assert.equal(JSON.parse(init.body).messages[0].content, 'hello');
    assert.equal(init.redirect, 'error');
    return Response.json({ choices: [{ message: { content: 'ok' } }] });
  }});
  assert.equal((await client.chat([{ role: 'user', content: 'hello' }])).choices[0].message.content, 'ok');
});
test('stream parses split chunks and rejects premature EOF', async () => {
  const encoder = new TextEncoder();
  const client = new ZittoMind({ token: 'secret', fetch: async () => new Response(new ReadableStream({ start(c) {
    c.enqueue(encoder.encode('data: {"cho'));
    c.enqueue(encoder.encode('ices":[]}\n\ndata: [DONE]\n\n')); c.close();
  }})) });
  const chunks = [];
  for await (const chunk of client.stream([])) chunks.push(chunk);
  assert.deepEqual(chunks, [{ choices: [] }]);
  client.fetch = async () => new Response('data: {"choices":[]}\n\n');
  await assert.rejects(async () => { for await (const event of client.stream([])) void event; }, /Incomplete/);
});
test('plain HTTP remote endpoints and missing credentials are rejected', () => {
  assert.throws(() => new ZittoMind({ token: 's', baseURL: 'http://example.com' }));
  assert.throws(() => new ZittoMind({ token: '' }));
});
