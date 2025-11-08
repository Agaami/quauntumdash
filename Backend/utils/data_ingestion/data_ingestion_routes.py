from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, BackgroundTasks
import uuid

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
from utils.summarize import generate_summary_background


# ==================== ROUTER CONFIGURATION ====================

router = APIRouter(
    prefix="/api/data",
    tags=["Data Ingestion & Summarization"],
    responses={404: {"description": "Not found"}}
)


# ==================== ENDPOINTS ====================

@router.post(
    "/upload-file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload data file",
    description="Upload CSV/Excel file with automatic AI summarization in background"
)
async def upload_file(
    background_tasks: BackgroundTasks,
    user_id: str = Form(..., description="User ID (UUID format)"),
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
    normalize_numeric: bool = Form(False, description="Normalize numeric columns")
):
    """
    Upload CSV/Excel file with automatic AI summarization
    
    The file is processed, validated, and stored in database.
    AI summary generation runs in background after upload completes.
    """
    cleaning_report = None

    try:
        # Validate file
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file_extension = get_file_extension(file.filename)

        # Validate user_id format
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format. Must be a valid UUID."
            )

        # Read file
        content = await file.read()

        try:
            df = read_file_to_dataframe(content, file_extension)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading {file_extension.upper()} file: {str(e)}"
            )

        # Validate file is not empty
        if df.empty:
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
            table_name, rows_inserted, sanitized_columns = DataIngestionService.upload_and_store(
                conn, user_id, df, file_extension
            )

            # Trigger background summarization
            background_tasks.add_task(
                generate_summary_background,
                DATABASE_URL,
                table_name,
                user_id
            )

            return FileUploadResponse(
                status=True,
                message=f"Successfully uploaded {rows_inserted} rows. AI summary generating in background.",
                table_name=table_name,
                rows_inserted=rows_inserted,
                columns=sanitized_columns,
                user_id=user_id,
                file_type=file_extension.upper(),
                cleaning_applied=apply_cleaning,
                cleaning_report=cleaning_report,
                summarization_status="in_progress"
            )

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get(
    "/summarize/{user_id}",
    response_model=SummaryResponse,
    summary="Get AI summary",
    description="Get AI-generated summary for user's data table"
)
async def get_summary(user_id: str):
    """
    Manually generate or retrieve AI summary for user's table
    """
    try:
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        # Check table exists
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            if not table_exists(conn, table_name):
                raise HTTPException(
                    status_code=404,
                    detail=f"No table found for user_id: {user_id}. Please upload a file first."
                )

            # Generate summary
            result = DataIngestionService.get_summary(user_id)
            return SummaryResponse(**result)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}"
        )


@router.get(
    "/table-data/{user_id}",
    response_model=TableInfoResponse,
    summary="Get table data",
    description="Retrieve table information, metadata, and sample rows"
)
async def get_table_data(user_id: str):
    """
    Retrieve table information and sample data
    """
    try:
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Check if table exists
            if not table_exists(conn, table_name):
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for user_id: {user_id}. Please upload a file first."
                )

            # Get table info
            info = get_table_info(conn, table_name)

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
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving table data: {str(e)}"
        )


@router.delete(
    "/table-data/{user_id}",
    summary="Delete table",
    description="Delete the table associated with a user_id"
)
async def delete_table_data(user_id: str):
    """
    Delete the table associated with a user_id
    
    This permanently removes all data associated with the user_id.
    """
    try:
        # Validate user_id format
        uuid.UUID(user_id)
        table_name = sanitize_table_name(user_id)

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Check if table exists
            if not table_exists(conn, table_name):
                raise HTTPException(
                    status_code=404,
                    detail=f"No table found for user_id: {user_id}"
                )

            # Delete table
            delete_table(conn, table_name)

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
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting table: {str(e)}"
        )


@router.get(
    "/list-user-tables",
    summary="List all tables",
    description="List all user data tables in the database"
)
async def list_user_tables():
    """
    List all user data tables in the database
    
    Returns all tables created through data uploads with their column counts.
    """
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB connection failed")

        try:
            # Get list of all tables
            tables = list_all_tables(conn)

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
        raise HTTPException(
            status_code=500,
            detail=f"Error listing tables: {str(e)}"
        )
