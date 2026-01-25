import React, { useState } from 'react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: number;
}

interface SearchResult {
  title: string;
  url: string;
  content: string;
}

export const WebChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hi! I can help you with vinyl record questions using web search. Ask me about prices, history, collecting tips, or any music-related topics!'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastSearchResults, setLastSearchResults] = useState<SearchResult[]>([]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add assistant response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        sources: data.sources_used || 0
      }]);
      
      // Update search results if available
      if (data.search_results) {
        setLastSearchResults(data.search_results.slice(0, 3));
      }

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error while searching for information. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-full bg-white">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-blue-600 text-white p-4 border-b">
          <h2 className="text-xl font-semibold">Web-Enhanced Vinyl Chat</h2>
          <p className="text-sm opacity-90">Ask questions about vinyl records, prices, history, and more!</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.sources && message.sources > 0 && (
                  <div className="text-xs mt-1 opacity-70">
                    📄 {message.sources} web sources used
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                  <span>Searching the web...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <div className="flex space-x-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about vinyl prices, artists, collecting tips..."
              className="flex-1 p-2 border rounded-lg resize-none"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Search Results Sidebar */}
      {lastSearchResults.length > 0 && (
        <div className="w-80 border-l bg-gray-50 p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Recent Search Sources</h3>
          <div className="space-y-3">
            {lastSearchResults.map((result, index) => (
              <div key={index} className="bg-white p-3 rounded-lg border text-sm">
                <div className="font-medium text-gray-800 truncate" title={result.title}>
                  {result.title}
                </div>
                <div className="text-gray-600 mt-1 text-xs truncate" title={result.url}>
                  {result.url}
                </div>
                <div className="text-gray-700 mt-2 text-xs leading-relaxed">
                  {result.content?.substring(0, 120)}...
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};