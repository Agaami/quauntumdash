from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime
import os

# Import database utilities
from utils.data_ingestion.data_ingestion import get_db_connection, sanitize_table_name

# Import SQL agent functions
from utils.rag_agent.agent import (
    get_table_schema,
    get_table_stats,
    get_session_summary,
    generate_sql_query_with_llm,
    execute_sql_query,
    validate_sql_query
)

# Import session management
from utils.session.session_manager import log_session_activity
from utils.session.session_middleware import get_session_from_request
import psycopg2


# ==================== MODELS ====================

class NaturalLanguageQuery(BaseModel):
    user_query: str
    execute: bool = False  # Whether to execute the query or just generate it


class SQLAgentResponse(BaseModel):
    success: bool
    user_query: str
    generated_sql: Optional[str]
    table_name: str
    execution_result: Optional[dict] = None
    error: Optional[str] = None


# ==================== ROUTER ====================

router = APIRouter(
    prefix="/api/sql-agent",
    tags=["SQL Agent"],
    responses={404: {"description": "Not found"}}
)


# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    if request.client:
        return request.client.host
    
    return "unknown"


def get_session_db_connection():
    """Get connection to session database"""
    try:
        DATABASE_URL = os.getenv(
            "POSTGRES_URL", 
            "postgres://postgres.txfvbvtrqmvwpqjsjnxx:IeNr4DjZfNqa8RhY@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
        )
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Session DB connection error: {e}")
        return None


# ==================== ENDPOINTS ====================

