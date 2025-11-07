import React, { useState, useEffect } from 'react';
import { User, CreditCard, Lock, Mail, Crown, TrendingUp, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import ConversationSidebar from '../components/chat/ConversationSidebar';
import { conversationService } from '../services/conversationService';
import type { Conversation } from '../types';

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3201';

console.log('[SettingsPage] USER_SERVICE_URL:', USER_SERVICE_URL);
console.log('[SettingsPage] VITE_USER_SERVICE_URL from env:', import.meta.env.VITE_USER_SERVICE_URL);

// Helper function for authenticated API calls
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('access_token');  // FIXED: was 'token', should be 'access_token'
  const url = `${USER_SERVICE_URL}${endpoint}`;

  console.log('[apiCall] Making request to:', url);
  console.log('[apiCall] Method:', options.method || 'GET');
  console.log('[apiCall] Has token:', !!token);

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  console.log('[apiCall] Response status:', response.status);

  if (response.status === 401) {
    console.log('[apiCall] 401 Unauthorized - Redirecting to login');
    localStorage.removeItem('access_token');  // FIXED: was 'token'
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    console.error('[apiCall] Error response:', error);
    throw new Error(error.detail || 'An error occurred');
  }

  return response.json();
};

type Tab = 'profile' | 'subscription';

interface QuotaInfo {
  user_id: string;
  subscription_tier: string;
  subscription_status: string;
  tier_name: string;
  tier_name_fr: string;
  messages_per_day_limit: number | null;
  messages_per_month_limit: number | null;
  messages_today: number;
  messages_this_month: number;
  messages_remaining_today: number | null;
  messages_remaining_month: number | null;
  can_send_message: boolean;
  is_quota_exceeded: boolean;
  needs_upgrade: boolean;
  warning_threshold_reached: boolean;
}

