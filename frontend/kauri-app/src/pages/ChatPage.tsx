import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Menu, X } from 'lucide-react';
import { chatbotService } from '../services/chatbotService';
import { conversationService } from '../services/conversationService';
import { useAuth } from '../contexts/AuthContext';
import ConversationSidebar from '../components/chat/ConversationSidebar';
import { MessageFeedback } from '../components/chat/MessageFeedback';
import { ContextWarningBanner } from '../components/chat/ContextWarningBanner';
import type { ChatMessage, Conversation, ConversationContextInfo } from '../types';

const ChatPage: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [contextInfo, setContextInfo] = useState<ConversationContextInfo | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await conversationService.listConversations(false, 50, 0);
      setConversations(response.conversations);
    } catch (error) {
      console.error('Erreur lors du chargement des conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  const fetchContextInfo = async (convId: string) => {
    try {
      const info = await conversationService.getContextInfo(convId);
      setContextInfo(info);
    } catch (error) {
      console.error('Erreur lors de la récupération des infos de contexte:', error);
    }
  };

  const loadConversationMessages = async (convId: string) => {
    try {
      const conversation = await conversationService.getConversation(convId);
      if (conversation.messages) {
        // Convert API messages to ChatMessage format
        const chatMessages: ChatMessage[] = conversation.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.created_at || new Date()),
        }));
        setMessages(chatMessages);
      }
      setConversationId(convId);
    } catch (error) {
      console.error('Erreur lors du chargement des messages:', error);
    }
  };

  const handleNewConversation = () => {
    setConversationId(undefined);
    setMessages([]);
  };

  const handleSelectConversation = (convId: string) => {
    loadConversationMessages(convId);
    setIsSidebarOpen(false); // Close sidebar on mobile after selecting
  };

  const handleDeleteConversation = async (convId: string) => {
    try {
      await conversationService.deleteConversation(convId);
      // Reload conversations list
      await loadConversations();
      // If deleted conversation was active, clear it
      if (conversationId === convId) {
        handleNewConversation();
      }
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
    }
  };

  const handleArchiveConversation = async (convId: string) => {
    try {
      await conversationService.updateConversation(convId, { is_archived: true });
      // Reload conversations list
      await loadConversations();
      // If archived conversation was active, clear it
      if (conversationId === convId) {
        handleNewConversation();
      }
    } catch (error) {
      console.error('Erreur lors de l\'archivage:', error);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    // Check if context is over limit
    if (contextInfo?.is_over_limit) {
      alert('La limite de contexte est atteinte. Veuillez créer une nouvelle conversation.');
      return;
    }

    const query = inputValue;
    const userMessage: ChatMessage = {
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Create placeholder for assistant message
    const assistantMessageIndex = messages.length + 1;
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Use fetch with streaming instead of EventSource for POST support
      const token = localStorage.getItem('access_token');
      const CHATBOT_SERVICE_URL = import.meta.env.VITE_CHATBOT_SERVICE_URL || 'http://localhost:3202';

      const response = await fetch(`${CHATBOT_SERVICE_URL}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: query,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let buffer = '';
      let tempSources: any[] = []; // Store sources temporarily

      if (!reader) {
        throw new Error('No reader available');
      }

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          setIsLoading(false);
          break;
        }

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Split by double newlines (SSE format)
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));

              if (data.type === 'conversation_id') {
                if (!conversationId) {
                  setConversationId(data.conversation_id);
                  loadConversations();
                }
              } else if (data.type === 'sources') {
                // Store sources temporarily, don't display yet
                tempSources = data.sources;
              } else if (data.type === 'token') {
                fullResponse += data.content;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantMessageIndex] = {
                    ...newMessages[assistantMessageIndex],
                    content: fullResponse,
                  };
                  return newMessages;
                });
              } else if (data.type === 'done') {
                // Now add sources and metadata when response is complete
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantMessageIndex] = {
                    ...newMessages[assistantMessageIndex],
                    sources: tempSources.length > 0 ? tempSources : undefined,
                    metadata: data.metadata,
                  };
                  return newMessages;
                });

                // Update conversation ID from metadata
                if (data.metadata && data.metadata.conversation_id && !conversationId) {
                  setConversationId(data.metadata.conversation_id);
                  loadConversations();
                }
                setIsLoading(false);
              } else if (data.type === 'message_id') {
                // Update message with message_id for feedback
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantMessageIndex] = {
                    ...newMessages[assistantMessageIndex],
                    id: data.message_id,
                  };
                  return newMessages;
                });

                // Fetch context info after message is saved
                const currentConvId = conversationId || (data.metadata && data.metadata.conversation_id);
                if (currentConvId) {
                  fetchContextInfo(currentConvId).catch(err => {
                    console.error('Error fetching context info:', err);
                  });
                }
              } else if (data.type === 'error') {
                console.error('Streaming error:', data.content);
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantMessageIndex] = {
                    ...newMessages[assistantMessageIndex],
                    content: 'Désolé, une erreur est survenue. Veuillez réessayer.',
                  };
                  return newMessages;
                });
                setIsLoading(false);
                break;
              }
            } catch (error) {
              console.error('Error parsing SSE data:', error);
            }
          }
        }
      }

    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[assistantMessageIndex] = {
          ...newMessages[assistantMessageIndex],
          content: 'Désolé, une erreur est survenue. Veuillez réessayer.',
        };
        return newMessages;
      });
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
    <div className="h-screen flex bg-gray-50 relative">
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-lg hover:bg-gray-50 transition"
        aria-label="Toggle menu"
      >
        {isSidebarOpen ? <X size={24} className="text-gray-700" /> : <Menu size={24} className="text-gray-700" />}
      </button>

      {/* Backdrop for mobile */}
      {isSidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Conversation Sidebar */}
      <div className={`
        fixed md:relative inset-y-0 left-0 z-40
        transform transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <ConversationSidebar
          conversations={conversations}
          currentConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          onArchiveConversation={handleArchiveConversation}
          loading={loadingConversations}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col w-full md:w-auto">
        {/* Context Warning Banner */}
        {contextInfo && (contextInfo.is_near_limit || contextInfo.is_over_limit) && (
          <ContextWarningBanner contextInfo={contextInfo} />
        )}

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto px-2 md:px-4 pt-16 md:pt-8 pb-4 max-w-4xl mx-auto w-full flex flex-col scrollbar-hide">
        {messages.length === 0 && (
          <>
            <div className="text-center mb-6 mt-12 md:mt-0">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2 px-2">
                Bonjour {user?.first_name || 'Utilisateur'} !
              </h1>
              <p className="text-gray-600 text-sm md:text-base px-2">Comment puis-je vous aider aujourd'hui ?</p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-6 md:mt-8 max-w-3xl mx-auto px-2">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(suggestion)}
                    className="p-3 md:p-4 text-left border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition"
                  >
                    <p className="text-xs md:text-sm text-gray-700">{suggestion}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Input Container - Only shown when no messages */}
            <div className="mt-6 max-w-4xl mx-auto w-full px-2">
              <div className="relative rounded-xl transition-all" style={{ boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)' }}>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    contextInfo?.is_over_limit
                      ? "Limite de contexte atteinte"
                      : "Posez votre question..."
                  }
                  className="w-full pl-3 md:pl-4 pr-12 py-3 bg-white border-0 rounded-xl focus:outline-none resize-none transition-all text-sm md:text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                  rows={1}
                  disabled={isLoading || contextInfo?.is_over_limit}
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                  onFocus={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 0 0 2px #22c55e'}
                  onBlur={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 2px 12px rgba(0, 0, 0, 0.08)'}
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !inputValue.trim() || contextInfo?.is_over_limit}
                  className="absolute right-2 bottom-2 bg-gray-200 hover:bg-green-600 text-gray-600 hover:text-white p-2 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  title={contextInfo?.is_over_limit ? "Limite de contexte atteinte" : "Envoyer"}
                >
                  <Send size={18} className="md:hidden" />
                  <Send size={20} className="hidden md:block" />
                </button>
              </div>
            </div>
          </>
        )}

        {messages.map((message, index) => (
          <div
            key={message.id || `${message.role}-${index}-${message.timestamp.getTime()}`}
            className={`flex gap-2 md:gap-3 mb-4 md:mb-6 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="w-7 h-7 md:w-8 md:h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="md:w-[18px] md:h-[18px] text-green-600" />
              </div>
            )}
            <div className={`max-w-[85%] md:max-w-[70%]`}>
              <div
                className={`rounded-2xl px-3 md:px-4 py-2 md:py-3 ${
                  message.role === 'user'
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="text-xs md:text-sm whitespace-pre-wrap">{message.content}</p>

                {/* Sources - Only for assistant messages */}
                {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                  <div className="mt-3 md:mt-4 pt-2 md:pt-3 border-t border-gray-300">
                    <div className="mb-1.5 md:mb-2">
                      <span className="text-[10px] md:text-xs font-semibold text-gray-700">Sources ({message.sources.length})</span>
                    </div>
                    <div className="space-y-1 md:space-y-1.5">
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="flex items-center gap-1.5 md:gap-2 text-[10px] md:text-xs">
                          <span className="font-bold text-gray-400 min-w-[14px] md:min-w-[16px]">{idx + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <span className="font-medium text-gray-800 truncate block">{source.title}</span>
                          </div>
                          <span className="inline-flex items-center px-1 md:px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-semibold flex-shrink-0 text-[9px] md:text-xs">
                            {source.score.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <p className={`text-[10px] md:text-xs mt-1.5 md:mt-2 ${
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
          <div className="flex gap-2 md:gap-3 mb-4 md:mb-6">
            <div className="w-7 h-7 md:w-8 md:h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="md:w-[18px] md:h-[18px] text-green-600" />
            </div>
            <div className="bg-gray-100 rounded-2xl px-3 md:px-4 py-2 md:py-3">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
        </div>

        {/* Input Container - Only shown when there are messages */}
        {messages.length > 0 && (
          <div className="px-2 md:px-4 py-3 md:py-4">
            <div className="max-w-4xl mx-auto w-full">
              <div className="relative rounded-xl transition-all" style={{ boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)' }}>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    contextInfo?.is_over_limit
                      ? "Limite de contexte atteinte"
                      : "Posez votre question..."
                  }
                  className="w-full pl-3 md:pl-4 pr-12 py-2.5 md:py-3 bg-white border-0 rounded-xl focus:outline-none resize-none transition-all text-sm md:text-base disabled:bg-gray-100 disabled:cursor-not-allowed"
                  rows={1}
                  disabled={isLoading || contextInfo?.is_over_limit}
                  style={{ minHeight: '44px', maxHeight: '120px' }}
                  onFocus={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 0 0 2px #22c55e'}
                  onBlur={(e) => e.currentTarget.parentElement!.style.boxShadow = '0 2px 12px rgba(0, 0, 0, 0.08)'}
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !inputValue.trim() || contextInfo?.is_over_limit}
                  className="absolute right-2 bottom-2 bg-gray-200 hover:bg-green-600 text-gray-600 hover:text-white p-2 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  title={contextInfo?.is_over_limit ? "Limite de contexte atteinte" : "Envoyer"}
                >
                  <Send size={18} className="md:hidden" />
                  <Send size={20} className="hidden md:block" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
