import { useLayoutEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Header from './components/Header.jsx'
import ScanPage from './pages/ScanPage.jsx'
import AnalyzePage from './pages/AnalyzePage.jsx'
import ResultPage from './pages/ResultPage.jsx'
import ProductPage from './pages/ProductPage.jsx'
import PresentationPage from './pages/PresentationPage.jsx'
import HandyPage from './pages/HandyPage.jsx'

export default function App() {
  const { pathname, hash } = useLocation()
  const isPresentation = pathname === '/praesentation'

  // Neue Seite beginnt oben; sonst bleibt die Scrollposition der vorherigen Seite stehen.
  // Mit #Anker (z. B. /praesentation#beweis) scrollt die Seite selbst zum Ziel.
  useLayoutEffect(() => {
    if (!hash) window.scrollTo(0, 0)
  }, [pathname])
  return (
    <div className="min-h-dvh">
      {!isPresentation && <Header />}
      <main className={`mx-auto w-full ${isPresentation ? 'max-w-none' : 'max-w-3xl px-4 pt-4 pb-32'}`}>
        <Routes>
          <Route path="/praesentation" element={<PresentationPage />} />
          <Route path="/" element={<ScanPage />} />
          <Route path="/analyse/:scanId" element={<AnalyzePage />} />
          <Route path="/ergebnis/:scanId" element={<ResultPage />} />
          <Route path="/produkt/:artikelnummer" element={<ProductPage />} />
          <Route path="/handy/:sitzungId" element={<HandyPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
