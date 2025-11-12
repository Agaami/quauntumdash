from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, Request, Depends
import uuid
import json
from datetime import datetime


# Import from data_ingestion module
from utils.data_ingestion.data_ingestion import (
    FileUploadResponse,
    TableInfoResponse,
    SummaryResponse,
    allowed_file,
    get_file_extension,
    sanitize_table_name,
    read_file_to_dataframe,
    get_db_connection,
    get_table_info,
    table_exists,
    delete_table,
    list_all_tables,
    DataIngestionService,
    ALLOWED_EXTENSIONS,
    DATABASE_URL
)

from utils.data_ingestion.data_cleaner import CleaningOptions

# Import session management utilities
from utils.session.session_manager import log_session_activity, verify_session
from utils.session.session_middleware import get_session_from_request


# ==================== ROUTER CONFIGURATION ====================


router = APIRouter(
    prefix="/api/data",
    tags=["Data Ingestion & Summarization"],
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


# ==================== ENDPOINTS ====================


@router.post(
    "/upload-file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload data file",
    description="Upload CSV/Excel file with automatic AI summarization (requires session)"
)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="File to upload (CSV, XLSX, or XLS)"),
    apply_cleaning: bool = Form(False, description="Apply data cleaning"),
    remove_duplicates: bool = Form(True, description="Remove duplicate rows"),
    fill_missing_values: bool = Form(True, description="Fill missing values"),
    remove_empty_rows: bool = Form(True, description="Remove completely empty rows"),
    remove_empty_columns: bool = Form(True, description="Remove completely empty columns"),
    clean_text: bool = Form(True, description="Clean text columns"),
    standardize_column_names: bool = Form(True, description="Standardize column names"),
    optimize_data_types: bool = Form(True, description="Optimize data types"),
    remove_outliers: bool = Form(False, description="Remove outliers using IQR method"),
    iqr_multiplier: float = Form(1.5, description="IQR multiplier for outlier detection"),
    normalize_numeric: bool = Form(False, description="Normalize numeric columns"),
    session_data: dict = Depends(get_session_from_request)
):
    """
    Upload CSV/Excel file with automatic AI summarization
    
    Requires valid session. The file is processed, validated, and stored in database.
    AI summary is generated synchronously before returning response.
    All actions are logged to the session table.
    """
    cleaning_report = None
    
    # Get user_id from session
    user_id = session_data["user_id"]
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')

    try:
        # Validate file
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file_extension = get_file_extension(file.filename)

        # Read file
        content = await file.read()

        try:
            df = read_file_to_dataframe(content, file_extension)
        except Exception as e:
            # Log failed attempt
            log_session_activity(
                session_id=session_id,
                endpoint="/api/data/upload-file",
                method="POST",
                request_path=str(request.url),
                request_body=json.dumps({
                    "filename": file.filename,
                    "file_type": file_extension,
                    "error": "File reading failed"
                }),
                response_status=400,
                response_body=json.dumps({"error": str(e)}),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "file_upload_failed",
                    "error_type": "file_reading_error"
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading {file_extension.upper()} file: {str(e)}"
            )

        # Validate file is not empty
        if df.empty:
            log_session_activity(
                session_id=session_id,
                endpoint="/api/data/upload-file",
                method="POST",
                request_path=str(request.url),
                request_body=json.dumps({
                    "filename": file.filename,
                    "file_type": file_extension,
                    "error": "Empty file"
                }),
                response_status=400,
                response_body=json.dumps({"error": "File is empty"}),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "file_upload_failed",
                    "error_type": "empty_file"
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty. No data to upload."
            )

        # Apply cleaning if requested
        if apply_cleaning:
            cleaning_options = CleaningOptions(
                remove_duplicates=remove_duplicates,
                fill_missing_values=fill_missing_values,
                remove_empty_rows=remove_empty_rows,
                remove_empty_columns=remove_empty_columns,
                clean_text=clean_text,
                standardize_column_names=standardize_column_names,
                optimize_data_types=optimize_data_types,
                remove_outliers=remove_outliers,
                iqr_multiplier=iqr_multiplier,
                normalize_numeric=normalize_numeric
            )

            df, cleaning_report = DataIngestionService.process_file(df, apply_cleaning, cleaning_options)

            if df.empty:
                log_session_activity(
                    session_id=session_id,
                    endpoint="/api/data/upload-file",
                    method="POST",
                    request_path=str(request.url),
                    request_body=json.dumps({
                        "filename": file.filename,
                        "cleaning_applied": True,
                        "error": "All data removed during cleaning"
                    }),
                    response_status=400,
                    response_body=json.dumps({"error": "All data removed during cleaning"}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "file_upload_failed",
                        "error_type": "cleaning_removed_all_data"
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All data removed during cleaning. Adjust parameters."
                )

        # Database operations
        conn = get_db_connection()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection failed"
            )

        try:
            # Upload and generate summary synchronously (UPDATED TO HANDLE 4 RETURN VALUES)
            table_name, rows_inserted, sanitized_columns, summary_result = DataIngestionService.upload_and_store(
                conn, user_id, df, file_extension, generate_summary=True
            )
            
            # LOG SUCCESSFUL FILE UPLOAD WITH SUMMARY TO SESSION TABLE
            log_session_activity(
                session_id=session_id,
                endpoint="/api/data/upload-file",
                method="POST",
                request_path=str(request.url),
                request_body=json.dumps({
                    "filename": file.filename,
                    "file_type": file_extension,
                    "file_size": len(content),
                    "cleaning_applied": apply_cleaning
                }),
                response_status=201,
                response_body=json.dumps({
                    "table_name": table_name,
                    "rows_inserted": rows_inserted,
                    "columns": sanitized_columns,
                    "summary_status": summary_result.get("status") if summary_result else "not_generated"
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "file_upload_success",
                    "table_name": table_name,
                    "rows_count": rows_inserted,
                    "columns_count": len(sanitized_columns),
                    "cleaning_applied": apply_cleaning,
                    "cleaning_report": cleaning_report,
                    "summary_generated": summary_result is not None and summary_result.get("status") == "success",
                    "upload_timestamp": datetime.utcnow().isoformat()
                }
            )

            return FileUploadResponse(
                status=True,
                message=f"Successfully uploaded {rows_inserted} rows. AI summary generated.",
                table_name=table_name,
                rows_inserted=rows_inserted,
                columns=sanitized_columns,
                user_id=user_id,
                file_type=file_extension.upper(),
                cleaning_applied=apply_cleaning,
                cleaning_report=cleaning_report,
                summary=summary_result,  # Include the complete summary in response
                summarization_status="completed" if summary_result and summary_result.get("status") == "success" else "failed"
            )

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors
        log_session_activity(
            session_id=session_id,
            endpoint="/api/data/upload-file",
            method="POST",
            request_path=str(request.url),
            request_body=json.dumps({"filename": file.filename if file else "unknown"}),
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "file_upload_failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )



@router.get(
    "/summarize/{user_id}",
    response_model=SummaryResponse,
    summary="Get AI summary",
    description="Get AI-generated summary for user's data table (requires session)"
)
async def get_summary(
    user_id: str,
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Manually generate or retrieve AI summary for user's table
    Requires valid session. User can only access their own data.
    """
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    try:
        # Verify user can only access their own data
        if session_data["user_id"] != user_id:
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/summarize/{user_id}",
                method="GET",
                request_path=str(request.url),
                request_body=None,
                response_status=403,
                response_body=json.dumps({"error": "Access denied"}),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "unauthorized_access_attempt",
                    "requested_user_id": user_id,
                    "actual_user_id": session_data["user_id"]
                }
            )
            
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only access your own data."
            )
        
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        # Check table exists
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            if not table_exists(conn, table_name):
                log_session_activity(
                    session_id=session_id,
                    endpoint=f"/api/data/summarize/{user_id}",
                    method="GET",
                    request_path=str(request.url),
                    request_body=None,
                    response_status=404,
                    response_body=json.dumps({"error": "Table not found"}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "get_summary_failed",
                        "error": "table_not_found"
                    }
                )
                
                raise HTTPException(
                    status_code=404,
                    detail=f"No table found for user_id: {user_id}. Please upload a file first."
                )

            # Generate summary
            result = DataIngestionService.get_summary(user_id)
            
            # LOG SUCCESSFUL SUMMARY RETRIEVAL
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/summarize/{user_id}",
                method="GET",
                request_path=str(request.url),
                request_body=None,
                response_status=200,
                response_body=json.dumps({
                    "table_name": result.get("table_name"),
                    "summary_retrieved": True
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "get_summary_success",
                    "table_name": result.get("table_name"),
                    "retrieval_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return SummaryResponse(**result)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        log_session_activity(
            session_id=session_id,
            endpoint=f"/api/data/summarize/{user_id}",
            method="GET",
            request_path=str(request.url),
            request_body=None,
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "get_summary_failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}"
        )



@router.get(
    "/table-data/{user_id}",
    response_model=TableInfoResponse,
    summary="Get table data",
    description="Retrieve table information, metadata, and sample rows (requires session)"
)
async def get_table_data(
    user_id: str,
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Retrieve table information and sample data
    Requires valid session. User can only access their own data.
    """
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    try:
        # Verify user can only access their own data
        if session_data["user_id"] != user_id:
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/table-data/{user_id}",
                method="GET",
                request_path=str(request.url),
                request_body=None,
                response_status=403,
                response_body=json.dumps({"error": "Access denied"}),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "unauthorized_access_attempt",
                    "requested_user_id": user_id,
                    "actual_user_id": session_data["user_id"]
                }
            )
            
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only access your own data."
            )
        
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Check if table exists
            if not table_exists(conn, table_name):
                log_session_activity(
                    session_id=session_id,
                    endpoint=f"/api/data/table-data/{user_id}",
                    method="GET",
                    request_path=str(request.url),
                    request_body=None,
                    response_status=404,
                    response_body=json.dumps({"error": "Table not found"}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "get_table_data_failed",
                        "error": "table_not_found"
                    }
                )
                
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for user_id: {user_id}. Please upload a file first."
                )

            # Get table info
            info = get_table_info(conn, table_name)
            
            # LOG SUCCESSFUL TABLE DATA RETRIEVAL
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/table-data/{user_id}",
                method="GET",
                request_path=str(request.url),
                request_body=None,
                response_status=200,
                response_body=json.dumps({
                    "table_name": table_name,
                    "row_count": info['row_count'],
                    "column_count": len(info['columns'])
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "get_table_data_success",
                    "table_name": table_name,
                    "row_count": info['row_count'],
                    "retrieval_timestamp": datetime.utcnow().isoformat()
                }
            )

            return TableInfoResponse(
                table_name=table_name,
                row_count=info['row_count'],
                columns=info['columns'],
                sample_data=info['sample_data']
            )

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        log_session_activity(
            session_id=session_id,
            endpoint=f"/api/data/table-data/{user_id}",
            method="GET",
            request_path=str(request.url),
            request_body=None,
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "get_table_data_failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving table data: {str(e)}"
        )



