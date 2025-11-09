import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import OAuthButtons from '../components/auth/OAuthButtons';

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3201';
const ENABLE_OAUTH = import.meta.env.VITE_ENABLE_OAUTH === 'true';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showResendButton, setShowResendButton] = useState(false);
  const [resendingEmail, setResendingEmail] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setShowResendButton(false);
    setResendSuccess(false);
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/chat');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Email ou mot de passe incorrect';
      setError(errorMessage);

      // Si l'erreur indique que l'email n'est pas vérifié, afficher le bouton de renvoi
      if (errorMessage.includes('vérifier votre adresse email')) {
        setShowResendButton(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingEmail(true);
    setError('');
    setResendSuccess(false);

    try {
      const response = await fetch(`${USER_SERVICE_URL}/api/v1/verification/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (response.ok) {
        setResendSuccess(true);
        setShowResendButton(false);
      } else {
        const data = await response.json();
        setError(data.detail || 'Erreur lors de l\'envoi de l\'email');
      }
    } catch (error) {
      setError('Une erreur est survenue. Veuillez réessayer.');
    } finally {
      setResendingEmail(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-5">
          {/* Logo et titre */}
          <div className="text-center mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Kauri</h1>
          </div>

          {/* Formulaire */}
          <form onSubmit={handleSubmit} className="space-y-2">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
                {showResendButton && (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendingEmail}
                    className="mt-3 w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {resendingEmail ? 'Envoi en cours...' : 'Renvoyer l\'email de vérification'}
                  </button>
                )}
              </div>
            )}

            {resendSuccess && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                Email de vérification renvoyé avec succès! Consultez votre boîte de réception.
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-gray-700 mb-0.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition text-sm"
                placeholder="votre@email.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-gray-700 mb-0.5">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-1.5 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition text-sm"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed mt-3"
            >
              {isLoading ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>

          {/* OAuth Buttons */}
          {ENABLE_OAUTH && (
            <div className="mt-4">
              <OAuthButtons />
            </div>
          )}

          {/* Lien vers inscription */}
          <div className="mt-4 text-center">
            <p className="text-gray-600 text-sm">
              Pas encore de compte ?{' '}
              <Link to="/register" className="text-green-600 hover:text-green-700 font-medium">
                S'inscrire
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-600 mt-6">
          © 2025 Kauri. Tous droits réservés.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
