import React from 'react';
import { TrendingUp, DollarSign, Wallet, AlertTriangle } from 'lucide-react';
import KPICard from '../components/dashboard/KPICard';
import TransactionList from '../components/dashboard/TransactionList';
import TaskList from '../components/dashboard/TaskList';
import Chatbot from '../components/dashboard/Chatbot';
import { useAuth } from '../contexts/AuthContext';
import { Transaction, Task } from '../types';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  // Mock data (à remplacer par de vraies données API)
  const mockTransactions: Transaction[] = [
    {
      id: '1',
      type: 'vente',
      client: 'SARL DELTA',
      amount: 2450000,
      status: 'validé',
      date: '02 Nov',
    },
    {
      id: '2',
      type: 'achat',
      client: 'Fournisseur OMEGA',
      amount: 875000,
      status: 'validé',
      date: '02 Nov',
    },
    {
      id: '3',
      type: 'vente',
      client: 'Entreprise GAMMA',
      amount: 1200000,
      status: 'en attente',
      date: '01 Nov',
    },
  ];

  const mockTasks: Task[] = [
    {
      id: '1',
      title: "Valider 3 factures d'achat",
      priority: 'urgent',
      urgentCount: 2,
    },
    {
      id: '2',
      title: 'Rapprochement bancaire Octobre',
      priority: 'moyen',
    },
    {
      id: '3',
      title: 'Déclaration TVA - Échéance 15 Nov',
      priority: 'urgent',
    },
  ];

  return (
    <div className="space-y-6">
      {/* En-tête de bienvenue */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Bonjour {user?.full_name?.split(' ')[0] || 'Aïcha'} 👋
        </h1>
        <p className="text-gray-600 mt-1">Voici un aperçu de votre activité comptable</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Chiffre d'affaires"
          value="45 250 000 FCFA"
          change="+12.5%"
          trend="up"
          icon={<TrendingUp size={24} className="text-green-600" />}
        />
        <KPICard
          title="Dépenses du mois"
          value="18 430 000 FCFA"
          change="-3.2%"
          trend="down"
          icon={<DollarSign size={24} className="text-red-600" />}
        />
        <KPICard
          title="Trésorerie"
          value="62 820 000 FCFA"
          change="+8.7%"
          trend="up"
          icon={<Wallet size={24} className="text-green-600" />}
        />
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm text-gray-600 mb-1">Factures en attente</p>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">8</h3>
              <div className="flex items-center gap-1">
                <span className="text-sm font-medium text-yellow-600">2 urgentes</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-yellow-50">
              <AlertTriangle size={24} className="text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Transactions et Tâches */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TransactionList transactions={mockTransactions} />
        <TaskList tasks={mockTasks} />
      </div>

      {/* Chatbot */}
      <Chatbot />
    </div>
  );
};

export default DashboardPage;
