import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, Archive, Trash2, User, Settings, LogOut, ChevronUp, ChevronDown } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import type { Conversation } from '../../types';

interface ConversationSidebarProps {
  conversations: Conversation[];
  currentConversationId?: string;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onArchiveConversation: (conversationId: string) => void;
  loading?: boolean;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onArchiveConversation,
  loading = false,
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false);

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return "Aujourd'hui";
    } else if (diffDays === 1) {
      return 'Hier';
    } else if (diffDays < 7) {
      return `il y a ${diffDays} jours`;
    } else if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `il y a ${weeks} semaine${weeks > 1 ? 's' : ''}`;
    } else {
      return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    }
  };

  const formatConversationTitle = (conversation: Conversation): string => {
    if (conversation.title) {
      return conversation.title;
    }

    const date = new Date(conversation.created_at);
    return `Conversation du ${date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    })}`;
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Kauri</h2>
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition text-sm font-medium"
        >
          <Plus size={18} />
          Nouvelle conversation
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
            <p className="mt-2 text-sm">Chargement...</p>
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageSquare size={48} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucune conversation</p>
          </div>
        ) : (
          <div className="py-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`group relative px-4 py-3 cursor-pointer transition ${
                  currentConversationId === conversation.id
                    ? 'bg-green-50 border-l-4 border-green-600'
                    : 'hover:bg-gray-50 border-l-4 border-transparent'
                }`}
                onClick={() => onSelectConversation(conversation.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {formatConversationTitle(conversation)}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-xs text-gray-500">
                        {formatDate(conversation.updated_at)}
                      </p>
                      {conversation.message_count !== undefined && (
                        <>
                          <span className="text-xs text-gray-400">•</span>
                          <p className="text-xs text-gray-500">
                            {conversation.message_count} message{conversation.message_count > 1 ? 's' : ''}
                          </p>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Action buttons (shown on hover) */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onArchiveConversation(conversation.id);
                      }}
                      className="p-1 rounded hover:bg-gray-200 transition"
                      title="Archiver"
                    >
                      <Archive size={14} className="text-gray-600" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Êtes-vous sûr de vouloir supprimer cette conversation ?')) {
                          onDeleteConversation(conversation.id);
                        }
                      }}
                      className="p-1 rounded hover:bg-red-100 transition"
                      title="Supprimer"
                    >
                      <Trash2 size={14} className="text-red-600" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Menu */}
      <div className="p-4">
        <button
          onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          className="w-full flex items-center gap-3 hover:bg-gray-50 rounded-lg p-2 transition"
        >
          <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
            {user?.first_name?.[0]?.toUpperCase() || 'U'}{user?.last_name?.[0]?.toUpperCase() || ''}
          </div>
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
          {isUserMenuOpen ? (
            <ChevronDown size={16} className="text-gray-400" />
          ) : (
            <ChevronUp size={16} className="text-gray-400" />
          )}
        </button>

        {isUserMenuOpen && (
          <div className="mt-2 space-y-1">
            <button
              onClick={() => {
                navigate('/dashboard');
                setIsUserMenuOpen(false);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition"
            >
              <User size={16} />
              Tableau de bord
            </button>
            <button
              onClick={logout}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition"
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

export default ConversationSidebar;
