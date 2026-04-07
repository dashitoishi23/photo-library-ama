import type { Message } from '../types'

export interface ChatWindowProps {
  messages: Message[]
  input: string
  onInputChange: (value: string) => void
  onSend: () => void
}

export function ChatWindow({ messages, input, onInputChange, onSend }: ChatWindowProps) {
  return (
    <main className="chat-main">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSend()}
          placeholder="Ask about your photos..."
        />
        <button onClick={onSend}>Send</button>
      </div>
    </main>
  )
}
