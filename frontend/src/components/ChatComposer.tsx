import { useState } from 'react'
import { Button } from './ui/Button'
import { Textarea } from './ui/Textarea'

export function ChatComposer({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState('')

  const submit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const value = text.trim()
    if (!value || disabled) return
    onSend(value)
    setText('')
  }

  const onKeyDown: React.TextareaHTMLAttributes<HTMLTextAreaElement>['onKeyDown'] = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-cohere-border bg-cohere-light p-4">
      <div className="max-w-4xl mx-auto">
        <div className="relative">
          <Textarea
            value={text}
            onChange={(e) => setText(e.currentTarget.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a follow-up..."
            rows={3}
            className="pr-24 min-h-[3.5rem] resize-none"
          />
          <Button
            type="submit"
            disabled={disabled || !text.trim()}
            className="absolute bottom-5 right-4 py-2 px-4 text-sm rounded-lg"
            aria-label="Send message"
          >
            Send
          </Button>
        </div>
      </div>
    </form>
  )
}
