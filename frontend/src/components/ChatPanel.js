import React, { useState, useEffect, useRef } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Loader2 } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';

export const ChatPanel = () => {
  const { selectedClient } = useClient();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (selectedClient) {
      loadChatHistory();
    }
  }, [selectedClient]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const loadChatHistory = async () => {
    try {
      const response = await api.chat.getHistory(selectedClient.id);
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load chat history');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedClient) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    try {
      const response = await api.chat.send({
        client_id: selectedClient.id,
        content: userMessage
      });

      setMessages([...messages, response.data.user_message, response.data.ai_message]);
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-card" data-testid="chat-panel">
      <div className="p-4 border-b border-border">
        <h2 className="font-semibold font-heading">AI Assistant</h2>
        <p className="text-xs text-muted-foreground">Chat with Easy X about {selectedClient?.name}</p>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground" data-testid="empty-chat-message">
              Start a conversation with Easy X
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                data-testid={`chat-message-${msg.role}`}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-foreground border border-border'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start" data-testid="loading-indicator">
              <div className="bg-muted border border-border rounded-lg px-3 py-2 text-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Thinking...
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Easy X anything..."
            data-testid="chat-input"
            className="min-h-[60px] resize-none"
            disabled={loading}
          />
          <Button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            size="icon"
            data-testid="send-chat-button"
            className="h-[60px] w-[60px]"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;