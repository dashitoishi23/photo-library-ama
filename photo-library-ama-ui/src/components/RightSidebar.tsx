export interface RightSidebarProps {
  totalPhotos: number
  vectorDbEntries: number
  onGenerateCaptions: () => void
}

export function RightSidebar({ totalPhotos, vectorDbEntries, onGenerateCaptions }: RightSidebarProps) {
  const isMismatch = totalPhotos !== vectorDbEntries

  return (
    <aside className="sidebar-right">
      <div className="sidebar-header">
        <h2>Stats</h2>
      </div>
      <div className="stats">
        <div className="stat-item">
          <span className="stat-label">Total Photos</span>
          <span className="stat-value">{totalPhotos}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Vector DB Entries</span>
          <span className="stat-value">{vectorDbEntries}</span>
        </div>
        {isMismatch && (
          <div className="stat-mismatch">
            <span>Photos: {totalPhotos} | Vectors: {vectorDbEntries}</span>
          </div>
        )}
        <button className="generate-btn" onClick={onGenerateCaptions}>
          Generate Captions
        </button>
      </div>
    </aside>
  )
}
