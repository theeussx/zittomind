/** Text Chat Completions client. Credentials are never placed in URLs. */
export class ZittoMind {
  constructor({ token, baseURL = 'http://127.0.0.1:8787', fetch: transport = globalThis.fetch }) {
    const url = new URL(baseURL);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('Invalid base URL');
    if (url.protocol === 'http:' && !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) throw new Error('Remote endpoints require HTTPS');
    if (!token) throw new Error('Proxy token required');
    this.baseURL = baseURL.replace(/\/$/, '');
    this.token = token;
    this.fetch = transport;
  }
  async request(messages, options, stream, signal) {
    const response = await this.fetch(`${this.baseURL}/v1/chat/completions`, {
      method: 'POST', headers: { 'Authorization': `Bearer ${this.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'auto', ...options, messages, stream }), signal, redirect: 'error'
    });
    if (!response.ok) throw new Error(`ZittoMind HTTP ${response.status}`);
    return response;
  }
  async chat(messages, options = {}, { signal } = {}) {
    return (await this.request(messages, options, false, signal)).json();
  }
  async *stream(messages, options = {}, { signal } = {}) {
    const response = await this.request(messages, options, true, signal);
    if (!response.body) throw new Error('Missing response stream');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        let end;
        while ((end = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, end).trim();
          buffer = buffer.slice(end + 1);
          if (!line.startsWith('data:')) continue;
          const data = line.slice(5).trim();
          if (data === '[DONE]') return;
          const event = JSON.parse(data);
          if (event.error) throw new Error('Upstream stream failed');
          yield event;
        }
        if (buffer.length > 1_000_000) throw new Error('Oversized stream event');
        if (done) throw new Error('Incomplete stream');
      }
    } finally {
      await reader.cancel();
      reader.releaseLock();
    }
  }
}
