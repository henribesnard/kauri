import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  ShoppingCart,
  TrendingUp,
  Building2,
  Package,
  BarChart3,
  CheckCircle2
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: number;
}

const Sidebar: React.FC = () => {
  const location = useLocation();

  const navItems: NavItem[] = [
    { name: 'Tableau de bord', path: '/dashboard', icon: <Home size={20} /> },
    { name: 'Achats', path: '/achats', icon: <ShoppingCart size={20} />, badge: 3 },
    { name: 'Ventes', path: '/ventes', icon: <TrendingUp size={20} />, badge: 5 },
    { name: 'Banque', path: '/banque', icon: <Building2 size={20} />, badge: 12 },
    { name: 'Immobilisations', path: '/immobilisations', icon: <Package size={20} /> },
    { name: 'Rapports', path: '/rapports', icon: <BarChart3 size={20} /> },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="w-64 bg-white h-screen border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-900">Kauri</h1>
        <p className="text-sm text-gray-600 mt-1">Expert Comptable OHADA</p>
      </div>

      {/* Navigation */}
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

      {/* OHADA Badge */}
      <div className="p-4 border-t border-gray-200">
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-green-600" />
            <div>
              <p className="text-sm font-semibold text-green-900">Conformité OHADA</p>
              <p className="text-xs text-green-700">Tous vos documents sont conformes aux normes SYSCOHADA</p>
            </div>
          </div>
          <button className="mt-2 text-xs text-green-700 hover:text-green-800 font-medium">
            Voir le détail →
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
