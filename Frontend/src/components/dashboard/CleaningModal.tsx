import { motion } from 'framer-motion';

// Define the props
interface CleaningModalProps {
  onConfirm: () => void; // Function to call when user clicks "Apply"
  onCancel: () => void;  // Function to call when user clicks "Cancel"
}

// A reusable checkbox component
const CheckboxItem = ({ label }: { label: string }) => (
  <label className="flex items-center space-x-3 rounded-lg bg-light-bg p-3">
    <input
      type="checkbox"
      defaultChecked
      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
    />
    <span className="text-sm font-medium text-text-dark">{label}</span>
  </label>
);

export const CleaningModal = ({ onConfirm, onCancel }: CleaningModalProps) => {
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
          Select Cleaning Steps
        </h2>
        <p className="mt-2 text-sm text-text-light">
          Choose the preprocessing steps you'd like to apply.
        </p>

        {/* Checklist */}
        <div className="mt-4 space-y-2">
          <CheckboxItem label="Remove Duplicates" />
          <CheckboxItem label="Fill Missing Values" />
          <CheckboxItem label="Remove Empty Rows & Columns" />
          <CheckboxItem label="Clean Text (lowercase, remove punctuation)" />
          <CheckboxItem label="Standardize Column Names" />
          <CheckboxItem label="Remove Outliers (using IQR)" />
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-border-light bg-card px-4 py-2 text-sm font-medium text-text-dark hover:bg-light-bg"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80"
          >
            Apply & Upload
          </button>
        </div>
      </motion.div>
    </div>
  );
};