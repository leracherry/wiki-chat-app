import { Link } from 'react-router-dom'

export function ChatHeader({ chatId, routeChatId, wikipediaEnabled }: { chatId?: string; routeChatId?: string; wikipediaEnabled?: boolean }) {
  return (
    <div className="bg-cohere-light border-b border-cohere-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-brand-base hover:text-brand-base/80 font-medium">← New Chat</Link>
          <div className="text-ink/60 text-sm">Chat ID: {chatId || routeChatId}</div>
        </div>
        <div className="flex items-center text-sm text-ink/60">
          <span className={`w-2 h-2 rounded-full mr-2 ${wikipediaEnabled ? 'bg-green-500' : 'bg-ink/30'}`} />
          Wikipedia {wikipediaEnabled ? 'enabled' : 'disabled'}
        </div>
      </div>
    </div>
  )
}

