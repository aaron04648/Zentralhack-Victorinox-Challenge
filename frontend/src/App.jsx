import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Header from './components/Header.jsx'
import ScanPage from './pages/ScanPage.jsx'
import AnalyzePage from './pages/AnalyzePage.jsx'
import ResultPage from './pages/ResultPage.jsx'
import ProductPage from './pages/ProductPage.jsx'
import PresentationPage from './pages/PresentationPage.jsx'
import HandyPage from './pages/HandyPage.jsx'

export default function App() {
  const { pathname } = useLocation()
  const isPresentation = pathname === '/praesentation'
  return (
    <div className="min-h-dvh">
      <Header />
      <main className={`mx-auto w-full ${isPresentation ? 'max-w-none px-0 pt-0' : 'max-w-3xl px-4 pt-4'} pb-32`}>
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
