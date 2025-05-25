import './index.css'  // This will contain our Tailwind imports
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import HomePage from './pages/home'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HomePage />
  </StrictMode>,
)
