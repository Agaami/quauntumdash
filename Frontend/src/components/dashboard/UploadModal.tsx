import { motion } from 'framer-motion';

interface UploadModalProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export const UploadModal = ({ onConfirm, onCancel }: UploadModalProps) => {
  return (
    // Dark backdrop with blur
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <motion.div
        // 1. Use 'frosted-glass' for the white glassmorphism effect
        className="w-full max-w-md rounded-xl frosted-glass p-6 shadow-2xl"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
      >
        <h2 className="text-xl font-semibold text-text-dark">
          Data Cleaning & Preprocessing
        </h2>
        
        {/* 2. Set text colors to be dark and readable */}
        <p className="mt-4 text-text-light">
          Do you want to perform data cleaning?
        </p>
        <p className="mt-2 text-sm text-gray-500">
          We highly recommend this as it will generate the best results.
        </p>

        <div className="mt-6 flex justify-end gap-3">
          {/* 3. Light-mode "Cancel" button */}
          <button
            onClick={onCancel}
            className="rounded-lg border border-border-light bg-white/50 px-4 py-2 text-sm font-medium text-text-dark hover:bg-gray-100"
          >
            No, Upload As-Is
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80"
          >
            Yes, Clean Data
          </button>
        </div>
      </motion.div>
    </div>
  );
};
