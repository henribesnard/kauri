import React from 'react';
import { AlertTriangle, AlertCircle } from 'lucide-react';
import type { ConversationContextInfo } from '../../types';

interface ContextWarningBannerProps {
  contextInfo: ConversationContextInfo;
}

export const ContextWarningBanner: React.FC<ContextWarningBannerProps> = ({ contextInfo }) => {
  if (!contextInfo.is_near_limit && !contextInfo.is_over_limit) {
    return null;
  }

  const isOverLimit = contextInfo.is_over_limit;
  const usagePercentage = Math.round(contextInfo.usage_percentage);

  return (
    <div
      className={`mx-4 my-2 p-3 rounded-lg border ${
        isOverLimit
          ? 'bg-red-50 border-red-200'
          : 'bg-orange-50 border-orange-200'
      }`}
    >
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0 mt-0.5">
          {isOverLimit ? (
            <AlertCircle className="text-red-600" size={20} />
          ) : (
            <AlertTriangle className="text-orange-600" size={20} />
          )}
        </div>
        <div className="flex-1">
          <p
            className={`text-sm font-medium ${
              isOverLimit ? 'text-red-900' : 'text-orange-900'
            }`}
          >
            {isOverLimit
              ? 'Limite de contexte atteinte'
              : 'Limite de contexte proche'}
          </p>
          <p
            className={`text-xs mt-1 ${
              isOverLimit ? 'text-red-700' : 'text-orange-700'
            }`}
          >
            {isOverLimit
              ? 'Vous ne pouvez plus poser de questions dans cette conversation. Veuillez créer une nouvelle conversation pour continuer.'
              : `La conversation utilise ${usagePercentage}% de la limite de contexte (${contextInfo.total_tokens}/${contextInfo.max_tokens} tokens). Considérez créer une nouvelle conversation bientôt.`}
          </p>
          <div className="mt-2 bg-white rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all ${
                isOverLimit ? 'bg-red-600' : 'bg-orange-500'
              }`}
              style={{ width: `${Math.min(usagePercentage, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
