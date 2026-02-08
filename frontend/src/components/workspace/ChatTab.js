import React from 'react';
import ChatPanel from '@/components/ChatPanel';

export const ChatTab = () => {
  return (
    <div className="h-full" data-testid="chat-tab">
      <ChatPanel />
    </div>
  );
};

export default ChatTab;