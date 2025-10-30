import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2 import sql
import pandas as pd
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from io import BytesIO, StringIO
import re
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import data cleaning and summarization
from data_cleaner import DataCleaner, CleaningOptions
from summarize import DatabaseSummarizer, generate_summary_background


# ==================== CONFIGURATION ====================

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL not found in .env file")

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


# ==================== PYDANTIC MODELS ====================

class FileUploadResponse(BaseModel):
    """Response model for file upload endpoint"""
    status: bool
    message: str
    table_name: str
    rows_inserted: int
    columns: list
    user_id: str
    file_type: str
    cleaning_applied: bool
    cleaning_report: Optional[dict] = None
    summarization_status: str


class TableInfoResponse(BaseModel):
    """Response model for table info endpoint"""
    table_name: str
    row_count: int
    columns: list
    sample_data: Optional[list] = None


class SummaryResponse(BaseModel):
    """Response model for summary endpoint"""
    status: str
    table_name: str
    generated_at: str
    duration_seconds: float
    statistical_summary: dict
    ai_insights: str
    prompt_length: int


# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """
    Establish connection to PostgreSQL database
    
    Returns:
        Connection object or None if connection fails
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"DB connection error: {e}")
        return None


# ==================== UTILITY FUNCTIONS ====================

def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension in lowercase
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def sanitize_table_name(user_id: str) -> str:
    """
    Create a valid PostgreSQL table name from user_id
    Removes special characters and converts to lowercase
    
    Args:
        user_id: User ID (usually UUID)
        
    Returns:
        Sanitized table name safe for PostgreSQL
    """
    clean_id = re.sub(r'[^a-zA-Z0-9_]', '', user_id.replace('-', '_'))
    return clean_id.lower()


def sanitize_column_name(col_name: str) -> str:
    """
    Sanitize column names for PostgreSQL
    Removes special characters, replaces spaces with underscores
    
    Args:
        col_name: Original column name
        
    Returns:
        Sanitized column name safe for PostgreSQL
    """
    clean_name = str(col_name).strip().replace(' ', '_')
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', clean_name)
    if clean_name and clean_name[0].isdigit():
        clean_name = f"col_{clean_name}"
    return clean_name.lower() if clean_name else "unnamed_column"


def infer_postgres_type(dtype) -> str:
    """
    Infer PostgreSQL column type from pandas dtype
    
    Args:
        dtype: Pandas data type
        
    Returns:
        PostgreSQL type string
    """
    dtype_str = str(dtype)

    if 'int' in dtype_str:
        return 'INTEGER'
    elif 'float' in dtype_str:
        return 'NUMERIC'
    elif 'bool' in dtype_str:
        return 'BOOLEAN'
    elif 'datetime' in dtype_str:
        return 'TIMESTAMP'
    elif 'date' in dtype_str:
        return 'DATE'
    else:
        return 'TEXT'


