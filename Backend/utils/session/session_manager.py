import secrets
import string
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from datetime import datetime
from typing import Optional, Dict
import os


# Database configuration - Use connection string from environment
# Supabase pooler URL for better connection handling
DATABASE_URL = os.getenv(
    "POSTGRES_URL", 
    "postgres://postgres.txfvbvtrqmvwpqjsjnxx:IeNr4DjZfNqa8RhY@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
)


def generate_session_id(length: int = 32) -> str:
    """Generate cryptographically secure random session ID"""
    # Use secrets module for cryptographic strength
    alphabet = string.ascii_letters + string.digits
    session_id = ''.join(secrets.choice(alphabet) for _ in range(length))
    return session_id


def get_db_connection():
    """Create database connection using connection string"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        print(f"Note: Make sure Supabase project is active and credentials are correct")
        raise


def create_session_table(session_id: str):
    """Create a new table for the session to track all activities"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use session_id directly as table name
        table_name = session_id
        
        print(f"🔧 Creating session table: {table_name}")
        
        # Create table using sql.Identifier for proper quoting
        create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {} (
            id SERIAL PRIMARY KEY,
            action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            endpoint VARCHAR(500),
            method VARCHAR(10),
            request_path VARCHAR(500),
            request_body TEXT,
            response_status INTEGER,
            response_body TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            additional_info JSONB
        )
        """).format(sql.Identifier(table_name))
        
        cursor.execute(create_table_query)
        conn.commit()
        
        print(f"✅ Created session table: {table_name}")
        
        cursor.close()
        return table_name
        
    except Exception as e:
        print(f"❌ Error creating session table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def create_session_master_table():
    """Create master table to track all sessions"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        create_master_query = """
        CREATE TABLE IF NOT EXISTS session_master (
            session_id VARCHAR(100) PRIMARY KEY,
            user_id VARCHAR(100),
            email VARCHAR(255),
            session_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            ip_address VARCHAR(45),
            user_agent TEXT,
            session_table_name VARCHAR(200)
        );
        """
        
        cursor.execute(create_master_query)
        conn.commit()
        
        cursor.close()
        print("✅ Session master table ready")
        
    except Exception as e:
        print(f"❌ Error creating session master table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def create_new_session(
    user_id: str, 
    email: str, 
    session_type: str,
    ip_address: str = None,
    user_agent: str = None
) -> Dict[str, str]:
    """Create a new session for user"""
    conn = None
    try:
        # Generate unique session ID
        session_id = generate_session_id()
        
        print(f"\n{'='*60}")
        print(f"🔐 CREATING NEW SESSION")
        print(f"{'='*60}")
        print(f"Session ID: {session_id}")
        print(f"User ID: {user_id}")
        print(f"Email: {email}")
        print(f"Type: {session_type}")
        print(f"{'='*60}\n")
        
        # Create session-specific table (table name = session_id)
        table_name = create_session_table(session_id)
        
        # Insert into master session table
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO session_master 
        (session_id, user_id, email, session_type, ip_address, user_agent, session_table_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            session_id, user_id, email, session_type, 
            ip_address, user_agent, table_name
        ))
        
        conn.commit()
        cursor.close()
        
        print(f"✅ Session created successfully!")
        print(f"   Session ID: {session_id}")
        print(f"   Table: {table_name}\n")
        
        return {
            "session_id": session_id,
            "table_name": table_name,
            "user_id": user_id,
            "email": email
        }
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def log_session_activity(
    session_id: str,
    endpoint: str,
    method: str,
    request_path: str,
    request_body: str = None,
    response_status: int = None,
    response_body: str = None,
    ip_address: str = None,
    user_agent: str = None,
    additional_info: dict = None
):
    """Log activity for a session"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get session table name from master
        cursor.execute(
            "SELECT session_table_name FROM session_master WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            print(f"⚠️  Session not found: {session_id}")
            cursor.close()
            return
        
        table_name = result[0]
        
        # Insert activity log using sql.Identifier for proper quoting
        insert_query = sql.SQL("""
        INSERT INTO {} 
        (endpoint, method, request_path, request_body, response_status, 
         response_body, ip_address, user_agent, additional_info)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(table_name))
        
        cursor.execute(insert_query, (
            endpoint, method, request_path, request_body,
            response_status, response_body, ip_address, 
            user_agent, psycopg2.extras.Json(additional_info) if additional_info else None
        ))
        
        # Update last activity in master table
        cursor.execute(
            "UPDATE session_master SET last_activity = CURRENT_TIMESTAMP WHERE session_id = %s",
            (session_id,)
        )
        
        conn.commit()
        cursor.close()
        
    except Exception as e:
        print(f"⚠️  Error logging session activity: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def verify_session(session_id: str) -> Optional[Dict]:
    """Verify if session is valid and active"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT session_id, user_id, email, session_type, 
                   created_at, last_activity, is_active, session_table_name
            FROM session_master 
            WHERE session_id = %s AND is_active = TRUE
            """,
            (session_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"❌ Error verifying session: {e}")
        return None
    finally:
        if conn:
            conn.close()


def invalidate_session(session_id: str):
    """Mark session as inactive"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE session_master SET is_active = FALSE WHERE session_id = %s",
            (session_id,)
        )
        
        conn.commit()
        cursor.close()
        
        print(f"✅ Session invalidated: {session_id}")
        
    except Exception as e:
        print(f"❌ Error invalidating session: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def get_session_history(session_id: str) -> list:
    """Get all activity logs for a session"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get table name
        cursor.execute(
            "SELECT session_table_name FROM session_master WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            return []
        
        table_name = result['session_table_name']
        
        # Get all logs using sql.Identifier for proper quoting
        query = sql.SQL("SELECT * FROM {} ORDER BY action_timestamp DESC").format(
            sql.Identifier(table_name)
        )
        cursor.execute(query)
        logs = cursor.fetchall()
        
        cursor.close()
        
        # Convert datetime objects to ISO format strings
        formatted_logs = []
        for log in logs:
            log_dict = dict(log)
            if 'action_timestamp' in log_dict and isinstance(log_dict['action_timestamp'], datetime):
                log_dict['action_timestamp'] = log_dict['action_timestamp'].isoformat()
            formatted_logs.append(log_dict)
        
        return formatted_logs
        
    except Exception as e:
        print(f"❌ Error fetching session history: {e}")
        return []
    finally:
        if conn:
            conn.close()


# Initialize session master table on module import
# Wrapped in try-except to allow app to start even if DB is unavailable
try:
    create_session_master_table()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize session master table: {e}")
    print(f"   Session management will be unavailable until database is accessible")
