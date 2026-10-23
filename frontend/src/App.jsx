import { useEffect, useState } from 'react'

export default function App() {
  const [status, setStatus] = useState('…')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('nicht erreichbar'))
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui', padding: '2rem' }}>
      <h1>Victorinox Challenge</h1>
      <p>Backend: {status}</p>
    </main>
  )
}
