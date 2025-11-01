import { motion } from 'framer-motion';
import { useState } from 'react';
import { type CleaningOptions } from '../../types';

interface CleaningModalProps {
  onConfirm: (options: CleaningOptions) => void;
  onCancel: () => void;
}

// 1. Checkbox style for light frosted glass
const CheckboxItem = ({ label, checked, onChange }: { label: string, checked: boolean, onChange: () => void }) => (
  <label className="flex items-center space-x-3 rounded-lg bg-white/50 p-3 cursor-pointer hover:bg-white/80">
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
    />
    <span className="text-sm font-medium text-text-dark">{label}</span>
  </label>
);

export const CleaningModal = ({ onConfirm, onCancel }: CleaningModalProps) => {
  const [options, setOptions] = useState<CleaningOptions>({
    remove_duplicates: true,
    fill_missing_values: true,
    remove_empty_rows: true,
    remove_empty_columns: true,
    clean_text: true,
    standardize_column_names: true,
    optimize_data_types: true,
    remove_outliers: false,
    iqr_multiplier: 1.5,
    normalize_numeric: false,
  });

  const handleChange = (option: keyof CleaningOptions) => {
    setOptions(prev => ({
      ...prev,
      [option]: !prev[option],
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <motion.div
        // 2. Use 'frosted-glass'
        className="w-full max-w-md rounded-xl frosted-glass p-6 shadow-2xl"
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
        <div className="mt-4 space-y-2 max-h-60 overflow-y-auto">
          <CheckboxItem label="Remove Duplicates" checked={options.remove_duplicates} onChange={() => handleChange('remove_duplicates')} />
          <CheckboxItem label="Fill Missing Values" checked={options.fill_missing_values} onChange={() => handleChange('fill_missing_values')} />
          <CheckboxItem label="Remove Empty Rows" checked={options.remove_empty_rows} onChange={() => handleChange('remove_empty_rows')} />
          <CheckboxItem label="Remove Empty Columns" checked={options.remove_empty_columns} onChange={() => handleChange('remove_empty_columns')} />
          <CheckboxItem label="Clean Text" checked={options.clean_text} onChange={() => handleChange('clean_text')} />
          <CheckboxItem label="Standardize Column Names" checked={options.standardize_column_names} onChange={() => handleChange('standardize_column_names')} />
          <CheckboxItem label="Optimize Data Types" checked={options.optimize_data_types} onChange={() => handleChange('optimize_data_types')} />
          <CheckboxItem label="Remove Outliers (IQR)" checked={options.remove_outliers} onChange={() => handleChange('remove_outliers')} />
        </div>

        {/* 3. Styled buttons for light mode */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-border-light bg-white/50 px-4 py-2 text-sm font-medium text-text-dark hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(options)}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/80"
          >
            Apply & Upload
          </button>
        </div>
      </motion.div>
    </div>
  );
};
