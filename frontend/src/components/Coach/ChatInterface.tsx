/**
 * AI Coach Chat Interface
 * Real-time chat with the AI mental health coach
 */
import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../../api/client';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  sentiment?: number;
}

interface ChatInterfaceProps {
  conversationId?: number;
  persona?: 'coach' | 'friend' | 'expert';
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  conversationId: initialConversationId,
  persona = 'coach',
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | undefined>(initialConversationId);
  const [crisisDetected, setCrisisDetected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversationId) {
      loadMessages();
    } else {
      // Show welcome message
      setMessages([
        {
          id: 0,
          role: 'assistant',
          content: getWelcomeMessage(persona),
          created_at: new Date().toISOString(),
        },
      ]);
    }
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadMessages = async () => {
    if (!conversationId) return;

    try {
      const data = await apiClient.getConversationMessages(conversationId);
      setMessages(data);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setLoading(true);

    // Add user message to UI immediately
    const tempUserMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await apiClient.sendMessage(userMessage, conversationId, persona);

      // Update conversation ID if new
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      // Check for crisis
      if (response.metadata?.crisis_level === 'critical' || response.metadata?.crisis_level === 'high') {
        setCrisisDetected(true);
      }

      // Add assistant response
      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: Message = {
        id: Date.now() + 1,
        role: 'system',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="bg-indigo-600 text-white p-4 rounded-t-lg">
        <h2 className="text-xl font-semibold">
          {persona === 'coach' && '🎯 Professional Coach'}
          {persona === 'friend' && '💙 Supportive Friend'}
          {persona === 'expert' && '🧠 Mental Health Expert'}
        </h2>
        <p className="text-sm opacity-90">24/7 Support • Confidential • HIPAA Compliant</p>
      </div>

      {/* Crisis Alert */}
      {crisisDetected && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 m-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Crisis Support Resources</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>
                  <strong>National Suicide & Crisis Lifeline:</strong> 988
                  <br />
                  <strong>Crisis Text Line:</strong> Text "HELLO" to 741741
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {loading && (
          <div className="flex items-start space-x-2">
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '0.2s' }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '0.4s' }}
                ></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !inputMessage.trim()}
            className="bg-indigo-600 text-white px-6 rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="bg-gray-100 text-gray-600 rounded-lg px-4 py-2 text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[70%] rounded-lg p-3 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <p
          className={`text-xs mt-1 ${
            isUser ? 'text-indigo-200' : 'text-gray-500'
          }`}
        >
          {new Date(message.created_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};

function getWelcomeMessage(persona: string): string {
  const messages = {
    coach: `Hi! I'm your professional mental health coach. I'm here to help you develop strategies for managing stress, improving your wellbeing, and achieving your mental health goals.

What would you like to work on today?`,

    friend: `Hey there! I'm here to listen and support you, just like a good friend would. Whether you need to vent, talk through something, or just want someone to understand what you're going through, I'm here.

How are you doing today?`,

    expert: `Hello! I'm your mental health expert, trained in evidence-based therapeutic techniques including CBT and DBT. I can help you understand the psychology behind your thoughts and emotions, and guide you through scientifically-validated interventions.

What would you like to explore or learn about today?`,
  };

  return messages[persona as keyof typeof messages] || messages.coach;
}

export default ChatInterface;
