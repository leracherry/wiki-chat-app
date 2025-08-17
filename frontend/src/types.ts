export type Role = 'user' | 'assistant'

export interface Message {
  role: Role
  content: string
  isStreaming?: boolean
  isSearching?: boolean
  searchQuery?: string
}

export type StreamEvent =
  | { type: 'chat_id'; chat_id: string }
  | { type: 'text'; text: string }
  | { type: 'tool'; query?: string }
  | { type: 'done' }
  | { type: 'error'; error: string }

