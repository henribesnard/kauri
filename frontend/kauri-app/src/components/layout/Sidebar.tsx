import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ShoppingCart,
  TrendingUp,
  Building2,
  Package,
  BarChart3,
  Plus,
  MessageSquare,
  Clock,
  ChevronDown,
  Settings,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: number;
}

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Extract initials from first and last name
  const getInitials = () => {
    const firstName = user?.first_name || '';
    const lastName = user?.last_name || '';
    if (!firstName && !lastName) return 'U';
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
  };

  const navItems: NavItem[] = [
    { name: 'Achats', path: '/achats', icon: <ShoppingCart size={20} />, badge: 3 },
    { name: 'Ventes', path: '/ventes', icon: <TrendingUp size={20} />, badge: 5 },
    { name: 'Banque', path: '/banque', icon: <Building2 size={20} />, badge: 12 },
    { name: 'Immobilisations', path: '/immobilisations', icon: <Package size={20} /> },
    { name: 'Rapports', path: '/rapports', icon: <BarChart3 size={20} /> },
  ];

  const mockConversations = [
    { id: '1', title: 'Conversation du 03/11/2...', date: 'il y a 2 jours', messages: 1 },
    { id: '2', title: 'Conversation du 03/11/2...', date: 'il y a 2 jours', messages: 2 },
    { id: '3', title: 'Conversation du 01/11/2...', date: 'il y a 4 jours', messages: 1 },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="w-64 bg-white h-screen border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-6">
        <h1 className="text-3xl font-bold text-green-600" style={{ fontFamily: "'Playfair Display', serif" }}>Kauri</h1>
      </div>

      {/* Bouton Nouvelle conversation (visible seulement sur /chat) */}
      {location.pathname === '/chat' && (
        <div className="px-4 pb-4">
          <button
            onClick={() => window.location.reload()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <Plus size={18} />
            <span className="text-sm font-medium">Nouvelle conversation</span>
          </button>
        </div>
      )}

      {/* Navigation ou Conversations */}
      {location.pathname === '/chat' ? (
        <nav className="flex-1 p-4 overflow-y-auto">
          <div className="space-y-1">
            {mockConversations.map((conv) => (
              <button
                key={conv.id}
                className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 transition"
              >
                <div className="flex items-start gap-2">
                  <MessageSquare size={16} className="text-gray-400 mt-1 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{conv.title}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                      <Clock size={12} />
                      <span>{conv.date}</span>
                      <span>•</span>
                      <span>{conv.messages} message{conv.messages > 1 ? 's' : ''}</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </nav>
      ) : (
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center justify-between px-4 py-3 rounded-lg transition-colors
                ${isActive(item.path)
                  ? 'bg-green-50 text-green-700'
                  : 'text-gray-700 hover:bg-gray-50'
                }
              `}
            >
              <div className="flex items-center gap-3">
                {item.icon}
                <span className="font-medium">{item.name}</span>
              </div>
              {item.badge && (
                <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-1 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>
      )}

      {/* Menu utilisateur */}
      <div className="p-4">
        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
              {getInitials()}
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-gray-900">
                {user?.first_name || ''} {user?.last_name || ''}
              </p>
              <p className="text-xs text-gray-500">{user?.email}</p>
            </div>
          </div>
          <ChevronDown size={16} className={`text-gray-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown menu */}
        {showUserMenu && (
          <div className="mt-2 border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => {
                navigate('/settings');
                setShowUserMenu(false);
              }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <Settings size={16} />
              Paramètres
            </button>
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
            >
              <LogOut size={16} />
              Se déconnecter
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