@router.post("/query", response_model=SQLAgentResponse)
async def natural_language_to_sql(
    query_data: NaturalLanguageQuery,
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Convert natural language query to SQL and optionally execute it
    
    This endpoint:
    1. Retrieves user's table schema and generates data context
    2. Uses LLM to generate SQL query from natural language
    3. Validates the generated SQL
    4. Optionally executes the query
    5. Logs all actions to the session
    """
    user_id = session_data["user_id"]
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    try:
        # Get table name from user_id
        table_name = sanitize_table_name(user_id)
        
        print(f"\n{'='*60}")
        print(f"🔍 SQL AGENT REQUEST")
        print(f"{'='*60}")
        print(f"User ID: {user_id}")
        print(f"Session ID: {session_id}")
        print(f"Query: {query_data.user_query}")
        print(f"Execute: {query_data.execute}")
        print(f"{'='*60}\n")
        
        # Connect to user database
        conn = get_db_connection()
        if not conn:
            raise HTTPException(
                status_code=500,
                detail="Database connection failed"
            )
        
        try:
            # Get table schema
            schema = get_table_schema(conn, table_name)
            if not schema or not schema.get('columns'):
                log_session_activity(
                    session_id=session_id,
                    endpoint="/api/sql-agent/query",
                    method="POST",
                    request_path=str(request.url),
                    request_body=json.dumps({
                        "user_query": query_data.user_query,
                        "error": "No table found"
                    }),
                    response_status=404,
                    response_body=json.dumps({"error": "No table found"}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "sql_generation_failed",
                        "reason": "table_not_found"
                    }
                )
                
                raise HTTPException(
                    status_code=404,
                    detail=f"No data table found for user. Please upload data first."
                )
            
            # Get table statistics and sample data for context
            data_context = get_table_stats(conn, table_name)
            
            # Try to get summary from session logs (optional)
            session_conn = get_session_db_connection()
            if session_conn:
                try:
                    session_summary = get_session_summary(session_conn, session_id, table_name)
                    if session_summary:
                        data_context = f"{data_context}\n\nPrevious Summary: {session_summary}"
                finally:
                    session_conn.close()
            
            # Generate SQL query using LLM
            sql_result = generate_sql_query_with_llm(
                user_query=query_data.user_query,
                table_name=table_name,
                schema=schema,
                data_context=data_context,
                session_id=session_id
            )
            
            if not sql_result['success']:
                log_session_activity(
                    session_id=session_id,
                    endpoint="/api/sql-agent/query",
                    method="POST",
                    request_path=str(request.url),
                    request_body=json.dumps({
                        "user_query": query_data.user_query
                    }),
                    response_status=400,
                    response_body=json.dumps({"error": sql_result.get('error')}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "sql_generation_failed",
                        "error": sql_result.get('error')
                    }
                )
                
                raise HTTPException(
                    status_code=400,
                    detail=sql_result.get('error', 'Failed to generate SQL query')
                )
            
            generated_sql = sql_result['sql_query']
            
            # Validate SQL query
            validation = validate_sql_query(generated_sql)
            if not validation['valid']:
                log_session_activity(
                    session_id=session_id,
                    endpoint="/api/sql-agent/query",
                    method="POST",
                    request_path=str(request.url),
                    request_body=json.dumps({
                        "user_query": query_data.user_query,
                        "generated_sql": generated_sql
                    }),
                    response_status=400,
                    response_body=json.dumps({"error": validation['reason']}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "sql_validation_failed",
                        "reason": validation['reason'],
                        "generated_sql": generated_sql
                    }
                )
                
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid SQL query: {validation['reason']}"
                )
            
            # Execute query if requested
            execution_result = None
            if query_data.execute:
                exec_result = execute_sql_query(conn, generated_sql)
                
                if exec_result['success']:
                    execution_result = {
                        "row_count": exec_result['row_count'],
                        "results": exec_result['results']
                    }
                else:
                    log_session_activity(
                        session_id=session_id,
                        endpoint="/api/sql-agent/query",
                        method="POST",
                        request_path=str(request.url),
                        request_body=json.dumps({
                            "user_query": query_data.user_query,
                            "generated_sql": generated_sql,
                            "execute": True
                        }),
                        response_status=400,
                        response_body=json.dumps({"error": exec_result['error']}),
                        ip_address=client_ip,
                        user_agent=user_agent,
                        additional_info={
                            "action": "sql_execution_failed",
                            "error": exec_result['error'],
                            "generated_sql": generated_sql
                        }
                    )
                    
                    raise HTTPException(
                        status_code=400,
                        detail=exec_result['error']
                    )
            
            # LOG SUCCESSFUL SQL GENERATION (AND EXECUTION)
            log_session_activity(
                session_id=session_id,
                endpoint="/api/sql-agent/query",
                method="POST",
                request_path=str(request.url),
                request_body=json.dumps({
                    "user_query": query_data.user_query,
                    "execute": query_data.execute
                }),
                response_status=200,
                response_body=json.dumps({
                    "generated_sql": generated_sql,
                    "executed": query_data.execute,
                    "row_count": execution_result['row_count'] if execution_result else None
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "sql_generation_success",
                    "user_query": query_data.user_query,
                    "generated_sql": generated_sql,
                    "table_name": table_name,
                    "executed": query_data.execute,
                    "row_count": execution_result['row_count'] if execution_result else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return SQLAgentResponse(
                success=True,
                user_query=query_data.user_query,
                generated_sql=generated_sql,
                table_name=table_name,
                execution_result=execution_result
            )
        
        finally:
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors
        log_session_activity(
            session_id=session_id,
            endpoint="/api/sql-agent/query",
            method="POST",
            request_path=str(request.url),
            request_body=json.dumps({"user_query": query_data.user_query}),
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "sql_agent_error",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"SQL Agent error: {str(e)}"
        )


@router.get("/schema")
async def get_user_table_schema(
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """Get the schema of user's data table"""
    user_id = session_data["user_id"]
    table_name = sanitize_table_name(user_id)
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        schema = get_table_schema(conn, table_name)
        
        if not schema or not schema.get('columns'):
            raise HTTPException(
                status_code=404,
                detail="No table found. Please upload data first."
            )
        
        # Get table stats
        stats = get_table_stats(conn, table_name)
        
        return {
            "table_name": table_name,
            "schema": schema,
            "statistics": stats
        }
    finally:
        conn.close()
