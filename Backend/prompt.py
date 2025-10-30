
SYSTEM_PROMPT = """You are an expert data analyst specializing in statistical analysis and business intelligence. Your role is to analyze database statistics and provide clear, actionable insights that help users understand their data quickly."""

SUMMARIZATION_PROMPT = """
Analyze this database summary and provide comprehensive insights:

**Table Information:**
- Table Name: {table_name}
- Total Rows: {total_rows}
- Total Columns: {total_columns}

**Column Details:**
{columns_summary}

**Your Task:**
Provide a detailed analysis in the following format:

## Dataset Overview
Brief description of what this data represents based on column names and types.

## Key Statistics
- Highlight the most important numerical insights
- Note any interesting ranges, averages, or distributions
- Identify columns with the most variability

## Data Quality Assessment
- Report on missing values and their impact
- Note any data type inconsistencies
- Flag potential data quality issues

## Notable Patterns
- Identify interesting distributions or trends
- Highlight any categorical patterns (top values)
- Note any correlations or relationships you can infer

## Recommendations
- Suggest 3-5 specific analyses or visualizations
- Recommend data cleaning steps if needed
- Propose business questions this data could answer

Keep your response structured, concise, and focused on actionable insights. Use bullet points where appropriate.
"""


def format_columns_for_prompt(columns_summary: list) -> str:
    """Format column summaries into readable text for LLM prompt"""
    formatted = []
    
    for col in columns_summary:
        col_text = f"\n### {col['column_name']} ({col['data_type']})"
        
        # Numeric columns
        if 'min' in col and col['min'] is not None:
            col_text += f"\n- Range: {col['min']:.2f} to {col['max']:.2f}"
            if col['avg'] is not None:
                col_text += f"\n- Average: {col['avg']:.2f}"
            if col['median'] is not None:
                col_text += f"\n- Median: {col['median']:.2f}"
            col_text += f"\n- Unique values: {col['unique_values']}"
        
        # Text columns
        elif 'top_values' in col and col['top_values']:
            col_text += f"\n- Unique values: {col['unique_values']}"
            top_3 = col['top_values'][:3]
            col_text += "\n- Top values:"
            for v in top_3:
                col_text += f"\n  • {v['value']}: {v['frequency']} occurrences"
        
        # Boolean columns
        elif 'true_count' in col:
            col_text += f"\n- True: {col['true_count']}"
            col_text += f"\n- False: {col['false_count']}"
        
        # Missing values (all types)
        if 'null_count' in col and col['null_count'] > 0:
            null_percentage = (col['null_count'] / col.get('total_rows', 1)) * 100 if col.get('total_rows') else 0
            col_text += f"\n- Missing values: {col['null_count']} ({null_percentage:.1f}%)"
        
        formatted.append(col_text)
    
    return "\n".join(formatted)
