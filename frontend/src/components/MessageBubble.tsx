import type { Message } from '../types'
import { cx } from '../utils/cx'

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cx('flex mb-4', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cx(
        'max-w-3xl px-4 py-3 rounded-2xl',
        isUser ? 'bg-brand-base text-white ml-12' : 'bg-cohere-light border border-cohere-border mr-12'
      )}>
        {!isUser && message.isSearching && (
          <div className="mb-2 text-sm text-ink/60 flex items-center">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-brand-base mr-2" />
            Searching Wikipedia{message.searchQuery ? ` for: ${message.searchQuery}` : ''}
          </div>
        )}
        <div className="whitespace-pre-wrap">
          {message.content}
          {!isUser && message.isStreaming && (
            <span className="inline-block w-2 h-5 bg-brand-base animate-pulse ml-1" />
          )}
        </div>
      </div>
    </div>
  )
}

