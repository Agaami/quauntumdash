// Add this new interface to src/types.ts
export interface CleaningOptions {
  remove_duplicates: boolean;
  fill_missing_values: boolean;
  remove_empty_rows: boolean;
  remove_empty_columns: boolean;
  clean_text: boolean;
  standardize_column_names: boolean;
  optimize_data_types: boolean;
  remove_outliers: boolean;
  iqr_multiplier: number;
  normalize_numeric: boolean;
}