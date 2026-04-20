import { useState } from 'react'
import type { ChatHistory } from './types'
import { LeftSidebar } from './components/LeftSidebar'
import { ChatWindow } from './components/ChatWindow'
import { RightSidebar } from './components/RightSidebar'
import './App.css'

function App() {
  const [chatHistory] = useState<ChatHistory[]>([
    { id: '1', title: 'Beach vacation photos' },
    { id: '2', title: 'Dog photos' },
    { id: '3', title: '2024 events' }
  ])

  const handleGenerateCaptions = () => {
    console.log('Generate captions clicked')
  }

  return (
    <div className="app-container">
      <LeftSidebar chatHistory={chatHistory} />
      <ChatWindow />
      <RightSidebar
        onGenerateCaptions={handleGenerateCaptions}
      />
    </div>
  )
}

export default App
