export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  photos?: string[]
}

export interface ChatHistory {
  id: string
  title: string
}
