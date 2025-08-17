import type { StreamEvent } from '../types'

const { VITE_API_URL } = import.meta.env
const API_BASE = VITE_API_URL ?? 'http://localhost:8000'

export interface StreamChatParams {
  message: string
  chatId?: string
  useWikipedia?: boolean
}

export async function* streamChat(params: StreamChatParams): AsyncGenerator<StreamEvent, void, unknown> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: params.message,
      chat_id: params.chatId,
      use_wikipedia: Boolean(params.useWikipedia),
    }),
  })

  if (!res.ok || !res.body) {
    const text = await (async () => {
      try { return await res.text() } catch { return '' }
    })()
    yield { type: 'error', error: text || `HTTP ${res.status}` }
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6)
      try {
        const evt = JSON.parse(payload) as StreamEvent
        yield evt
      } catch {
        // ignore malformed chunks
      }
    }
  }
}

export async function complete(prompt: string, opts?: { max_tokens?: number; temperature?: number; model?: string }) {
  const res = await fetch(`${API_BASE}/api/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, ...opts }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<{ id: string; output: string; finish_reason: string; usage?: unknown }>
}

export async function health() {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<{ status: string }>
}
