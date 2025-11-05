import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';
import { chatbotService } from '../services/chatbotService';
import { useAuth } from '../contexts/AuthContext';
import type { ChatMessage } from '../types';

const ChatPage: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await chatbotService.sendQuery(inputValue, sessionId);

      if (!sessionId) {
        setSessionId(response.session_id);
      }

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Désolé, une erreur est survenue. Veuillez réessayer.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    "Explique-moi le plan comptable OHADA",
    "Comment enregistrer une facture d'achat ?",
    "Quels sont les comptes de classe 6 ?",
    "Comment faire un rapprochement bancaire ?",
    "Qu'est-ce qu'un acte uniforme OHADA ?",
    "Comment comptabiliser un amortissement ?"
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 pt-8 pb-4 max-w-4xl mx-auto w-full flex flex-col">
        {messages.length === 0 && (
          <>
            <div className="text-center mb-6">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Bonjour {user?.first_name || 'Utilisateur'} !
              </h1>
              <p className="text-gray-600">Comment puis-je vous aider aujourd'hui ?</p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-8 max-w-3xl mx-auto">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(suggestion)}
                    className="p-4 text-left border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition"
                  >
                    <p className="text-sm text-gray-700">{suggestion}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Input Container - Only shown when no messages */}
            <div className="mt-6 max-w-4xl mx-auto w-full">
              <div className="relative rounded-xl transition-all" style={{ boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)' }}>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Posez votre question..."
                  className="w-full pl-4 pr-12 py-3 bg-white border-0 rounded-xl focus:outline-none resize-none transition-all"
                  rows={1}
                  disabled={isLoading}
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                  onFocus={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 0 0 2px #22c55e'}
                  onBlur={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 2px 12px rgba(0, 0, 0, 0.08)'}
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !inputValue.trim()}
                  className="absolute right-2 bottom-2 bg-gray-200 hover:bg-green-600 text-gray-600 hover:text-white p-2 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
          </>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 mb-6 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                <Bot size={18} className="text-green-600" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-green-100' : 'text-gray-500'
              }`}>
                {message.timestamp.toLocaleTimeString('fr-FR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 mb-6">
            <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
              <Bot size={18} className="text-green-600" />
            </div>
            <div className="bg-gray-100 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Container - Only shown when there are messages */}
      {messages.length > 0 && (
        <div className="px-4 py-4">
          <div className="max-w-4xl mx-auto w-full">
            <div className="relative rounded-xl transition-all" style={{ boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)' }}>
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Posez votre question..."
                className="w-full pl-4 pr-12 py-3 bg-white border-0 rounded-xl focus:outline-none resize-none transition-all"
                rows={1}
                disabled={isLoading}
                style={{ minHeight: '48px', maxHeight: '120px' }}
                onFocus={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 0 0 2px #22c55e'}
                onBlur={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 2px 12px rgba(0, 0, 0, 0.08)'}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !inputValue.trim()}
                className="absolute right-2 bottom-2 bg-gray-200 hover:bg-green-600 text-gray-600 hover:text-white p-2 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <Send size={20} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage;
