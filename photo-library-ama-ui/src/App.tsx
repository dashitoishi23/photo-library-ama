import { useState } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { RightSidebar } from './components/RightSidebar'
import './App.css'
import { env } from './env'

const API_URL = `http://${env.VITE_BACKEND_HOST}:${env.VITE_BACKEND_PORT}`

function App() {
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerateCaptions = async () => {
    setIsGenerating(true)
    try {
      await fetch(`${API_URL}/generate-captions`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="app-container">
      <ChatWindow />
      <RightSidebar
        onGenerateCaptions={handleGenerateCaptions}
        isGenerating={isGenerating}
      />
    </div>
  )
}

export default App