def read_file_to_dataframe(content: bytes, file_extension: str) -> pd.DataFrame:
    """
    Read file content into pandas DataFrame
    Supports CSV, XLSX, XLS formats
    
    Args:
        content: File content as bytes
        file_extension: File extension (csv, xlsx, xls)
        
    Returns:
        pandas DataFrame
        
    Raises:
        Exception: If file cannot be read
    """
    try:
        if file_extension == 'csv':
            text_content = content.decode('utf-8')
            df = pd.read_csv(StringIO(text_content))
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(BytesIO(content), engine='openpyxl' if file_extension == 'xlsx' else None)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")
        return df

    except UnicodeDecodeError:
        if file_extension == 'csv':
            for encoding in ['latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    text_content = content.decode(encoding)
                    df = pd.read_csv(StringIO(text_content))
                    print(f"Successfully read CSV with {encoding} encoding")
                    return df
                except:
                    continue
        raise Exception("Failed to decode file. Please check file encoding.")

    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")


# ==================== TABLE CREATION ====================

def create_table_from_dataframe(conn, table_name: str, df: pd.DataFrame, drop_if_exists: bool = True):
    """
    Dynamically create PostgreSQL table from DataFrame schema
    
    Args:
        conn: Database connection
        table_name: Name of table to create
        df: DataFrame with data
        drop_if_exists: Whether to drop existing table first
        
    Returns:
        True if successful
        
    Raises:
        Exception: If table creation fails
    """
    cursor = conn.cursor()

    try:
        if drop_if_exists:
            drop_query = sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            )
            cursor.execute(drop_query)
            print(f"Dropped existing table: {table_name}")

        # Sanitize column names
        df.columns = [sanitize_column_name(col) for col in df.columns]

        # Build column definitions
        columns_def = []
        for col_name, dtype in df.dtypes.items():
            pg_type = infer_postgres_type(dtype)
            columns_def.append(
                sql.SQL("{} {}").format(
                    sql.Identifier(col_name),
                    sql.SQL(pg_type)
                )
            )

        # Add metadata columns
        columns_def.append(sql.SQL("uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        columns_def.append(sql.SQL("row_id SERIAL PRIMARY KEY"))

        # Create table
        create_query = sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(columns_def)
        )

        cursor.execute(create_query)
        conn.commit()
        print(f"Created table: {table_name}")

        return True

    except Exception as e:
        conn.rollback()
        raise Exception(f"Error creating table: {e}")
    finally:
        cursor.close()


# ==================== DATA INSERTION ====================

def insert_dataframe_to_table(conn, table_name: str, df: pd.DataFrame):
    """
    Insert DataFrame data into PostgreSQL table using bulk insert
    
    Args:
        conn: Database connection
        table_name: Name of table to insert into
        df: DataFrame with data to insert
        
    Returns:
        Number of rows inserted
        
    Raises:
        Exception: If insertion fails
    """
    cursor = conn.cursor()

    try:
        # Sanitize column names
        df.columns = [sanitize_column_name(col) for col in df.columns]
        
        # Replace NaN values with None
        df = df.replace({np.nan: None, pd.NaT: None})

        # Convert to tuples
        data_tuples = [tuple(row) for row in df.to_numpy()]

        # Build column list
        columns = sql.SQL(', ').join(map(sql.Identifier, df.columns))

        # Build insert query
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table_name),
            columns
        )

        # Bulk insert with pagination
        execute_values(
            cursor,
            insert_query.as_string(conn),
            data_tuples,
            page_size=1000
        )

        conn.commit()
        rows_inserted = len(data_tuples)
        print(f"✅ Inserted {rows_inserted} rows into {table_name} using bulk insert")

        return rows_inserted

    except Exception as e:
        conn.rollback()
        raise Exception(f"Error inserting data: {e}")
    finally:
        cursor.close()


# ==================== TABLE DELETION ====================

def delete_table(conn, table_name: str):
    """
    Delete table from database
    
    Args:
        conn: Database connection
        table_name: Name of table to delete
        
    Returns:
        True if successful
        
    Raises:
        Exception: If deletion fails
    """
    cursor = conn.cursor()

    try:
        drop_query = sql.SQL("DROP TABLE {} CASCADE").format(
            sql.Identifier(table_name)
        )
        cursor.execute(drop_query)
        conn.commit()
        print(f"🗑️ Deleted table: {table_name}")
        return True

    except Exception as e:
        conn.rollback()
        raise Exception(f"Error deleting table: {e}")
    finally:
        cursor.close()


# ==================== TABLE INFO RETRIEVAL ====================

