import React, { useState, useEffect } from 'react';
import { Facebook, Linkedin, Twitter } from 'lucide-react';

// Official Google logo component
const GoogleIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:8001';

interface OAuthProvider {
  name: string;
  displayName: string;
  icon: React.ReactNode;
  color: string;
  hoverColor: string;
  enabled: boolean;
}

const OAuthButtons: React.FC = () => {
  const [providers, setProviders] = useState<Record<string, boolean>>({
    google: false,
    facebook: false,
    linkedin: false,
    twitter: false,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [hasProviderError, setHasProviderError] = useState(false);

  useEffect(() => {
    // Fetch available OAuth providers
    const fetchProviders = async () => {
      try {
        const response = await fetch(`${USER_SERVICE_URL}/api/v1/oauth/providers`);
        if (!response.ok) {
          throw new Error(`Provider endpoint returned ${response.status}`);
        }
        const data = await response.json();
        setProviders(data?.providers || {});
        setHasProviderError(false);
      } catch (error) {
        console.error('Failed to fetch OAuth providers:', error);
        setProviders({
          google: false,
          facebook: false,
          linkedin: false,
          twitter: false,
        });
        setHasProviderError(true);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProviders();
  }, []);

  const handleOAuthLogin = (provider: string) => {
    // Redirect to OAuth login endpoint
    window.location.href = `${USER_SERVICE_URL}/api/v1/oauth/login/${provider}`;
  };

  const oauthProviders: OAuthProvider[] = [
    {
      name: 'google',
      displayName: 'Google',
      icon: <GoogleIcon className="w-5 h-5" />,
      color: 'bg-white border border-gray-300 text-gray-700',
      hoverColor: 'hover:bg-gray-50',
      enabled: providers.google,
    },
    {
      name: 'facebook',
      displayName: 'Facebook',
      icon: <Facebook className="w-5 h-5" />,
      color: 'bg-blue-600 text-white',
      hoverColor: 'hover:bg-blue-700',
      enabled: providers.facebook,
    },
    {
      name: 'linkedin',
      displayName: 'LinkedIn',
      icon: <Linkedin className="w-5 h-5" />,
      color: 'bg-blue-700 text-white',
      hoverColor: 'hover:bg-blue-800',
      enabled: providers.linkedin,
    },
    {
      name: 'twitter',
      displayName: 'Twitter',
      icon: <Twitter className="w-5 h-5" />,
      color: 'bg-sky-500 text-white',
      hoverColor: 'hover:bg-sky-600',
      enabled: providers.twitter,
    },
  ];

  const enabledProviders = (oauthProviders || []).filter(p => !!p && p.enabled);

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
      </div>
    );
  }

  if (hasProviderError || enabledProviders.length === 0) {
    return null; // Don't show anything if no providers are configured
  }

  return (
    <div className="space-y-2">
      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300"></div>
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="px-2 bg-white text-gray-500">Ou continuer avec</span>
        </div>
      </div>

      {/* OAuth Buttons */}
      <div className="grid grid-cols-1 gap-2">
        {enabledProviders.map((provider) => (
          <button
            key={provider.name}
            onClick={() => handleOAuthLogin(provider.name)}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition ${provider.color} ${provider.hoverColor}`}
          >
            {provider.icon}
            <span>Continuer avec {provider.displayName}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default OAuthButtons;
