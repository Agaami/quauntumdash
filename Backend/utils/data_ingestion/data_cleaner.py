import pandas as pd
import numpy as np
import re
from typing import Dict, Tuple
from pydantic import BaseModel


class CleaningOptions(BaseModel):
    """Options for data cleaning operations"""
    remove_duplicates: bool = True
    fill_missing_values: bool = True
    remove_empty_rows: bool = True
    remove_empty_columns: bool = True
    clean_text: bool = True
    standardize_column_names: bool = True
    optimize_data_types: bool = True
    remove_outliers: bool = False
    iqr_multiplier: float = 1.5
    normalize_numeric: bool = False


class DataCleaner:
    """
    Comprehensive data cleaning and preprocessing module
    """
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame, options: CleaningOptions) -> Tuple[pd.DataFrame, Dict]:
        """
        Clean and preprocess DataFrame based on provided options
        Returns: (cleaned_df, cleaning_report)
        """
        report = {
            "original_shape": df.shape,
            "operations": [],
            "options_applied": options.dict()
        }
        
        # Make a copy to avoid modifying original
        df_cleaned = df.copy()
        
        # 1. Remove completely empty rows
        if options.remove_empty_rows:
            initial_rows = len(df_cleaned)
            df_cleaned = df_cleaned.dropna(how='all')
            dropped_empty_rows = initial_rows - len(df_cleaned)
            if dropped_empty_rows > 0:
                report["operations"].append(f"Removed {dropped_empty_rows} completely empty rows")
        
        # 2. Remove completely empty columns
        if options.remove_empty_columns:
            initial_cols = len(df_cleaned.columns)
            df_cleaned = df_cleaned.dropna(axis=1, how='all')
            dropped_empty_cols = initial_cols - len(df_cleaned.columns)
            if dropped_empty_cols > 0:
                report["operations"].append(f"Removed {dropped_empty_cols} completely empty columns")
        
        # 3. Remove duplicate rows
        if options.remove_duplicates:
            initial_rows = len(df_cleaned)
            df_cleaned = df_cleaned.drop_duplicates()
            dropped_duplicates = initial_rows - len(df_cleaned)
            if dropped_duplicates > 0:
                report["operations"].append(f"Removed {dropped_duplicates} duplicate rows")
        
        # 4. Clean column names
        if options.standardize_column_names:
            df_cleaned.columns = [DataCleaner._clean_column_name(col) for col in df_cleaned.columns]
            report["operations"].append("Standardized column names")
        
        # 5. Handle missing values
        if options.fill_missing_values:
            missing_report = DataCleaner._handle_missing_values(df_cleaned)
            if missing_report:
                report["operations"].append(missing_report)
        
        # 6. Clean text columns
        if options.clean_text:
            text_cleaned = DataCleaner._clean_text_columns(df_cleaned)
            if text_cleaned > 0:
                report["operations"].append(f"Cleaned {text_cleaned} text columns (trimmed whitespace, removed special characters)")
        
        # 7. Standardize data types
        if options.optimize_data_types:
            df_cleaned = DataCleaner._standardize_data_types(df_cleaned)
            report["operations"].append("Optimized data types")
        
        # 8. Remove outliers from numeric columns (optional - using IQR method)
        if options.remove_outliers:
            initial_rows = len(df_cleaned)
            df_cleaned = DataCleaner._remove_outliers(df_cleaned, options.iqr_multiplier)
            outliers_removed = initial_rows - len(df_cleaned)
            if outliers_removed > 0:
                report["operations"].append(f"Removed {outliers_removed} outlier rows using IQR method (multiplier: {options.iqr_multiplier})")
        
        # 9. Normalize numeric columns (optional - scale to 0-1 range)
        if options.normalize_numeric:
            normalized_cols = DataCleaner._normalize_numeric_columns(df_cleaned)
            if normalized_cols > 0:
                report["operations"].append(f"Normalized {normalized_cols} numeric columns to 0-1 range")
        
        report["final_shape"] = df_cleaned.shape
        report["cleaning_summary"] = f"Cleaned data: {df_cleaned.shape[0]} rows × {df_cleaned.shape[1]} columns"
        
        return df_cleaned, report
    
    @staticmethod
    def _clean_column_name(col_name: str) -> str:
        """Clean and standardize column names"""
        # Convert to string and strip
        name = str(col_name).strip()
        
        # Replace multiple spaces with single underscore
        name = re.sub(r'\s+', '_', name)
        
        # Remove special characters except underscore
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        
        # Convert to lowercase
        name = name.lower()
        
        # Handle names starting with digit
        if name and name[0].isdigit():
            name = f"col_{name}"
        
        return name if name else "unnamed_column"
    
    @staticmethod
    def _handle_missing_values(df: pd.DataFrame) -> str:
        """Handle missing values in DataFrame"""
        total_missing = 0
        
        for col in df.columns:
            missing_count = df[col].isna().sum()
            
            if missing_count > 0:
                total_missing += missing_count
                
                # For numeric columns, fill with median
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col].fillna(df[col].median(), inplace=True)
                
                # For categorical/text columns, fill with mode or 'Unknown'
                elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                    mode_value = df[col].mode()
                    if len(mode_value) > 0:
                        df[col].fillna(mode_value[0], inplace=True)
                    else:
                        df[col].fillna('Unknown', inplace=True)
                
                # For datetime columns, forward fill
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col].fillna(method='ffill', inplace=True)
        
        if total_missing > 0:
            return f"Handled {total_missing} missing values (numeric: median, text: mode/Unknown, datetime: forward fill)"
        return ""
    
    @staticmethod
    def _clean_text_columns(df: pd.DataFrame) -> int:
        """Clean text columns - trim whitespace and remove extra spaces"""
        cleaned_count = 0
        
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                try:
                    # Strip whitespace
                    df[col] = df[col].astype(str).str.strip()
                    
                    # Replace multiple spaces with single space
                    df[col] = df[col].str.replace(r'\s+', ' ', regex=True)
                    
                    # Replace 'nan' string back to None
                    df[col] = df[col].replace(['nan', 'None', 'NULL', ''], None)
                    
                    cleaned_count += 1
                except:
                    pass
        
        return cleaned_count
    
    @staticmethod
    def _standardize_data_types(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize and standardize data types"""
        for col in df.columns:
            # Convert object columns that are actually numeric
            if df[col].dtype == 'object':
                try:
                    # Try to convert to numeric
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            
            # Optimize integer columns
            if pd.api.types.is_integer_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], downcast='integer')
            
            # Optimize float columns
            if pd.api.types.is_float_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], downcast='float')
        
        return df
    
    @staticmethod
    def _remove_outliers(df: pd.DataFrame, iqr_multiplier: float = 1.5) -> pd.DataFrame:
        """Remove outliers using IQR method for numeric columns"""
        df_no_outliers = df.copy()
        
        for col in df_no_outliers.columns:
            if pd.api.types.is_numeric_dtype(df_no_outliers[col]) and not pd.api.types.is_bool_dtype(df_no_outliers[col]):
                Q1 = df_no_outliers[col].quantile(0.25)
                Q3 = df_no_outliers[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - iqr_multiplier * IQR
                upper_bound = Q3 + iqr_multiplier * IQR
                
                # Remove rows with outliers
                df_no_outliers = df_no_outliers[
                    (df_no_outliers[col] >= lower_bound) & 
                    (df_no_outliers[col] <= upper_bound)
                ]
        
        return df_no_outliers
    
    @staticmethod
    def _normalize_numeric_columns(df: pd.DataFrame) -> int:
        """Normalize numeric columns to 0-1 range (Min-Max scaling)"""
        normalized_count = 0
        
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
                min_val = df[col].min()
                max_val = df[col].max()
                
                if max_val > min_val:  # Avoid division by zero
                    df[col] = (df[col] - min_val) / (max_val - min_val)
                    normalized_count += 1
        
        return normalized_count


def get_default_cleaning_options() -> CleaningOptions:
    """Get default cleaning options (safe defaults)"""
    return CleaningOptions(
        remove_duplicates=True,
        fill_missing_values=True,
        remove_empty_rows=True,
        remove_empty_columns=True,
        clean_text=True,
        standardize_column_names=True,
        optimize_data_types=True,
        remove_outliers=False,  # Disabled by default (can lose valid data)
        normalize_numeric=False  # Disabled by default (changes actual values)
    )

