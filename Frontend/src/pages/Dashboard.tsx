import { useState, useRef } from 'react';
import { Header } from '../components/layout/Header';
import { LeftSidebar } from '../components/layout/LeftSidebar';
import { RightSidebar } from '../components/layout/RightSidebar';
import { AnimatePresence } from 'framer-motion';
import { UploadModal } from '../components/dashboard/UploadModal';
import { CleaningModal } from '../components/dashboard/CleaningModal';
import { AnalysisCard } from '../components/dashboard/AnalysisCard';
import { ProfileModal } from '../components/dashboard/ProfileModal'; // Import ProfileModal
import { useAuth } from '../hooks/useAuth';
import apiClient from '../api/apiClient';
import { type CleaningOptions } from '../types';

type ModalState = 'closed' | 'upload_prompt' | 'cleaning_options';

interface SummaryResponse {
  ai_insights: string;
}

interface FileUploadResponse {
  message: string;
}

interface AnalysisResult {
  id: number;
  title: string;
  content: string | React.ReactNode;
}

export interface ChatSession {
  id: string;
  title: string;
}

// --- NEW, ROBUST PARSER ---
const parseKeyStatistics = (rawText: string): string[] => {
  try {
    // Regex to capture content between "## Key Statistics" and "## Data Quality Assessment"
    // 's' flag makes '.' match newlines, 'i' flag makes it case-insensitive
    const match = rawText.match(/## Key Statistics\n*(.*?)\n*## Data Quality Assessment/is);

    if (!match || !match[1]) {
      // If the specific section isn't found, try to find any list-like items
      const fallbackMatch = rawText.match(/[-•].*?(?=\n\n|\n(##|$))/gs);
      if (fallbackMatch) {
         return fallbackMatch
           .map(line => line.replace(/[-•]\s*/, '').trim())
           .filter(line => line.length > 0);
      }
      return ["Could not parse key statistics from AI response."];
    }
    
    let insights = match[1];

    // Clean the extracted text: remove sub-headings, bold, standardize bullets, remove extra lines
    const cleanInsights = insights
      .replace(/### \w+ Insights:/g, "") // Remove sub-headings like '### Numerical Insights:'
      .replace(/\*\*/g, "")              // Remove all bold markers
      .replace(/^- /gm, "• ")             // Change markdown dashes to bullets
      .replace(/\n\s*\n/g, "\n")        // Replace multiple newlines with single
      .trim()
      .split('\n'); // Split into an array by line
      
    // Filter out any empty lines that might result from cleaning
    return cleanInsights.filter(line => line.trim() !== ""); 
  } catch (e) {
    console.error("Error parsing insights:", e);
    return ["Error: Could not process AI insights."];
  }
}
// --- END NEW PARSER ---


export const Dashboard = () => {
  const [modalStep, setModalStep] = useState<ModalState>('closed');
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([
    { id: Date.now(), title: 'Welcome!', content: 'Upload a file to get started.' },
  ]);
  
  const [automatedInsights, setAutomatedInsights] = useState<string[] | null>(null);
  
  // Initialize chatHistory as truly empty
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  
  // State to control the ProfileModal visibility
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  const { user, isAuthenticated } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchSummary = async (userId: string, tempId: number) => {
    try {
      const { data }: { data: SummaryResponse } = await apiClient.get(`/data/summarize/${userId}`);
      
      const keyStats = parseKeyStatistics(data.ai_insights);
      setAutomatedInsights(keyStats);
      
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId 
          ? { 
              id: r.id, 
              title: "Analysis Complete", 
              content: "Key statistics are in the 'Automated Insights' panel. Chat with the AI assistant for more details." 
            } 
          : r
        )
      );
    } catch (err: any) {
      let errorMsg = err.response?.data?.detail || "Failed to fetch summary.";
      if (errorMsg.includes("LM Studio")) {
        errorMsg = "AI server is not running. Please start LM Studio.";
      }
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId ? { ...r, title: "Summary Failed", content: errorMsg } : r)
      );
      setAutomatedInsights(["Failed to load insights. " + errorMsg]);
    }
  };

  const uploadFile = async (applyCleaning: boolean, options?: CleaningOptions) => {
    if (!isAuthenticated || !user) {
      setUploadError("Please log in to upload files.");
      return;
    }
    if (!selectedFile) {
      setUploadError("No file selected.");
      return;
    }
    setModalStep('closed');
    setIsUploading(true);
    setUploadError(null);
    setAutomatedInsights(null); // Clear previous insights
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('user_id', user.user_id);
    formData.append('apply_cleaning', String(applyCleaning));
    if (applyCleaning && options) {
      Object.entries(options).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }
    const tempId = Date.now();
    setAnalysisResults(prev => [
      { id: tempId, title: `Uploading "${selectedFile.name}"...`, content: "Processing file and generating AI summary..." },
      ...prev.filter(r => r.title !== 'Welcome!')
    ]);
    try {
      const { data }: { data: FileUploadResponse } = await apiClient.post('/data/upload-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId ? { ...r, content: data.message } : r)
      );
      await fetchSummary(user.user_id, tempId);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "File upload failed.";
      setUploadError(errorMsg);
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId ? { ...r, title: "Upload Failed", content: errorMsg } : r)
      );
      setAutomatedInsights(["Failed to load insights. " + errorMsg]);
    } finally {
      setIsUploading(false);
      setSelectedFile(null);
      if(fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleUploadClick = () => {
    if (!isAuthenticated) {
      setUploadError("Please log in or register to upload files.");
      return;
    }
    setUploadError(null);
    fileInputRef.current?.click();
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setModalStep('upload_prompt');
    }
  };
  const handleUploadConfirm = () => setModalStep('cleaning_options');
  const handleUploadCancel = () => uploadFile(false);
  const handleCleaningConfirm = (options: CleaningOptions) => uploadFile(true, options);
  const handleCleaningCancel = () => setModalStep('closed');
  
  return (
    <>
      <div className="fixed top-0 left-0 w-full h-screen -z-10 bg-light-bg" />
      
      <div className="flex h-screen w-full p-4 gap-4">
        <LeftSidebar insights={automatedInsights} chatHistory={chatHistory} />

        <div className="flex-1 flex flex-col h-full gap-4">
          <Header />
          <main className="flex-1 overflow-y-auto p-6 pr-2">
            
            <h2 className="text-xl font-semibold mb-4 text-text-dark">Quick Analysis</h2>
            <div className="flex gap-2 mb-8">
              <button className="text-sm bg-white border border-border-light rounded-full px-4 py-2 text-text-light hover:bg-gray-100 hover:text-text-dark transition-colors shadow-sm">
                Summarize Data
              </button>
              <button className="text-sm bg-white border border-border-light rounded-full px-4 py-2 text-text-light hover:bg-gray-100 hover:text-text-dark transition-colors shadow-sm">
                Find Correlations
              </button>
            </div>
            
            <h2 className="text-xl font-semibold mb-4 text-text-dark">Upload Your Data</h2>
            
            <input 
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept=".csv, .xlsx, .xls"
            />
            
            <div 
              className="flex items-center justify-center h-48 rounded-lg border-2 border-dashed border-gray-300 transition-colors hover:border-primary hover:bg-white/50 cursor-pointer"
              onClick={handleUploadClick}
            >
              <button
                className="rounded-lg bg-primary px-5 py-2.5 font-medium text-white shadow-sm hover:bg-primary/80 pointer-events-none"
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Upload .CSV, .XLSX, .JSON'}
              </button>
            </div>
            {uploadError && <p className="mt-2 text-center text-red-500">{uploadError}</p>}

            <div className="mt-8 space-y-4">
              <AnimatePresence>
                {analysisResults.map(result => (
                  <AnalysisCard key={result.id} title={result.title}>
                    {typeof result.content === 'string' ? <p>{result.content}</p> : result.content}
                  </AnalysisCard>
                ))}
              </AnimatePresence>
            </div>
          </main>
        </div>

        {/* Pass the setChatHistory and the profile click handler */}
        <RightSidebar 
          setChatHistory={setChatHistory} 
          onProfileClick={() => setIsProfileModalOpen(true)} 
        />
      </div>

      <AnimatePresence>
        {modalStep === 'upload_prompt' && (
          <UploadModal 
            onConfirm={handleUploadConfirm}
            onCancel={handleUploadCancel}
          />
        )}
        {modalStep === 'cleaning_options' && (
          <CleaningModal 
            onConfirm={handleCleaningConfirm}
            onCancel={handleCleaningCancel}
          />
        )}
        {/* Render ProfileModal if isProfileModalOpen is true */}
        {isProfileModalOpen && (
          <ProfileModal onClose={() => setIsProfileModalOpen(false)} />
        )}
      </AnimatePresence>
    </>
  );
};
