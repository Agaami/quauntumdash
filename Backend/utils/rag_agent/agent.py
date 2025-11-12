import os
import json
from typing import Dict, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import re
from decimal import Decimal

# Import prompts from prompts.py
from utils.rag_agent.rag_prompt import (
    SQL_GENERATION_SYSTEM_PROMPT,
    SQL_GENERATION_PROMPT
)

# LM Studio configuration
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama-3.1-8b-instruct")


def sanitize_identifier(name: str) -> str:
    """
    Sanitize any database identifier (table name, column name, etc.)
    Ensures it's a valid PostgreSQL identifier
    """
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace('-', '_'))
    clean_name = clean_name.lower()
    
    # Add prefix if starts with digit
    if clean_name and clean_name[0].isdigit():
        clean_name = f"tbl_{clean_name}"
    
    return clean_name


def get_table_schema(conn, table_name: str) -> Dict:
    """Get table schema information including columns and types"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n📋 Getting schema for table: {table_name}")
        
        # Get column information
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cursor.fetchall()
        cursor.close()
        
        print(f"✅ Found {len(columns)} columns")
        for col in columns:
            print(f"   - {col['column_name']} ({col['data_type']})")
        
        return {
            "table_name": table_name,
            "columns": [dict(col) for col in columns]
        }
    except Exception as e:
        print(f"❌ Error getting table schema: {e}")
        return {}


def get_table_stats(conn, table_name: str) -> Optional[str]:
    """
    Generate basic statistics about the table data
    This replaces the need for a separate summaries table
    """
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n📊 Getting statistics for table: {table_name}")
        
        # Use sql.Identifier to properly quote table name
        count_query = sql.SQL("SELECT COUNT(*) as row_count FROM {}").format(
            sql.Identifier(table_name)
        )
        cursor.execute(count_query)
        row_count = cursor.fetchone()['row_count']
        
        print(f"✅ Total rows: {row_count}")
        
        # Get column info
        cursor.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name NOT IN ('uploaded_at', 'row_id')
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        stats_text = f"Table has {row_count} rows.\n"
        stats_text += f"Columns: {', '.join([col['column_name'] for col in columns])}\n"
        
        # Get sample values for better context using properly quoted identifier
        sample_query = sql.SQL("SELECT * FROM {} LIMIT 3").format(
            sql.Identifier(table_name)
        )
        cursor.execute(sample_query)
        samples = cursor.fetchall()
        
        if samples:
            print(f"✅ Sample data retrieved (3 rows)")
            stats_text += "\nSample data (first 3 rows):\n"
            for i, row in enumerate(samples, 1):
                row_dict = dict(row)
                # Convert Decimal to float for display
                for key, value in row_dict.items():
                    if isinstance(value, Decimal):
                        row_dict[key] = float(value)
                print(f"   Row {i}: {row_dict}")
                stats_text += f"Row {i}: {row_dict}\n"
        
        cursor.close()
        return stats_text
        
    except Exception as e:
        print(f"❌ Error getting table stats: {e}")
        return None


def get_session_summary(session_conn, session_id: str, table_name: str) -> Optional[str]:
    """
    Try to retrieve summary from session logs
    This is optional - if it fails, we just skip it
    """
    try:
        cursor = session_conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n🔍 Looking for session summary...")
        
        # Get the session table name
        cursor.execute(
            "SELECT session_table_name FROM session_master WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            print(f"⚠️  Session not found in session_master (skipping)")
            cursor.close()
            return None
        
        session_table = result['session_table_name']
        print(f"   Session table: {session_table}")
        
        # Try to query - if it fails, just return None
        try:
            query = sql.SQL("""
                SELECT additional_info
                FROM {}
                WHERE endpoint = '/api/data/upload-file'
                AND action_timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY action_timestamp DESC
                LIMIT 1
            """).format(sql.Identifier(session_table))
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result and result['additional_info']:
                additional_info = result['additional_info']
                if isinstance(additional_info, dict):
                    summary = additional_info.get('data_summary', None)
                    if summary:
                        print(f"✅ Found summary in session logs")
                        cursor.close()
                        return summary
            
            print(f"⚠️  No summary found in session logs (skipping)")
        except Exception as e:
            print(f"⚠️  Could not retrieve session summary (skipping): {str(e)}")
        
        cursor.close()
        return None
        
    except Exception as e:
        print(f"⚠️  Session summary lookup failed (skipping): {str(e)}")
        return None


def generate_sql_query_with_llm(
    user_query: str,
    table_name: str,
    schema: Dict,
    data_context: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, str]:
    """Use LLM to generate SQL query from natural language"""
    try:
        import requests
        
        print(f"\n🤖 Generating SQL query with LLM...")
        print(f"   User Query: {user_query}")
        print(f"   Table: {table_name}")
        
        # Build context for the LLM
        columns_info = "\n".join([
            f"  - {col['column_name']} ({col['data_type']})"
            for col in schema.get('columns', [])
        ])
        
        context_section = f"\n\nData Context:\n{data_context}" if data_context else ""
        
        # Create prompt using the imported template
        prompt = SQL_GENERATION_PROMPT.format(
            table_name=table_name,
            columns_info=columns_info,
            context_section=context_section,
            user_query=user_query
        )

        # Call LM Studio API
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": SQL_GENERATION_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            sql_query = result['choices'][0]['message']['content'].strip()
            
            # Clean up the SQL query
            sql_query = sql_query.replace("``````", "").strip()
            sql_query = sql_query.rstrip(';')  # Remove trailing semicolon
            
            # Ensure table name is quoted if not already
            if f'"{table_name}"' not in sql_query and table_name in sql_query:
                sql_query = sql_query.replace(f' {table_name} ', f' "{table_name}" ')
                sql_query = sql_query.replace(f' {table_name}\n', f' "{table_name}"\n')
                sql_query = sql_query.replace(f'FROM {table_name}', f'FROM "{table_name}"')
                sql_query = sql_query.replace(f'from {table_name}', f'FROM "{table_name}"')
            
            print(f"✅ Generated SQL: {sql_query}")
            
            # Validate it's a SELECT query
            if not sql_query.upper().startswith("SELECT"):
                print(f"❌ Query is not a SELECT statement")
                return {
                    "success": False,
                    "error": "Generated query is not a SELECT statement",
                    "sql_query": None
                }
            
            return {
                "success": True,
                "sql_query": sql_query,
                "table_name": table_name
            }
        else:
            print(f"❌ LLM API error: {response.status_code}")
            return {
                "success": False,
                "error": f"LLM API error: {response.status_code}",
                "sql_query": None
            }
            
    except Exception as e:
        print(f"❌ Error generating SQL: {str(e)}")
        return {
            "success": False,
            "error": f"Error generating SQL: {str(e)}",
            "sql_query": None
        }


def execute_sql_query(conn, sql_query: str) -> Dict:
    """Execute SQL query and return results"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n🔍 Executing SQL query...")
        print(f"   Query: {sql_query}")
        
        # Execute query
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        cursor.close()
        
        print(f"✅ Query executed successfully!")
        print(f"   Rows returned: {len(results)}")
        
        # Convert datetime and Decimal objects to strings for JSON serialization
        json_results = []
        for i, row in enumerate(results):
            json_row = {}
            for key, value in dict(row).items():
                if isinstance(value, datetime):
                    json_row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    json_row[key] = float(value)
                else:
                    json_row[key] = value
            json_results.append(json_row)
            
            # Print results to terminal
            if i < 10:  # Print first 10 rows
                print(f"\n   Row {i+1}:")
                for key, value in json_row.items():
                    print(f"      {key}: {value}")
        
        if len(results) > 10:
            print(f"\n   ... and {len(results) - 10} more rows")
        
        print(f"\n{'='*60}")
        print(f"📊 QUERY RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"Total Rows: {len(results)}")
        if json_results:
            print(f"Columns: {', '.join(json_results[0].keys())}")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "row_count": len(results),
            "results": json_results
        }
    except Exception as e:
        print(f"❌ Query execution failed: {str(e)}")
        return {
            "success": False,
            "error": f"Query execution failed: {str(e)}",
            "results": []
        }


def validate_sql_query(sql_query: str) -> Dict[str, bool]:
    """Basic validation to ensure query is safe"""
    sql_upper = sql_query.upper().strip()
    
    print(f"\n🔒 Validating SQL query...")
    
    # Check if it's a SELECT query
    if not sql_upper.startswith("SELECT"):
        print(f"❌ Validation failed: Not a SELECT query")
        return {
            "valid": False,
            "reason": "Only SELECT queries are allowed"
        }
    
    # Check for dangerous keywords
    dangerous_keywords = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
        "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC"
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            print(f"❌ Validation failed: Contains forbidden keyword '{keyword}'")
            return {
                "valid": False,
                "reason": f"Query contains forbidden keyword: {keyword}"
            }
    
    print(f"✅ Query validation passed")
    return {"valid": True}
