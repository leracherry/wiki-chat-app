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
    <div className="min-h-screen bg-cohere-background flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-cohere-dark mb-4">
            Wiki Chat Assistant
          </h1>
          <p className="text-cohere-dark/70 text-lg">
            Ask me anything and I can search Wikipedia for additional context
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-lg border border-cohere-border p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-cohere-dark mb-2">
                Your Question
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Who was the second person to walk on the moon?"
                className="w-full px-4 py-3 border border-cohere-border rounded-lg focus:ring-2 focus:ring-cohere-dark focus:border-cohere-dark resize-none bg-cohere-background/50"
                rows={4}
              />
            </div>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="wikipedia"
                checked={useWikipedia}
                onChange={(e) => setUseWikipedia(e.target.checked)}
                className="h-4 w-4 text-cohere-dark focus:ring-cohere-dark border-cohere-border rounded"
              />
              <label htmlFor="wikipedia" className="text-sm font-medium text-cohere-dark">
                Use Wikipedia for additional context
              </label>
            </div>

            <button
              type="submit"
              disabled={!query.trim()}
              className="w-full inline-flex items-center justify-center bg-brand-base hover:bg-brand-hover text-white py-3 px-6 rounded-lg font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-hover/50 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              Send Message
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
