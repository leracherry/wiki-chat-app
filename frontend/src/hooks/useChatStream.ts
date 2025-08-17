import { useCallback, useMemo, useRef, useState } from 'react'
import type { Message } from '../types'
import { streamChat } from '../services/api'

export interface UseChatStreamOptions {
  initialMessage?: string
  initialUseWikipedia?: boolean
  initialChatId?: string
}

export function useChatStream(opts: UseChatStreamOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([])
  const [chatId, setChatId] = useState<string | undefined>(opts.initialChatId)
  const [isLoading, setIsLoading] = useState(false)
  const [useWikipedia, setUseWikipedia] = useState(Boolean(opts.initialUseWikipedia))
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setMessages([])
    setIsLoading(false)
    setChatId(undefined)
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return
    setMessages((prev) => [...prev, { role: 'user', content }])
    setIsLoading(true)
    setMessages((prev) => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      for await (const evt of streamChat({ message: content, chatId, useWikipedia })) {
        switch (evt.type) {
          case 'chat_id':
            setChatId(evt.chat_id)
            break
          case 'text':
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                last.content += evt.text
              }
              return copy
            })
            break
          case 'tool':
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                last.isSearching = true
                last.searchQuery = evt.query
              }
              return copy
            })
            break
          case 'done':
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                last.isStreaming = false
                last.isSearching = false
              }
              return copy
            })
            break
          case 'error':
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                last.content = `Error: ${evt.error}`
                last.isStreaming = false
                last.isSearching = false
              }
              return copy
            })
            break
          default:
            // ignore
            break
        }
      }
    } finally {
      setIsLoading(false)
    }
  }, [chatId, isLoading, useWikipedia])

  const api = useMemo(() => ({ sendMessage, reset, setUseWikipedia }), [sendMessage, reset])
  return { messages, isLoading, chatId, useWikipedia, ...api }
}
