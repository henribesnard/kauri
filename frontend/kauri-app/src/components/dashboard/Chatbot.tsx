import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot } from 'lucide-react';
import { chatbotService } from '../../services/chatbotService';
import { conversationService } from '../../services/conversationService';
import { MessageFeedback } from '../chat/MessageFeedback';
import { ContextWarningBanner } from '../chat/ContextWarningBanner';
import type { ChatMessage, ConversationContextInfo } from '../../types';

const Chatbot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Bonjour ! Je suis votre assistant comptable OHADA. Comment puis-je vous aider aujourd\'hui ?',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [contextInfo, setContextInfo] = useState<ConversationContextInfo | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchContextInfo = async (convId: string) => {
    try {
      const info = await conversationService.getContextInfo(convId);
      setContextInfo(info);
    } catch (error) {
      console.error('Erreur lors de la récupération des infos de contexte:', error);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    // Check if context is over limit
    if (contextInfo?.is_over_limit) {
      alert('La limite de contexte est atteinte. Veuillez créer une nouvelle conversation.');
      return;
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await chatbotService.sendQuery(inputValue, conversationId);

      let currentConvId = conversationId;
      if (!currentConvId && response.conversation_id) {
        currentConvId = response.conversation_id;
        setConversationId(currentConvId);
      }

      const assistantMessage: ChatMessage = {
        id: response.message_id || `msg-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        metadata: response.metadata,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Fetch context info after each message (non-blocking)
      if (currentConvId) {
        fetchContextInfo(currentConvId).catch(err => {
          console.error('Error fetching context info:', err);
        });
      }
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

  return (
    <>
      {/* Bouton flottant */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 bg-green-600 hover:bg-green-700 text-white rounded-full p-4 shadow-lg transition-all hover:scale-110 z-50"
        >
          <MessageCircle size={24} />
        </button>
      )}

      {/* Fenêtre du chatbot */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 border border-gray-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-green-600 to-green-700 text-white p-4 rounded-t-2xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
                <Bot size={20} className="text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold">Assistant OHADA</h3>
                <p className="text-xs text-green-100">En ligne</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="hover:bg-green-500 rounded-full p-1 transition"
            >
              <X size={20} />
            </button>
          </div>

          {/* Context Warning Banner */}
          {contextInfo && (contextInfo.is_near_limit || contextInfo.is_over_limit) && (
            <ContextWarningBanner contextInfo={contextInfo} />
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] ${
                    message.role === 'user'
                      ? ''
                      : 'w-full'
                  }`}
                >
                  <div
                    className={`rounded-2xl px-4 py-2 ${
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
                  {/* Add feedback for assistant messages */}
                  {message.role === 'assistant' && message.id && (
                    <MessageFeedback
                      messageId={message.id}
                      currentFeedback={message.user_feedback}
                      onFeedbackSubmitted={() => {
                        // Optionally refresh message to show updated feedback
                        console.log('Feedback submitted for message', message.id);
                      }}
                    />
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl px-4 py-2">
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

          {/* Input */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  contextInfo?.is_over_limit
                    ? "Limite de contexte atteinte"
                    : "Posez votre question..."
                }
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                disabled={isLoading || contextInfo?.is_over_limit}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !inputValue.trim() || contextInfo?.is_over_limit}
                className="bg-green-600 hover:bg-green-700 text-white p-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                title={contextInfo?.is_over_limit ? "Limite de contexte atteinte" : "Envoyer"}
              >
                <Send size={20} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Chatbot;
