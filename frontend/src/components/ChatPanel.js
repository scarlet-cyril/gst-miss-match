import React, { useState, useEffect, useRef } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
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
      console.error('Failed to load chat history:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedClient) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    const tempUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      console.log('[Chat] Sending message:', { client_id: selectedClient.id, content: userMessage });
      
      const response = await api.chat.send({
        client_id: selectedClient.id,
        content: userMessage
      });

      console.log('[Chat] Response received:', response.data);

      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        response.data.user_message,
        response.data.ai_message
      ]);

      // Show toast for tool executions
      if (response.data.ai_message.tool_calls && response.data.ai_message.tool_calls.length > 0) {
        response.data.ai_message.tool_calls.forEach(toolCall => {
          if (toolCall.result?.success) {
            toast.success(toolCall.result.message || 'Action completed successfully');
          } else if (toolCall.result?.success === false) {
            toast.error(toolCall.result.error || 'Action failed');
          }
        });
      }
    } catch (error) {
      console.error('[Chat] Error:', error);
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      toast.error('Failed to send message: ' + (error.response?.data?.detail || error.message));
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

  const renderMessage = (msg) => {
    const isUser = msg.role === 'user';
    const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0;

    return (
      <div
        key={msg.id}
        data-testid={`chat-message-${msg.role}`}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        <div className="flex flex-col gap-2 max-w-[85%]">
          <div
            className={`rounded-lg px-3 py-2 text-sm ${
              isUser
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-foreground border border-border'
            }`}
          >
            {msg.content}
          </div>
          
          {hasToolCalls && (
            <div className="space-y-1">
              {msg.tool_calls.map((toolCall, idx) => (
                <div
                  key={idx}
                  className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${
                    toolCall.result?.success
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}
                >
                  {toolCall.result?.success ? (
                    <CheckCircle className="w-3 h-3" />
                  ) : (
                    <AlertCircle className="w-3 h-3" />
                  )}
                  <span className="font-medium">{toolCall.tool}:</span>
                  <span>{toolCall.result?.message || toolCall.result?.error}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
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
            messages.map(renderMessage)
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
            placeholder="Ask Easy X anything or say 'create ledger entry'..."
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