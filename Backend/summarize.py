import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LM Studio Configuration from environment
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama-3.1-8b-instruct")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate required environment variables
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable is not set")

from prompt import SYSTEM_PROMPT, SUMMARIZATION_PROMPT, format_columns_for_prompt


class DatabaseSummarizer:
    """Generate AI-powered summaries of database tables"""
    
    def __init__(self, connection_string: str = None):
        # Use provided connection_string or fall back to environment variable
        self.connection_string = connection_string or DATABASE_URL
        
        if not self.connection_string:
            raise ValueError("❌ Connection string must be provided or DATABASE_URL must be set")
    
    def get_db_connection(self):
        """Establish database connection"""
        try:
            return psycopg2.connect(self.connection_string)
        except Exception as e:
            print(f"❌ DB connection error: {e}")
            return None
    
    def generate_statistical_summary(self, table_name: str) -> Dict[str, Any]:
        """Generate comprehensive statistical summary of table data"""
        conn = self.get_db_connection()
        if not conn:
            raise Exception("Database connection failed")
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get column info
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name NOT IN ('uploaded_at', 'row_id')
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = cursor.fetchall()
            
            summary = {
                "table_name": table_name,
                "total_rows": 0,
                "total_columns": len(columns),
                "columns_summary": []
            }
            
            # Get row count
            cursor.execute(sql.SQL("SELECT COUNT(*) as count FROM {}").format(
                sql.Identifier(table_name)
            ))
            summary["total_rows"] = cursor.fetchone()['count']
            
            # Generate stats per column
            for col in columns:
                col_name = col['column_name']
                col_type = col['data_type']
                
                col_summary = {
                    "column_name": col_name,
                    "data_type": col_type,
                    "total_rows": summary["total_rows"]
                }
                
                # Numeric columns: min, max, avg, median
                if col_type in ['integer', 'numeric', 'double precision', 'real']:
                    cursor.execute(sql.SQL("""
                        SELECT 
                            MIN({col}) as min_val,
                            MAX({col}) as max_val,
                            AVG({col}) as avg_val,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {col}) as median_val,
                            COUNT(DISTINCT {col}) as unique_count,
                            COUNT(*) - COUNT({col}) as null_count
                        FROM {table}
                    """).format(
                        col=sql.Identifier(col_name),
                        table=sql.Identifier(table_name)
                    ))
                    stats = cursor.fetchone()
                    col_summary.update({
                        "min": float(stats['min_val']) if stats['min_val'] is not None else None,
                        "max": float(stats['max_val']) if stats['max_val'] is not None else None,
                        "avg": float(stats['avg_val']) if stats['avg_val'] is not None else None,
                        "median": float(stats['median_val']) if stats['median_val'] is not None else None,
                        "unique_values": stats['unique_count'],
                        "null_count": stats['null_count']
                    })
                
                # Text columns: unique values, top values
                elif col_type in ['text', 'character varying', 'varchar', 'char']:
                    cursor.execute(sql.SQL("""
                        SELECT 
                            COUNT(DISTINCT {col}) as unique_count,
                            COUNT(*) - COUNT({col}) as null_count
                        FROM {table}
                    """).format(
                        col=sql.Identifier(col_name),
                        table=sql.Identifier(table_name)
                    ))
                    stats = cursor.fetchone()
                    
                    # Get top 5 most frequent values
                    cursor.execute(sql.SQL("""
                        SELECT {col} as value, COUNT(*) as frequency
                        FROM {table}
                        WHERE {col} IS NOT NULL
                        GROUP BY {col}
                        ORDER BY frequency DESC
                        LIMIT 5
                    """).format(
                        col=sql.Identifier(col_name),
                        table=sql.Identifier(table_name)
                    ))
                    top_values = [dict(row) for row in cursor.fetchall()]
                    
                    col_summary.update({
                        "unique_values": stats['unique_count'],
                        "null_count": stats['null_count'],
                        "top_values": top_values
                    })
                
                # Boolean columns
                elif col_type == 'boolean':
                    cursor.execute(sql.SQL("""
                        SELECT 
                            SUM(CASE WHEN {col} = true THEN 1 ELSE 0 END) as true_count,
                            SUM(CASE WHEN {col} = false THEN 1 ELSE 0 END) as false_count,
                            COUNT(*) - COUNT({col}) as null_count
                        FROM {table}
                    """).format(
                        col=sql.Identifier(col_name),
                        table=sql.Identifier(table_name)
                    ))
                    stats = cursor.fetchone()
                    col_summary.update(dict(stats))
                
                summary["columns_summary"].append(col_summary)
            
            cursor.close()
            return summary
            
        finally:
            conn.close()
    
    def call_lm_studio(self, prompt: str) -> str:
        """Call LM Studio API for LLM inference"""
        try:
            url = f"{LM_STUDIO_BASE_URL}/v1/chat/completions"
            
            payload = {
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
                "stream": False
            }
            
            print(f"🤖 Calling LM Studio at {url}...")
            
            # --- THIS IS THE FIX ---
            # Increase timeout from 120 (2 mins) to 300 (5 mins)
            response = requests.post(url, json=payload, timeout=300)
            # --- END OF FIX ---
            
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.ConnectionError:
            return "⚠️ Error: Could not connect to LM Studio. Please ensure LM Studio is running on http://127.0.0.1:1234"
        except requests.exceptions.Timeout:
            return "⚠️ Error: LM Studio request timed out. The model may be too slow or overloaded."
        except requests.exceptions.RequestException as e:
            print(f"❌ LM Studio API error: {e}")
            return f"⚠️ Error calling LLM: {str(e)}"
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return f"⚠️ Error generating summary: {str(e)}"
    
    def generate_ai_summary(self, table_name: str) -> Dict[str, Any]:
        """Generate AI-powered summary of database table"""
        start_time = datetime.now()
        
        print(f"\n{'='*70}")
        print(f"🔍 GENERATING AI SUMMARY")
        print(f"{'='*70}")
        print(f"Table: {table_name}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Get statistical summary
        print("\n📊 Step 1/3: Collecting database statistics...")
        stats_summary = self.generate_statistical_summary(table_name)
        print(f"✅ Collected stats for {stats_summary['total_columns']} columns, {stats_summary['total_rows']} rows")
        
        # Step 2: Format prompt
        print("\n📝 Step 2/3: Formatting prompt for LLM...")
        columns_text = format_columns_for_prompt(stats_summary['columns_summary'])
        
        prompt = SUMMARIZATION_PROMPT.format(
            table_name=stats_summary['table_name'],
            total_rows=stats_summary['total_rows'],
            total_columns=stats_summary['total_columns'],
            columns_summary=columns_text
        )
        print(f"✅ Prompt formatted ({len(prompt)} characters)")
        
        # Step 3: Call LLM
        print("\n🤖 Step 3/3: Calling LM Studio LLM...")
        ai_insights = self.call_lm_studio(prompt)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Summary generation complete!")
        print(f"Duration: {duration:.2f} seconds")
        print(f"{'='*70}\n")
        
        return {
            "status": "success",
            "table_name": table_name,
            "generated_at": end_time.isoformat(),
            "duration_seconds": duration,
            "statistical_summary": stats_summary,
            "ai_insights": ai_insights,
            "prompt_length": len(prompt)
        }


# Standalone function for background task
def generate_summary_background(connection_string: str = None, table_name: str = None, user_id: str = None):
    """
    Background task function to generate summary
    This runs asynchronously after file upload completes
    
    Args:
        connection_string: Optional custom connection string (uses DATABASE_URL from env if not provided)
        table_name: Name of the table to summarize
        user_id: ID of the user requesting the summary
    """
    try:
        print(f"\n{'='*70}")
        print(f"🚀 BACKGROUND SUMMARIZATION STARTED")
        print(f"{'='*70}")
        print(f"User ID: {user_id}")
        print(f"Table: {table_name}")
        
        summarizer = DatabaseSummarizer(connection_string=connection_string)
        result = summarizer.generate_ai_summary(table_name)
        
        # Print AI insights to console
        print(f"\n{'='*70}")
        print(f"📋 AI INSIGHTS FOR TABLE: {table_name}")
        print(f"{'='*70}")
        print(result['ai_insights'])
        print(f"{'='*70}\n")
        
        # Optionally: Save to a summaries table or file
        # save_summary_to_db(user_id, table_name, result)
        
        return result
        
    except Exception as e:
        print(f"\n❌ Background summarization failed: {e}\n")
        return {"status": "error", "message": str(e)}
