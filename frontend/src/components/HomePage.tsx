import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [useWikipedia, setUseWikipedia] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    const chatId = Math.random().toString(36).substring(2, 15)

    // Navigate with clean URL, passing data through state
    navigate(`/chat/${chatId}`, {
      state: {
        initialMessage: query,
        useWikipedia: useWikipedia
      }
    })
  }

  return (
    <div className="min-h-screen bg-cohere-background flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-[#39594d] mb-3">
            Wiki Chat Assistant
          </h1>
          <p className="text-ink/70 text-base sm:text-lg">
            Ask anything. Toggle Wikipedia for extra context when useful.
          </p>
        </div>

        <div className="bg-cohere-light rounded-2xl shadow-sm border border-cohere-border p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-ink mb-2">
                Your question
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Who was the second person to walk on the moon?"
                className="w-full px-4 py-3 border border-cohere-border rounded-xl bg-cohere-background shadow-sm placeholder:text-ink/40 focus:ring-2 focus:ring-brand-base/50 focus:border-brand-base resize-none"
                rows={4}
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="wikipedia"
                checked={useWikipedia}
                onChange={(e) => setUseWikipedia(e.target.checked)}
                className="h-4 w-4 text-brand-base focus:ring-brand-base border-cohere-border rounded"
              />
              <label htmlFor="wikipedia" className="text-sm font-medium text-ink">
                Use Wikipedia for additional context
              </label>
            </div>

            <button
              type="submit"
              disabled={!query.trim()}
              className="w-full inline-flex items-center justify-center bg-brand-base text-white py-3 px-6 rounded-lg font-medium shadow-sm hover:brightness-95 active:brightness-90 transition duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-base/50 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send Message
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
