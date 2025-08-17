import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Checkbox } from '../components/ui/Checkbox'
import { Textarea } from '../components/ui/Textarea'

export default function Home() {
  const [query, setQuery] = useState('')
  const [useWikipedia, setUseWikipedia] = useState(false)
  const navigate = useNavigate()

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    const chatId = Math.random().toString(36).slice(2, 9)
    navigate(`/chat/${chatId}`, { state: { initialMessage: query, useWikipedia } })
  }

  return (
    <div className="min-h-screen bg-cohere-background flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-[#39594d] mb-3">Wiki Chat Assistant</h1>
          <p className="text-ink/70 text-base sm:text-lg">Ask anything. Toggle Wikipedia for extra context when useful.</p>
        </div>

        <div className="bg-cohere-light rounded-2xl shadow-sm border border-cohere-border p-6 sm:p-8">
          <form onSubmit={onSubmit} className="space-y-6">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-ink mb-2">Your question</label>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Who was the second person to walk on the moon?"
                rows={4}
              />
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox id="use-wikipedia" checked={useWikipedia} onChange={setUseWikipedia} />
              <label htmlFor="use-wikipedia" className="text-sm text-ink">Search Wikipedia for additional context</label>
            </div>

            <Button type="submit" disabled={!query.trim()} className="w-full">Start Chat</Button>
          </form>
        </div>

        <div className="text-center mt-8">
          <p className="text-ink/50 text-sm">Powered by Cohere AI • Wikipedia integration available</p>
        </div>
      </div>
    </div>
  )
}
