import { useState } from 'react';
import { FaPaperPlane, FaUserCircle } from 'react-icons/fa';
import { type ChatSession } from '../../pages/Dashboard';

// Ensure the prop interface is correct
interface RightSidebarProps {
  setChatHistory: React.Dispatch<React.SetStateAction<ChatSession[]>>;
  onProfileClick: () => void; // This will trigger the modal in Dashboard.tsx
}

interface Message {
  from: 'user' | 'ai';
  text: string;
}

export const RightSidebar = ({ setChatHistory, onProfileClick }: RightSidebarProps) => {
  const [message, setMessage] = useState('');
  const [messageHistory, setMessageHistory] = useState<Message[]>([
    { from: 'ai', text: 'Hello! Upload your data to get started.' },
  ]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage: Message = { from: 'user', text: message };
    setMessageHistory(prev => [...prev, userMessage]);

    // Check if this is the first user message (second message overall)
    // to add it to chat history in LeftSidebar
    if (messageHistory.length === 1) { // It contains only the initial AI greeting
      const newChatTitle = message.length > 20 ? message.substring(0, 20) + "..." : message;
      const newChat: ChatSession = {
        id: new Date().toISOString(), // Unique ID for the chat session
        title: newChatTitle,
      };
      // Pass the new chat session to the Dashboard to update LeftSidebar
      setChatHistory(prev => [newChat, ...prev]);
    }
    
    setMessage('');
    
    // Placeholder for AI response
    setTimeout(() => {
      const aiResponse: Message = { from: 'ai', text: 'Processing your request...' };
      setMessageHistory(prev => [...prev, aiResponse]);
    }, 1000);
  };

  return (
    <div className="flex h-full w-[300px] flex-col frosted-glass rounded-l-xl p-4">
      
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-border-light pb-4">
        <h2 className="text-lg font-semibold text-text-dark">AI Assistant</h2>
        {/* Profile icon now correctly triggers the onProfileClick prop */}
        <button onClick={onProfileClick} className="focus:outline-none">
          <FaUserCircle className="h-7 w-7 text-gray-300 hover:text-text-dark" />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messageHistory.map((msg, index) => (
          <div key={index} className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}>
            <p className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                msg.from === 'user' ? 'bg-primary text-white' : 'bg-white text-text-dark border border-border-light'
              }`}
            >
              {msg.text}
            </p>
          </div>
        ))}
      </div>

      <form onSubmit={handleSendMessage} className="mt-auto flex shrink-0 gap-2 pt-4">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 rounded-lg border border-border-light bg-white/50 p-2 text-sm text-text-dark focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white hover:bg-primary/80 focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <FaPaperPlane className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
};
