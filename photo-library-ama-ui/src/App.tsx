import { useState } from 'react'
import type { Message, ChatHistory } from './types'
import { LeftSidebar } from './components/LeftSidebar'
import { ChatWindow } from './components/ChatWindow'
import { RightSidebar } from './components/RightSidebar'
import './App.css'

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I can answer questions about your photos. Ask me anything!' }
  ])
  const [input, setInput] = useState('')
  const [chatHistory] = useState<ChatHistory[]>([
    { id: '1', title: 'Beach vacation photos' },
    { id: '2', title: 'Dog photos' },
    { id: '3', title: '2024 events' }
  ])

  const totalPhotos = 0
  const vectorDbEntries = 0

  const handleSend = () => {
    if (!input.trim()) return
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
  }

  const handleGenerateCaptions = () => {
    console.log('Generate captions clicked')
  }

  return (
    <div className="app-container">
      <LeftSidebar chatHistory={chatHistory} />
      <ChatWindow
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
      />
      <RightSidebar
        totalPhotos={totalPhotos}
        vectorDbEntries={vectorDbEntries}
        onGenerateCaptions={handleGenerateCaptions}
      />
    </div>
  )
}

export default App
