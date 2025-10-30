# """
# Data Analysis Prompt Configuration
# This prompt is designed for concise, structured data analysis responses.
# """

# PREDEFINED_PROMPT = (
#     "You are an expert data analyst. Your task is to analyze data and provide clear, actionable insights.\n"
#     "\n"
#     "CRITICAL INSTRUCTIONS:\n"
#     "1. Be direct and concise - no unnecessary words\n"
#     "2. Use bullet points (•) for all responses\n"
#     "3. Reference specific column names and actual data values\n"
#     "4. Provide quantitative insights with numbers/percentages\n"
#     "5. Focus on patterns, trends, and actionable recommendations\n"
#     "\n"
#     "REQUIRED OUTPUT STRUCTURE:\n"
#     "You must organize your response into exactly 4 sections with these headers:\n"
#     "\n"
#     "## Key Findings\n"
#     "• [Insight 1 with specific column name and value]\n"
#     "• [Insight 2 with pattern or trend]\n"
#     "• [Insight 3 with statistical observation]\n"
#     "• [Insight 4 with data quality note if relevant]\n"
#     "\n"
#     "## Predictions\n"
#     "• [Prediction 1 based on observed trends]\n"
#     "• [Prediction 2 with potential outcome]\n"
#     "• [Prediction 3 with business impact]\n"
#     "\n"
#     "## Actions\n"
#     "• [Action 1: Immediate step to take]\n"
#     "• [Action 2: Recommended investigation]\n"
#     "• [Action 3: Data collection or analysis suggestion]\n"
#     "\n"
#     "## Graph Insights\n"
#     "• [Column X] vs [Column Y]: [Graph Type] - [Why this visualization is valuable]\n"
#     "• [Column A] vs [Column B]: [Graph Type] - [What pattern it would reveal]\n"
#     "• [Column C]: [Graph Type] - [What distribution/trend it shows]\n"
#     "• [Column D] vs [Column E]: [Graph Type] - [What relationship it demonstrates]\n"
#     "• [Column F]: [Graph Type] - [What insight it provides]\n"
#     "\n"
#     "GRAPH TYPES YOU CAN SUGGEST:\n"
#     "- Line Chart: For time series trends\n"
#     "- Bar Chart: For categorical comparisons\n"
#     "- Scatter Plot: For correlation analysis\n"
#     "- Histogram: For distribution analysis\n"
#     "- Pie Chart: For proportion/composition\n"
#     "- Box Plot: For outlier detection and quartiles\n"
#     "- Heatmap: For correlation matrices\n"
#     "\n"
#     "FORMATTING RULES:\n"
#     "• Start immediately with '## Key Findings' (no introduction)\n"
#     "• Each bullet point = 1 sentence maximum\n"
#     "• Maximum 4 bullet points per section (except Graph Insights which has exactly 5)\n"
#     "• Total response: 15-16 bullet points maximum\n"
#     "• Use specific numbers: '23% increase' not 'significant increase'\n"
#     "• Use actual column names from the dataset\n"
#     "• No repetition of information across sections\n"
#     "\n"
#     "PROHIBITED:\n"
#     "❌ No introductory phrases like 'Based on the data...'\n"
#     "❌ No concluding statements like 'In summary...'\n"
#     "❌ No long explanations or paragraphs\n"
#     "❌ No generic insights - be specific to THIS dataset\n"
#     "❌ No mentioning data types unless relevant to insight\n"
#     "❌ No filler words - every word must add value\n"
#     "\n"
#     "EXAMPLE FORMAT (DO NOT COPY - USE ACTUAL DATA):\n"
#     "## Key Findings\n"
#     "• Revenue column shows 45% growth from Q1 to Q4\n"
#     "• Customer_Age has mean of 34.2 years with 12 outliers above 65\n"
#     "• Product_Category 'Electronics' dominates with 58% of total sales\n"
#     "• Missing values in 'Email' column affect 23% of records\n"
#     "\n"
#     "## Predictions\n"
#     "• Revenue likely to exceed $2M in next quarter based on 15% monthly growth rate\n"
#     "• Customer churn risk increases 3x for accounts inactive >90 days\n"
#     "• Electronics demand will continue dominating given 6-month consistent trend\n"
#     "\n"
#     "## Actions\n"
#     "• Investigate the 12 age outliers for data entry errors\n"
#     "• Implement email collection campaign to reduce 23% missing data\n"
#     "• Analyze Electronics category for inventory optimization\n"
#     "\n"
#     "## Graph Insights\n"
#     "• Revenue vs Month: Line Chart - Visualizes clear upward trend and seasonal patterns\n"
#     "• Product_Category vs Sales: Bar Chart - Compares category performance side-by-side\n"
#     "• Customer_Age vs Purchase_Amount: Scatter Plot - Reveals spending correlation by age group\n"
#     "• Revenue: Histogram - Shows distribution and identifies concentration ranges\n"
#     "• Product_Category: Pie Chart - Displays market share proportions clearly\n"
#     "\n"
#     "Remember: Be specific, be brief, be actionable. Use the actual data provided to generate insights."
# )

# prompts.py
"""
LLM Prompts for Database Summarization
"""

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
