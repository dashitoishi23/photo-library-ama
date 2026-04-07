import type { ChatHistory } from '../types'

interface LeftSidebarProps {
  chatHistory: ChatHistory[]
}

export function LeftSidebar({ chatHistory }: LeftSidebarProps) {
  return (
    <aside className="sidebar-left">
      <div className="sidebar-header">
        <h2>Chat History</h2>
      </div>
      <div className="chat-list">
        {chatHistory.map(chat => (
          <div key={chat.id} className="chat-item">{chat.title}</div>
        ))}
      </div>
    </aside>
  )
}
