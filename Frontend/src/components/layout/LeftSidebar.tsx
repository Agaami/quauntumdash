import { FaLightbulb, FaDatabase } from 'react-icons/fa';
import { type ChatSession } from '../../pages/Dashboard';

interface LeftSidebarProps {
  insights: string[] | null;
  chatHistory: ChatSession[]; // This is now a dynamic array
}

const HistoryItem = ({ title }: { title: string }) => (
  <div className="mb-2 rounded-lg border border-border-light bg-light-bg p-3 text-sm text-text-light hover:bg-gray-100 cursor-pointer">
    <span className="truncate">{title}</span>
  </div>
);

export const LeftSidebar = ({ insights, chatHistory }: LeftSidebarProps) => {
  return (
    <nav className="flex h-full w-[260px] flex-col frosted-glass rounded-r-xl p-4">
      {/* Logo (shrink-0 prevents it from shrinking) */}
      <div className="mb-6 flex h-16 shrink-0 items-center px-2">
        <FaDatabase className="mr-2 h-6 w-6 text-primary" />
        <span className="text-xl font-bold text-text-dark">QuantumDash</span>
      </div>

      {/* Chat History (flex-1 makes it take available space and overflow) */}
      <div className="flex-1 overflow-y-auto">
        <h2 className="mb-3 px-2 text-xs font-semibold uppercase text-text-light">
          Chat History
        </h2>
        <div className="flex flex-col">
          {chatHistory.length > 0 ? (
            chatHistory.map(chat => (
              <HistoryItem key={chat.id} title={chat.title} />
            ))
          ) : (
            <p className="px-2 text-sm text-text-light">No history yet.</p>
          )}
        </div>
      </div>

      {/* Automated Insights (shrink-0 makes it take its natural height, no max-h) */}
      <div className="mt-4 shrink-0 rounded-lg border border-border-light bg-white/50 p-4">
        <div className="mb-2 flex items-center">
          <FaLightbulb className="mr-2 h-4 w-4 text-primary" />
          <h3 className="font-semibold text-text-dark">Automated Insights</h3>
        </div>
        
        <ul className="text-sm text-text-light list-disc list-inside space-y-1"> {/* Removed overflow-y-auto and max-h here */}
          {insights && insights.length > 0 ? (
            insights.map((insight, index) => (
              <li key={index}>{insight}</li>
            ))
          ) : (
            <li>Upload data to generate insights...</li>
          )}
        </ul>
      </div>
    </nav>
  );
};
