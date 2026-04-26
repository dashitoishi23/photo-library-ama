import { useState } from 'react'
import type { Message, PhotoMetadata } from '../types'
import { env } from '../env'

const API_URL = `http://${env.VITE_BACKEND_HOST}:${env.VITE_BACKEND_PORT}`

interface LLMResponse {
  result: string
  tool_call: {
    tool: string
    args: {
      query: string
      n_results: number
    }
  } | null
  photo_results: string
  photo_metadata?: PhotoMetadata[]
}

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I can answer questions about your photos. Ask me anything!' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null)

  const handleSend = async () => {
    if (!input.trim() || loading) return
    
    const userQuery = input
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: userQuery }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    
    try {
      const response = await fetch(`${API_URL}/llm_call`, {//
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery, max_iterations: 10 })
      })
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }
      
      const data: LLMResponse = await response.json()
      console.log({ data })
      
      let content = ''
      let photos: string[] = []
      let photoMetadata: PhotoMetadata[] = []

      // let responseData: ResponseData = {
      //   user_query: '',
      //   response_photos: [],
      //   response_additional_text: '',
      //   timestamp: ''
      // };
      
      if (data.tool_call === null) {
        content = data.result || ''
      } else {
        const searchResults = (data.result as any).results || []
        photos = searchResults.map((r: PhotoMetadata) => r.id)
        photoMetadata = searchResults
      }
      
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content,
        photos,
        photoMetadata
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (error) {
      console.error('Error calling LLM:', error)
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="chat-main">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
            {msg.photos && msg.photos.length > 0 && (
              <div className="message-photos">
                {msg.photos.slice(0, 4).map((photo, idx) => (
                  <div key={idx} className="photo-tooltip-container">
                    <img 
                      src={`${API_URL}/photos/${photo}`} 
                      alt={`Photo ${idx + 1}`}
                      onClick={() => setSelectedPhoto(photo)}
                      style={{ cursor: 'pointer' }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about your photos..."
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
      {selectedPhoto && (
        <div className="photo-popup" onClick={() => setSelectedPhoto(null)}>
          <img 
            src={`${API_URL}/photos/${selectedPhoto}`} 
            alt="Full size" 
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </main>
  )
}
