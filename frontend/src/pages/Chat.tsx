import { useEffect, useRef } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { useChatStream } from '../hooks/useChatStream'
import { ChatHeader } from '../components/ChatHeader'
import { MessageBubble } from '../components/MessageBubble'
import { ChatComposer } from '../components/ChatComposer'
import type { Message } from '../types'

interface LocationState { initialMessage?: string; useWikipedia?: boolean }

export default function Chat() {
  const { chatId: routeChatId } = useParams<{ chatId: string }>()
  const { state } = useLocation()
  const { initialMessage, useWikipedia: initialUseWikipedia } = (state as LocationState) || {}
  const { messages, isLoading, chatId, sendMessage } = useChatStream({
    initialMessage,
    initialUseWikipedia,
    initialChatId: routeChatId,
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    if (initialMessage && messages.length === 0) {
      // auto-send initial message once
      sendMessage(initialMessage)
    }
  }, [initialMessage, messages.length, sendMessage])

  return (
    <div className="min-h-screen bg-cohere-background flex flex-col">
      <ChatHeader chatId={chatId} routeChatId={routeChatId} wikipediaEnabled={Boolean(initialUseWikipedia)} />

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto">
          {messages.map((m: Message, i: number) => (<MessageBubble key={i} message={m} />))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <ChatComposer onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}
