import { motion } from 'framer-motion';

// Define the props our modal will accept
interface UploadModalProps {
  onConfirm: () => void; // Function to call when user clicks "Yes"
  onCancel: () => void;  // Function to call when user clicks "No, Upload As-Is"
}

export const UploadModal = ({ onConfirm, onCancel }: UploadModalProps) => {
  return (
    // Backdrop
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <motion.div
        className="w-full max-w-md rounded-lg bg-card p-6 soft-shadow"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
      >
        <h2 className="text-xl font-semibold text-text-dark">
          Data Cleaning & Preprocessing
        </h2>
        
        <p className="mt-4 text-text-light">
          Do you want to perform data cleaning?
        </p>
        <p className="mt-2 text-sm text-gray-400">
          We highly recommend this as it will generate the best results.
        </p>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-border-light bg-card px-4 py-2 text-sm font-medium text-text-dark hover:bg-light-bg"
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