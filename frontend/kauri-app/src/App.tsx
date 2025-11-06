import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import DashboardLayout from './components/layout/DashboardLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import PlaceholderPage from './pages/PlaceholderPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Routes publiques */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Route Chat standalone (sans DashboardLayout) */}
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />

          {/* Routes protégées avec DashboardLayout */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route
              path="achats"
              element={<PlaceholderPage title="Achats" description="Gérez vos factures d'achat et fournisseurs" />}
            />
            <Route
              path="ventes"
              element={<PlaceholderPage title="Ventes" description="Gérez vos factures de vente et clients" />}
            />
            <Route
              path="banque"
              element={<PlaceholderPage title="Banque" description="Gérez vos comptes bancaires et rapprochements" />}
            />
            <Route
              path="immobilisations"
              element={<PlaceholderPage title="Immobilisations" description="Gérez vos actifs et amortissements" />}
            />
            <Route
              path="rapports"
              element={<PlaceholderPage title="Rapports" description="Consultez vos rapports financiers" />}
            />
          </Route>

          {/* Route par défaut */}
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
