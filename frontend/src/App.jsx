import { Navigate, Route, Routes } from 'react-router-dom'
import Header from './components/Header.jsx'
import ScanPage from './pages/ScanPage.jsx'
import AnalyzePage from './pages/AnalyzePage.jsx'
import ResultPage from './pages/ResultPage.jsx'
import ProductPage from './pages/ProductPage.jsx'

export default function App() {
  return (
    <div className="min-h-dvh">
      <Header />
      <main className="mx-auto w-full max-w-3xl px-4 pb-32 pt-4">
        <Routes>
          <Route path="/" element={<ScanPage />} />
          <Route path="/analyse/:scanId" element={<AnalyzePage />} />
          <Route path="/ergebnis/:scanId" element={<ResultPage />} />
          <Route path="/produkt/:artikelnummer" element={<ProductPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
