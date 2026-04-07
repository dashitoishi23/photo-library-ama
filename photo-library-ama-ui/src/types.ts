export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface ChatHistory {
  id: string
  title: string
}
