import { useEffect, useState } from 'react'
import { env } from '../env'

const API_URL = `http://${env.VITE_BACKEND_HOST}:${env.VITE_BACKEND_PORT}`

export interface RightSidebarProps {
  onGenerateCaptions: () => void
  isGenerating: boolean
}

interface Stats {
  total_photos: number
  vector_db_entries: number
}

export function RightSidebar({ onGenerateCaptions, isGenerating }: RightSidebarProps) {
  const [stats, setStats] = useState<Stats>({ total_photos: 0, vector_db_entries: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/get-stats`)
      .then(res => res.json())
      .then(data => setStats({
        total_photos: data.photo_count || 0,
        vector_db_entries: data.chroma_count || 0
      }))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const { total_photos, vector_db_entries } = stats
  const isMismatch = total_photos !== vector_db_entries

  return (
    <aside className="sidebar-right">
      <div className="sidebar-header">
        <h2>Stats</h2>
      </div>
      <div className="stats">
        <div className="stat-item">
          <span className="stat-label">Total Photos</span>
          <span className="stat-value">{loading ? '...' : total_photos}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Vector DB Entries</span>
          <span className="stat-value">{loading ? '...' : vector_db_entries}</span>
        </div>
        {isMismatch && (
          <div className="stat-mismatch">
            <span>Photos: {total_photos} | Vectors: {vector_db_entries}</span>
          </div>
        )}
        <button className="generate-btn" onClick={onGenerateCaptions} disabled={isGenerating}>
          {isGenerating ? 'Generating...' : 'Generate Captions'}
        </button>
      </div>
    </aside>
  )
}
