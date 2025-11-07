import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { oauthLogin } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Éviter le double traitement
      if (isProcessing) return;
      setIsProcessing(true);

      // Get token from URL params
      const token = searchParams.get('token');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        // Handle OAuth error
        const errorMessages: Record<string, string> = {
          invalid_provider: 'Provider OAuth invalide',
          invalid_state: 'Session OAuth expirée ou invalide',
          no_token: 'Échec de l\'obtention du token',
          no_user_info: 'Impossible de récupérer les informations utilisateur',
          user_creation_failed: 'Échec de la création du compte',
          oauth_failed: 'Échec de l\'authentification OAuth',
        };

        setError(errorMessages[errorParam] || 'Erreur d\'authentification OAuth');

        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 3000);
        return;
      }

      if (token) {
        try {
          // Use the new oauthLogin method from AuthContext
          await oauthLogin(token);

          // Redirect to chat - utiliser replace pour éviter le retour arrière
          navigate('/chat', { replace: true });
        } catch (err) {
          console.error('Failed to complete OAuth login:', err);
          setError('Échec de la connexion OAuth');

          // Redirect to login after 3 seconds
          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 3000);
        }
      } else {
        setError('Token manquant dans la réponse OAuth');

        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, oauthLogin, isProcessing]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center">
            {error ? (
              <>
                <div className="mb-4">
                  <svg
                    className="mx-auto h-12 w-12 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Erreur d'authentification</h2>
                <p className="text-gray-600 mb-4">{error}</p>
                <p className="text-sm text-gray-500">Redirection vers la page de connexion...</p>
              </>
            ) : (
              <>
                <div className="mb-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Connexion en cours</h2>
                <p className="text-gray-600">Veuillez patienter...</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;
