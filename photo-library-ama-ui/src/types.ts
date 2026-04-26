export interface PhotoMetadata {
  id: string
  caption: string
  filename: string
  date_taken: string
  location: string
  camera_make: string
  camera_model?: string
  gps_lat?: number
  gps_lon?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  photos?: string[]
  photoMetadata?: PhotoMetadata[]
}

export interface ChatHistory {
  id: string
  title: string
}
