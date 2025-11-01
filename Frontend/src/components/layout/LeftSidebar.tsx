import { FaLightbulb, FaDatabase } from 'react-icons/fa';

const HistoryItem = ({ title }: { title: string }) => (
  <div className="mb-2 rounded-lg border border-border-light bg-white/50 p-3 text-sm text-text-light hover:bg-white/80 cursor-pointer">
    {title}
  </div>
);

export const LeftSidebar = () => {
  return (
    <nav className="flex h-full flex-col frosted-glass rounded-r-xl p-4">
      <div className="mb-6 flex h-16 items-center px-2">
        <FaDatabase className="mr-2 h-6 w-6 text-primary" />
        <span className="text-xl font-bold text-text-dark">QuantumDash</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <h2 className="mb-3 px-2 text-xs font-semibold uppercase text-text-light">
          Chat History
        </h2>
        <div className="flex flex-col">
          <HistoryItem title="Sales Forecast Q4..." />
          <HistoryItem title="User Churn Analysis..." />
          <HistoryItem title="Marketing Spend ROI" />
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-border-light bg-white/50 p-4">
        <div className="mb-2 flex items-center">
          <FaLightbulb className="mr-2 h-4 w-4 text-primary" />
          <h3 className="font-semibold text-text-dark">Automated Insights</h3>
        </div>
        <p className="text-sm text-text-light">
          New insights will appear here.
        </p>
      </div>
    </nav>
  );
};