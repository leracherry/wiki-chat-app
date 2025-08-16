import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  isSearching?: boolean
  searchQuery?: string
}

interface LocationState {
  initialMessage?: string
  useWikipedia?: boolean
}

export default function ChatPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const location = useLocation()
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentChatId, setCurrentChatId] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Get initial data from router state instead of URL params
  const state = location.state as LocationState || {}
  const initialMessage = state.initialMessage
  const useWikipedia = state.useWikipedia || false

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isLoading) return

    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      const response = await fetch(`${apiUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          chat_id: currentChatId || chatId,
          use_wikipedia: useWikipedia,
        }),
      })

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'chat_id') {
                setCurrentChatId(data.chat_id)
              } else if (data.type === 'text') {
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content += data.text
                  }
                  return newMessages
                })
              } else if (data.type === 'tool') {
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    // Set search state without adding to content
                    lastMessage.isSearching = true
                    lastMessage.searchQuery = data.query
                  }
                  return newMessages
                })
              } else if (data.type === 'done') {
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.isStreaming = false
                    lastMessage.isSearching = false
                  }
                  return newMessages
                })
              } else if (data.type === 'error') {
                console.error('Stream error:', data.error)
              }
            } catch (e) {
              // Ignore JSON parse errors
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1] = {
          role: 'assistant',
          content: 'Sorry, there was an error connecting to the API. Please make sure the backend is running on port 8000.',
          isStreaming: false,
        }
        return newMessages
      })
    }

    setIsLoading(false)
  }, [apiUrl, currentChatId, chatId, useWikipedia, isLoading])

  useEffect(() => {
    if (initialMessage && messages.length === 0) {
      handleSendMessage(initialMessage)
    }
  }, [initialMessage, handleSendMessage, messages.length])

  return (
    <div className="min-h-screen bg-cohere-background flex flex-col">
      <div className="bg-white shadow-sm border-b border-cohere-border px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-cohere-dark">Chat Session</h1>
            <p className="text-sm text-cohere-dark/60">ID: {currentChatId || chatId}</p>
          </div>
          <div className="flex items-center space-x-4">
            {useWikipedia && (
              <span className="px-3 py-1 bg-wikipedia-label text-white text-sm rounded-full">
                Wikipedia Enabled
              </span>
            )}
            <Link
              to="/"
              className="px-4 py-2 inline-flex items-center justify-center bg-brand-base hover:bg-brand-hover text-white rounded-lg font-medium transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-hover/50 focus-visible:ring-offset-2"
            >
              New Chat
            </Link>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl px-4 py-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-user-message text-white'
                    : 'bg-white text-cohere-dark shadow-sm border border-cohere-border'
                }`}
              >
                {/* Wikipedia Search Indicator */}
                {message.isSearching && message.searchQuery && (
                  <div className="flex items-center gap-2 mb-3 p-2 bg-cohere-light/50 rounded border border-cohere-border/50">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-cohere-dark/30 border-t-cohere-dark rounded-full animate-spin"></div>
                      <span className="text-sm text-cohere-dark/70">
                        🔍 Searching Wikipedia for: <span className="font-medium">{message.searchQuery}</span>
                      </span>
                    </div>
                  </div>
                )}

                <div className="whitespace-pre-wrap">
                  {message.content}
                  {message.isStreaming && !message.isSearching && (
                    <span className="inline-block w-2 h-5 bg-cohere-dark/40 ml-1 animate-pulse" />
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  )
}
