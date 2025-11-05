import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { Transaction } from '../../types';

interface TransactionListProps {
  transactions: Transaction[];
}

const TransactionList: React.FC<TransactionListProps> = ({ transactions }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Transactions récentes</h2>
      </div>
      <div className="divide-y divide-gray-100">
        {transactions.map((transaction) => (
          <div key={transaction.id} className="p-6 hover:bg-gray-50 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${
                  transaction.type === 'vente' ? 'bg-green-50' : 'bg-orange-50'
                }`}>
                  {transaction.type === 'vente' ? (
                    <TrendingUp size={20} className="text-green-600" />
                  ) : (
                    <TrendingDown size={20} className="text-orange-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{transaction.client}</p>
                  <p className="text-sm text-gray-500">
                    {transaction.date} • {transaction.type === 'vente' ? 'Vente' : 'Achat'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className={`text-lg font-semibold ${
                  transaction.type === 'vente' ? 'text-green-600' : 'text-orange-600'
                }`}>
                  {transaction.type === 'vente' ? '+' : '-'} {transaction.amount.toLocaleString()} FCFA
                </p>
                <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                  transaction.status === 'validé'
                    ? 'bg-green-50 text-green-700'
                    : 'bg-yellow-50 text-yellow-700'
                }`}>
                  {transaction.status}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TransactionList;