@router.delete(
    "/table-data/{user_id}",
    summary="Delete table",
    description="Delete the table associated with a user_id (requires session)"
)
async def delete_table_data(
    user_id: str,
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Delete the table associated with a user_id
    
    Requires valid session. User can only delete their own data.
    This permanently removes all data associated with the user_id.
    """
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    try:
        # Verify user can only delete their own data
        if session_data["user_id"] != user_id:
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/table-data/{user_id}",
                method="DELETE",
                request_path=str(request.url),
                request_body=None,
                response_status=403,
                response_body=json.dumps({"error": "Access denied"}),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "unauthorized_deletion_attempt",
                    "requested_user_id": user_id,
                    "actual_user_id": session_data["user_id"]
                }
            )
            
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only delete your own data."
            )
        
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Check if table exists
            if not table_exists(conn, table_name):
                log_session_activity(
                    session_id=session_id,
                    endpoint=f"/api/data/table-data/{user_id}",
                    method="DELETE",
                    request_path=str(request.url),
                    request_body=None,
                    response_status=404,
                    response_body=json.dumps({"error": "Table not found"}),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    additional_info={
                        "action": "delete_table_failed",
                        "error": "table_not_found"
                    }
                )
                
                raise HTTPException(
                    status_code=404,
                    detail=f"No table found for user_id: {user_id}"
                )

            # Delete table
            delete_table(conn, table_name)
            
            # LOG SUCCESSFUL TABLE DELETION
            log_session_activity(
                session_id=session_id,
                endpoint=f"/api/data/table-data/{user_id}",
                method="DELETE",
                request_path=str(request.url),
                request_body=None,
                response_status=200,
                response_body=json.dumps({
                    "table_name": table_name,
                    "deleted": True
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "delete_table_success",
                    "table_name": table_name,
                    "deletion_timestamp": datetime.utcnow().isoformat()
                }
            )

            return {
                "status": True,
                "message": f"Successfully deleted table '{table_name}'",
                "table_name": table_name,
                "user_id": user_id
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        log_session_activity(
            session_id=session_id,
            endpoint=f"/api/data/table-data/{user_id}",
            method="DELETE",
            request_path=str(request.url),
            request_body=None,
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "delete_table_failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting table: {str(e)}"
        )



@router.get(
    "/list-user-tables",
    summary="List all tables",
    description="List all user data tables in the database (requires session)"
)
async def list_user_tables(
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    List all user data tables in the database
    
    Requires valid session. Returns all tables created through data uploads with their column counts.
    """
    session_id = request.state.session_id
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Get list of all tables
            tables = list_all_tables(conn)
            
            # LOG SUCCESSFUL TABLE LIST RETRIEVAL
            log_session_activity(
                session_id=session_id,
                endpoint="/api/data/list-user-tables",
                method="GET",
                request_path=str(request.url),
                request_body=None,
                response_status=200,
                response_body=json.dumps({
                    "table_count": len(tables)
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "list_tables_success",
                    "table_count": len(tables),
                    "retrieval_timestamp": datetime.utcnow().isoformat()
                }
            )

            return {
                "status": True,
                "count": len(tables),
                "tables": tables
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        log_session_activity(
            session_id=session_id,
            endpoint="/api/data/list-user-tables",
            method="GET",
            request_path=str(request.url),
            request_body=None,
            response_status=500,
            response_body=json.dumps({"error": str(e)}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "list_tables_failed",
                "error_type": "unexpected_error",
                "error_message": str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error listing tables: {str(e)}"
        )
