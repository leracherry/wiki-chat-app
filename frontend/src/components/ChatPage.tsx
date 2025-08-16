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
  const state = (location.state as LocationState) || {}
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

      let completed = false
      while (!completed) {
        const { done, value } = await reader.read()
        if (done) {
          completed = true
          break
        }

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
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = `Error: ${data.error}`
                    lastMessage.isStreaming = false
                    lastMessage.isSearching = false
                  } else {
                    newMessages.push({ role: 'assistant', content: `Error: ${data.error}` })
                  }
                  return newMessages
                })
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
      <div className="bg-cohere-light/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg sm:text-xl font-semibold text-[#39594d]">Chat Session</h1>
            <p className="text-xs sm:text-sm text-ink/60">ID: {currentChatId || chatId}</p>
          </div>
          <div className="flex items-center space-x-3 sm:space-x-4">
            {useWikipedia && (
              <span className="hidden sm:inline px-3 py-1 bg-wikipedia-label/20 text-wikipedia-label border border-wikipedia-label text-sm rounded-full">
                Wikipedia Enabled
              </span>
            )}
            <Link
              to="/"
              className="px-4 py-2 inline-flex items-center justify-center bg-brand-base text-white rounded-lg font-medium transition duration-200 hover:brightness-95 active:brightness-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-base/50 focus-visible:ring-offset-2"
            >
              Start New Chat
            </Link>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        <div className="max-w-4xl mx-auto px-4 space-y-4 sm:space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl px-4 py-3 rounded-2xl ${
                  message.role === 'user'
                    ? 'bg-user-message text-white shadow-sm'
                    : 'bg-cohere-light text-ink shadow-sm'
                }`}
              >
                {/* Wikipedia Search Indicator */}
                {message.isSearching && message.searchQuery && (
                  <div className={`flex items-center gap-2 ${message.content?.trim() ? 'mb-3' : ''} p-2 rounded-lg border bg-accent/10 border-accent/30`}>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-ink/20 border-t-ink rounded-full animate-spin"></div>
                      <span className="text-sm text-ink/70">
                        🔍 Searching Wikipedia for: <span className="font-medium text-ink">{message.searchQuery}</span>
                      </span>
                    </div>
                  </div>
                )}

                <div className="whitespace-pre-wrap leading-relaxed">
                  {message.content}
                  {message.isStreaming && !message.isSearching && (
                    <span className="inline-block w-2 h-5 bg-ink/40 ml-1 animate-pulse align-[-0.15em]" />
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
