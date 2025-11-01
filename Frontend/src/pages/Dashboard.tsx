import { useState, useRef, Suspense } from 'react';
import { Header } from '../components/layout/Header';
import { LeftSidebar } from '../components/layout/LeftSidebar';
import { RightSidebar } from '../components/layout/RightSidebar';
import { AnimatePresence } from 'framer-motion';
import { UploadModal } from '../components/dashboard/UploadModal';
import { CleaningModal } from '../components/dashboard/CleaningModal';
import { AnalysisCard } from '../components/dashboard/AnalysisCard';
import { Canvas } from '@react-three/fiber';
import { InteractiveCameraRig } from '../components/layout/InteractiveCameraRig';
import { useAuth } from '../hooks/useAuth';
import apiClient from '../api/apiClient';
import { type CleaningOptions } from '../types';

type ModalState = 'closed' | 'upload_prompt' | 'cleaning_options';

// --- Simplified Analysis Result ---
interface AnalysisResult {
  id: number;
  title: string;
  content: string; // We'll just use simple text for now
}
// ---

export const Dashboard = () => {
  const [modalStep, setModalStep] = useState<ModalState>('closed');
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([
    { id: Date.now(), title: 'Welcome!', content: 'Upload a file to get started.' },
  ]);
  
  const { user } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- 1. REMOVED the 'fetchSummary' function ---

  // The main function to upload the file
  const uploadFile = async (applyCleaning: boolean, options?: CleaningOptions) => {
    if (!selectedFile || !user) {
      setUploadError("No file selected or user not found.");
      return;
    }

    setModalStep('closed');
    setIsUploading(true);
    setUploadError(null);

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
    // 2. Simplified the "Uploading" message
    setAnalysisResults(prev => [
      { id: tempId, title: `Uploading "${selectedFile.name}"...`, content: "Processing file..." },
      ...prev.filter(r => r.title !== 'Welcome!')
    ]);

    try {
      // Send to the backend
      const { data } = await apiClient.post('/data/upload-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // 3. Update the card with the simple success message
      // We no longer call fetchSummary
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId ? { ...r, title: "Upload Complete!", content: data.message } : r)
      );

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "File upload failed.";
      setUploadError(errorMsg);
      setAnalysisResults(prev => 
        prev.map(r => r.id === tempId ? { ...r, title: "Upload Failed", content: errorMsg } : r)
      );
    } finally {
      setIsUploading(false);
      setSelectedFile(null);
      if(fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // --- Modal logic functions (no change) ---
  const handleUploadClick = () => fileInputRef.current?.click();
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
      {/* 3D Background */}
      <div className="fixed top-0 left-0 w-full h-screen -z-10">
        <Canvas>
          <Suspense fallback={null}>
            <InteractiveCameraRig />
          </Suspense>
        </Canvas>
      </div>

      {/* Main Layout */}
      <div className="flex h-screen w-full p-4 gap-4">
        <LeftSidebar />

        <div className="flex-1 flex flex-col h-full gap-4">
          <Header />
          <main className="flex-1 overflow-y-auto p-6 pr-2">
            
            <h2 className="text-xl font-semibold mb-4 text-white">Quick Analysis</h2>
            <div className="flex gap-2 mb-8">
              <button className="text-sm bg-glass-bg border border-glass-border rounded-full px-4 py-2 text-text-light hover:bg-white/20 hover:text-white transition-colors">
                Summarize Data
              </button>
              <button className="text-sm bg-glass-bg border border-glass-border rounded-full px-4 py-2 text-text-light hover:bg-white/20 hover:text-white transition-colors">
                Find Correlations
              </button>
            </div>
            
            <h2 className="text-xl font-semibold mb-4 text-white">Upload Your Data</h2>
            
            <input 
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept=".csv, .xlsx, .xls"
            />
            
            <div 
              className="flex items-center justify-center h-48 rounded-lg border-2 border-dashed border-glass-border transition-colors hover:border-primary hover:bg-glass-bg cursor-pointer"
              onClick={handleUploadClick}
            >
              <button
                className="rounded-lg bg-primary px-5 py-2.5 font-medium text-white shadow-sm hover:bg-primary/80 pointer-events-none"
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Upload .CSV, .XLSX, .JSON'}
              </button>
            </div>
            {uploadError && <p className="mt-2 text-center text-red-400">{uploadError}</p>}

            <div className="mt-8 space-y-4">
              <AnimatePresence>
                {analysisResults.map(result => (
                  <AnalysisCard key={result.id} title={result.title}>
                    <p>{result.content}</p>
                  </AnalysisCard>
                ))}
              </AnimatePresence>
            </div>
          </main>
        </div>

        <RightSidebar />
      </div>

      {/* Modals */}
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
      </AnimatePresence>
    </>
  );
};