def get_table_info(conn, table_name: str) -> dict:
    """
    Get table metadata and sample data
    
    Args:
        conn: Database connection
        table_name: Name of table
        
    Returns:
        Dictionary with columns, row_count, and sample_data
        
    Raises:
        Exception: If query fails
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get column information
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))

        columns = [
            {"name": row['column_name'], "type": row['data_type']} 
            for row in cursor.fetchall()
        ]

        # Get row count
        count_query = sql.SQL("SELECT COUNT(*) as count FROM {}").format(
            sql.Identifier(table_name)
        )
        cursor.execute(count_query)
        row_count = cursor.fetchone()['count']

        # Get sample data
        sample_query = sql.SQL("SELECT * FROM {} LIMIT 5").format(
            sql.Identifier(table_name)
        )
        cursor.execute(sample_query)
        sample_data = [dict(row) for row in cursor.fetchall()]

        # Convert datetime objects to ISO format
        for row in sample_data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()

        return {
            "columns": columns,
            "row_count": row_count,
            "sample_data": sample_data
        }

    except Exception as e:
        raise Exception(f"Error getting table info: {e}")
    finally:
        cursor.close()


# ==================== TABLE EXISTENCE CHECK ====================

def table_exists(conn, table_name: str) -> bool:
    """
    Check if table exists in database
    
    Args:
        conn: Database connection
        table_name: Name of table to check
        
    Returns:
        True if table exists, False otherwise
    """
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))

        exists = cursor.fetchone()[0]
        return exists

    except Exception as e:
        print(f"Error checking table existence: {e}")
        return False
    finally:
        cursor.close()


# ==================== LIST ALL TABLES ====================

def list_all_tables(conn) -> list:
    """
    List all user data tables in database
    
    Args:
        conn: Database connection
        
    Returns:
        List of tables with column counts
        
    Raises:
        Exception: If query fails
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = [dict(row) for row in cursor.fetchall()]
        return tables

    except Exception as e:
        raise Exception(f"Error listing tables: {e}")
    finally:
        cursor.close()


# ==================== DATA INGESTION SERVICE ====================

class DataIngestionService:
    """
    Service class for data ingestion operations
    Handles file processing, storage, and retrieval
    """

    @staticmethod
    def process_file(df: pd.DataFrame, apply_cleaning: bool, cleaning_options: CleaningOptions) -> tuple:
        """
        Process DataFrame with optional cleaning
        
        Args:
            df: DataFrame to process
            apply_cleaning: Whether to apply cleaning
            cleaning_options: CleaningOptions object with cleaning parameters
            
        Returns:
            Tuple of (cleaned_df, cleaning_report)
            
        Raises:
            Exception: If all data is removed during cleaning
        """
        cleaning_report = None

        if apply_cleaning:
            print("\n🧹 Applying data cleaning...")
            df, cleaning_report = DataCleaner.clean_dataframe(df, cleaning_options)
            print(f"✅ Cleaning completed: {cleaning_report['cleaning_summary']}")

            if df.empty:
                raise Exception("All data removed during cleaning. Adjust parameters.")

        return df, cleaning_report

    @staticmethod
    def upload_and_store(conn, user_id: str, df: pd.DataFrame, file_extension: str) -> tuple:
        """
        Upload file data to database and prepare for summarization
        
        Args:
            conn: Database connection
            user_id: User ID (UUID)
            df: DataFrame with data
            file_extension: File extension (csv, xlsx, xls)
            
        Returns:
            Tuple of (table_name, rows_inserted, sanitized_columns)
            
        Raises:
            Exception: If upload fails
        """
        table_name = sanitize_table_name(user_id)
        sanitized_columns = [sanitize_column_name(col) for col in df.columns]

        print("\n" + "="*60)
        print(f"📊 FILE UPLOAD - {file_extension.upper()}")
        print("="*60)
        print(f"User ID: {user_id}")
        print(f"Table Name: {table_name}")
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
        print("="*60 + "\n")

        # Create table
        create_table_from_dataframe(conn, table_name, df, drop_if_exists=True)
        
        # Insert data
        rows_inserted = insert_dataframe_to_table(conn, table_name, df)

        print(f"✅ Successfully uploaded {rows_inserted} rows to '{table_name}'")
        print(f"🔄 Triggering AI summarization in background...\n")

        return table_name, rows_inserted, sanitized_columns

    @staticmethod
    def get_summary(user_id: str) -> dict:
        """
        Get AI summary for user's table
        
        Args:
            user_id: User ID (UUID)
            
        Returns:
            Dictionary with summary results
            
        Raises:
            Exception: If summarization fails
        """
        table_name = sanitize_table_name(user_id)
        summarizer = DatabaseSummarizer(DATABASE_URL)
        result = summarizer.generate_ai_summary(table_name)
        return result
