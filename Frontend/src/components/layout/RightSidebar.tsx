import { useState } from 'react';
import { FaPaperPlane, FaUserCircle } from 'react-icons/fa';

export const RightSidebar = () => {
  const [message, setMessage] = useState('');
  const chatMessages = [
    { from: 'ai', text: 'Hello! Upload your data to get started.' },
  ];

  return (
    <div className="flex h-full flex-col frosted-glass rounded-l-xl p-4">
      
      <div className="flex h-16 items-center justify-between border-b border-border-light pb-4">
        <h2 className="text-lg font-semibold text-text-dark">AI Assistant</h2>
        <button>
          <FaUserCircle className="h-7 w-7 text-gray-300 hover:text-text-dark" />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {chatMessages.map((msg, index) => (
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

      <form className="mt-auto flex gap-2 pt-4">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 rounded-lg border border-border-light bg-white/50 p-2 text-sm text-text-dark"
        />
        <button
          type="submit"
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white hover:bg-primary/80"
        >
          <FaPaperPlane className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
};