interface SubscriptionTier {
  tier_id: string;
  tier_name: string;
  tier_name_fr: string;
  tier_description: string;
  tier_description_fr: string;
  messages_per_day: number | null;
  messages_per_month: number | null;
  price_monthly: number;
  price_annual: number | null;
  has_document_sourcing: boolean;
  has_pdf_generation: boolean;
  has_priority_support: boolean;
}

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Conversations for sidebar
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
  });

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    console.log('[SettingsPage] Active tab changed to:', activeTab);
    if (activeTab === 'subscription') {
      console.log('[SettingsPage] Loading subscription tab...');
      fetchQuotaInfo();
      fetchTiers();
    }
  }, [activeTab]);

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await conversationService.listConversations(false, 50, 0);
      setConversations(response.conversations);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  const handleSelectConversation = (convId: string) => {
    navigate(`/chat?conversation=${convId}`);
  };

  const handleNewConversation = () => {
    navigate('/chat');
  };

  const handleDeleteConversation = async (convId: string) => {
    try {
      await conversationService.deleteConversation(convId);
      loadConversations();
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const handleArchiveConversation = async (convId: string) => {
    try {
      await conversationService.archiveConversation(convId);
      loadConversations();
    } catch (error) {
      console.error('Error archiving conversation:', error);
    }
  };

  const fetchQuotaInfo = async () => {
    console.log('[SettingsPage] Fetching quota info...');
    console.log('[SettingsPage] Token:', localStorage.getItem('access_token')?.substring(0, 20) + '...');
    console.log('[SettingsPage] URL:', `${USER_SERVICE_URL}/api/v1/subscription/quota`);
    try {
      const data = await apiCall('/api/v1/subscription/quota');
      console.log('[SettingsPage] Quota data received:', data);
      setQuotaInfo(data);
    } catch (err: any) {
      console.error('[SettingsPage] Error fetching quota:', err);
    }
  };

  const fetchTiers = async () => {
    console.log('[SettingsPage] Fetching tiers...');
    try {
      const data = await apiCall('/api/v1/subscription/tiers');
      console.log('[SettingsPage] Tiers data received:', data);
      setTiers(data);
    } catch (err: any) {
      console.error('[SettingsPage] Error fetching tiers:', err);
    }
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await apiCall('/api/v1/users/me', {
        method: 'PUT',
        body: JSON.stringify(profileForm),
      });
      setSuccess('Profil mis à jour avec succès !');
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la mise à jour du profil');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('Les mots de passe ne correspondent pas');
      setLoading(false);
      return;
    }

    try {
      await apiCall('/api/v1/users/me/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      });
      setSuccess('Mot de passe mis à jour avec succès !');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la mise à jour du mot de passe');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierId: string) => {
    // TODO: Implémenter le processus de paiement avec CinetPay
    // Pour l'instant, afficher un message d'information
    const tier = tiers.find(t => t.tier_id === tierId);
    const tierName = tier?.tier_name_fr || tierId;
    const price = tier?.price_monthly || 0;

    if (price === 0) {
      // Downgrade gratuit - pas besoin de paiement
      setError('');
      setSuccess('');
      setLoading(true);

      try {
        const data = await apiCall('/api/v1/subscription/upgrade', {
          method: 'POST',
          body: JSON.stringify({
            target_tier: tierId,
            payment_method: 'free',
            annual_billing: false,
          }),
        });
        setSuccess(`Abonnement mis à jour vers ${data.new_tier} !`);
        fetchQuotaInfo();
      } catch (err: any) {
        setError(err.message || 'Erreur lors de la mise à jour de l\'abonnement');
      } finally {
        setLoading(false);
      }
    } else {
      // Upgrade payant - afficher message temporaire
      setError('');
      setSuccess(`🚧 Fonctionnalité en cours de développement

Le paiement en ligne sera bientôt disponible via CinetPay.

Formule sélectionnée : ${tierName}
Prix : ${price.toLocaleString()} FCFA/mois

Pour activer cette formule dès maintenant, veuillez nous contacter à support@kauri.com`);
    }
  };

  const getProgressColor = (percentage: number) => {
    if (percentage >= 80) return 'bg-red-500';
    if (percentage >= 50) return 'bg-orange-500';
    return 'bg-green-500';
  };

  const calculatePercentage = (used: number, limit: number | null) => {
    if (limit === null) return 0;
    return Math.round((used / limit) * 100);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onArchiveConversation={handleArchiveConversation}
        loading={loadingConversations}
      />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto py-4 px-4">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
          <p className="text-sm text-gray-600 mt-1">Gérez votre profil et votre abonnement</p>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mb-4 bg-white p-1 rounded-lg shadow-sm">
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md font-medium transition ${
              activeTab === 'profile'
                ? 'bg-green-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <User size={18} />
            Profil
          </button>
          <button
            onClick={() => setActiveTab('subscription')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md font-medium transition ${
              activeTab === 'subscription'
                ? 'bg-green-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <CreditCard size={18} />
            Abonnement
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
            <p className="text-green-800">{success}</p>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="space-y-4">
            {/* Personal Information */}
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Informations personnelles</h2>
              <form onSubmit={handleProfileUpdate} className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Prénom
                    </label>
                    <input
                      type="text"
                      value={profileForm.first_name}
                      onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="Votre prénom"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nom
                    </label>
                    <input
                      type="text"
                      value={profileForm.last_name}
                      onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="Votre nom"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <Mail size={14} className="inline mr-1" />
                    Email
                  </label>
                  <input
                    type="email"
                    value={profileForm.email}
                    onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent bg-gray-50"
                    placeholder="votre@email.com"
                    disabled
                  />
                  <p className="text-xs text-gray-500 mt-1">L'email ne peut pas être modifié pour le moment</p>
                </div>
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Enregistrement...' : 'Enregistrer les modifications'}
                  </button>
                </div>
              </form>
            </div>

            {/* Change Password */}
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                <Lock size={16} className="inline mr-2" />
                Changer le mot de passe
              </h2>
              <form onSubmit={handlePasswordUpdate} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Mot de passe actuel
                  </label>
                  <input
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="••••••••"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nouveau mot de passe
                    </label>
                    <input
                      type="password"
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="••••••••"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Confirmer le mot de passe
                    </label>
                    <input
                      type="password"
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Mise à jour...' : 'Mettre à jour le mot de passe'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Subscription Tab */}
        {activeTab === 'subscription' && (
          <div className="space-y-4">
            {/* Current Plan */}
            {quotaInfo && (
              <div className="bg-white rounded-lg shadow-sm p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Formule actuelle</h2>
                    <p className="text-sm text-gray-600">Gérez votre abonnement et vos quotas</p>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                    <Crown size={14} />
                    <span className="font-medium">{quotaInfo.tier_name_fr}</span>
                  </div>
                </div>

                {/* Quota Progress - Only daily */}
                {quotaInfo.messages_per_day_limit !== null && (
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-700">Messages aujourd'hui</span>
                      <span className="font-medium text-gray-900">
                        {quotaInfo.messages_today} / {quotaInfo.messages_per_day_limit}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${getProgressColor(
                          calculatePercentage(quotaInfo.messages_today, quotaInfo.messages_per_day_limit)
                        )}`}
                        style={{
                          width: `${calculatePercentage(quotaInfo.messages_today, quotaInfo.messages_per_day_limit)}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                {quotaInfo.messages_per_day_limit === null && quotaInfo.messages_per_month_limit === null && (
                  <div className="text-center py-2">
                    <TrendingUp size={24} className="mx-auto text-green-600 mb-1" />
                    <p className="text-gray-700 font-medium text-sm">Messages illimités</p>
                  </div>
                )}
              </div>
            )}

            {/* Available Plans */}
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Formules disponibles</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {tiers.map((tier) => {
                  const isCurrentPlan = tier.tier_id === quotaInfo?.subscription_tier;
                  const isEnterprise = tier.tier_id === 'enterprise';
                  const isMax = tier.tier_id === 'max';

                  return (
                    <div
                      key={tier.tier_id}
                      className={`border-2 rounded-lg p-3 transition ${
                        isCurrentPlan
                          ? 'border-green-600 bg-green-50'
                          : 'border-gray-200 hover:border-green-300'
                      }`}
                    >
                      <div className="text-center mb-3">
                        <h3 className="text-base font-semibold text-gray-900">{tier.tier_name_fr}</h3>
                        <div className="mt-1">
                          {tier.price_monthly === 0 ? (
                            <p className="text-xl font-bold text-gray-900">Gratuit</p>
                          ) : (
                            <>
                              <p className="text-2xl font-bold text-gray-900">
                                {tier.price_monthly.toLocaleString()}
                                <span className="text-xs font-normal text-gray-600"> FCFA</span>
                              </p>
                              <p className="text-xs text-gray-500">par mois</p>
                            </>
                          )}
                        </div>
                      </div>

                      <ul className="space-y-1 mb-3 text-xs">
                        {tier.messages_per_day !== null ? (
                          <li className="text-gray-700">✓ {tier.messages_per_day} messages/jour</li>
                        ) : (
                          <li className="text-gray-700">✓ Messages illimités</li>
                        )}
                        {tier.has_document_sourcing && (
                          <li className="text-gray-700">✓ Sources documentaires</li>
                        )}
                        {tier.has_pdf_generation && (
                          <li className="text-gray-700">✓ Génération PDF</li>
                        )}
                        {tier.has_priority_support && (
                          <li className="text-gray-700">✓ Support prioritaire</li>
                        )}
                        {isEnterprise && (
                          <>
                            <li className="text-gray-700">✓ API dédiée</li>
                            <li className="text-gray-700">✓ Formation personnalisée</li>
                            <li className="text-gray-700">✓ SLA garanti</li>
                          </>
                        )}
                      </ul>

                      {isCurrentPlan ? (
                        <button
                          disabled
                          className="w-full px-3 py-1.5 text-sm bg-gray-300 text-gray-600 rounded-lg cursor-not-allowed"
                        >
                          Formule actuelle
                        </button>
                      ) : (
                        <button
                          onClick={() => handleUpgrade(tier.tier_id)}
                          disabled={loading}
                          className="w-full px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                        >
                          {tier.price_monthly === 0 ? 'Rétrograder' : 'Passer à cette formule'}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
