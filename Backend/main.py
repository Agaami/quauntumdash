from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime


# Import routers
from utils.authentication.auth_routes import router as auth_router
from utils.data_ingestion.data_ingestion_routes import router as data_router
from utils.rag_agent.agent_routes import router as sql_agent_router  # NEW


# Import session management initialization
from utils.session.session_manager import create_session_master_table



# ==================== FASTAPI APP INITIALIZATION ====================


app = FastAPI(
    title="Integrated Platform API with SQL Agent",
    description="User Management + Data Ingestion + AI Summarization + Natural Language SQL Query with Custom Session Tracking",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)



# ==================== CORS MIDDLEWARE ====================


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ==================== INCLUDE ROUTERS ====================


# Include authentication router
app.include_router(auth_router)

# Include data ingestion router
app.include_router(data_router)

# Include SQL agent router
app.include_router(sql_agent_router)  # NEW



# ==================== HEALTH CHECK ENDPOINT ====================


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Integrated Platform API",
        "version": "6.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "authentication": "enabled",
            "data_ingestion": "enabled",
            "session_management": "enabled",
            "ai_summarization": "enabled",
            "sql_agent": "enabled"  # NEW
        }
    }



@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with links to all resources"""
    return {
        "message": "Welcome to Integrated Platform API with SQL Agent",
        "version": "6.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "services": {
            "authentication": {
                "base_path": "/api/auth",
                "description": "User management with OTP verification and session tracking",
                "endpoints": {
                    "register_initiate": "/api/auth/register/initiate",
                    "register_verify": "/api/auth/register/verify",
                    "register_status": "/api/auth/register/status/{email}",
                    "signin": "/api/auth/signin",
                    "logout": "/api/auth/logout",
                    "verify_session": "/api/auth/verify-session",
                    "session_history": "/api/auth/session-history",
                    "delete_user": "/api/auth/delete-user/{user_id}",
                    "delete_user_by_email": "/api/auth/delete-user-by-email/{email}"
                }
            },
            "data_ingestion": {
                "base_path": "/api/data",
                "description": "File upload with automatic AI summarization (requires session)",
                "endpoints": {
                    "upload_file": "/api/data/upload-file",
                    "get_summary": "/api/data/summarize/{user_id}",
                    "get_table_data": "/api/data/table-data/{user_id}",
                    "delete_table": "/api/data/table-data/{user_id}",
                    "list_tables": "/api/data/list-user-tables"
                }
            },
            "sql_agent": {  # NEW
                "base_path": "/api/sql-agent",
                "description": "Natural language to SQL query generation and execution (requires session)",
                "endpoints": {
                    "natural_language_query": "/api/sql-agent/query",
                    "get_schema": "/api/sql-agent/schema"
                }
            }
        },
        "session_info": {
            "description": "Custom session management with activity tracking",
            "header_required": "X-Session-Id",
            "note": "All data ingestion and SQL agent endpoints require valid session"
        }
    }



# ==================== STARTUP AND SHUTDOWN EVENTS ====================


@app.on_event("startup")
async def startup_event():
    """Initialize application and database tables on startup"""
    print("\n" + "="*80)
    print("🚀 INTEGRATED PLATFORM API - STARTUP")
    print("="*80)
    print(f"Version: 6.0.0")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    # Initialize session management database
    print("\n🔧 INITIALIZING SESSION MANAGEMENT...")
    try:
        create_session_master_table()
        print("✅ Session management initialized successfully")
        print("   - Master session table created/verified")
        print("   - Session tracking ready")
        print("   - Activity logging enabled")
    except Exception as e:
        print(f"⚠️  Warning: Session initialization issue: {e}")
        print("   - Application will continue, but session tracking may be affected")
    
    print("\n📝 AUTHENTICATION MODULE (/api/auth)")
    print("  FROM: auth_routes.py → auth.py")
    print("  POST   /api/auth/register/initiate           - Start registration, send OTP")
    print("  POST   /api/auth/register/verify             - Verify OTP, create account + session")
    print("  GET    /api/auth/register/status/{email}     - Check registration status")
    print("  POST   /api/auth/signin                      - User login + create session")
    print("  POST   /api/auth/logout                      - Logout + invalidate session ⚡")
    print("  GET    /api/auth/verify-session              - Verify session validity ⚡")
    print("  GET    /api/auth/session-history             - Get session activity history ⚡")
    print("  DELETE /api/auth/delete-user/{user_id}       - Delete user by ID ⚡")
    print("  DELETE /api/auth/delete-user-by-email/{email} - Delete user by email ⚡")
    
    print("\n📊 DATA INGESTION & AI SUMMARIZATION (/api/data)")
    print("  FROM: data_ingestion_routes.py → data_ingestion.py")
    print("  POST   /api/data/upload-file                 - Upload CSV/Excel + auto-summarize ⚡")
    print("  GET    /api/data/summarize/{user_id}         - Get AI summary ⚡")
    print("  GET    /api/data/table-data/{user_id}        - Get table data & metadata ⚡")
    print("  DELETE /api/data/table-data/{user_id}        - Delete table ⚡")
    print("  GET    /api/data/list-user-tables            - List all tables ⚡")
    
    print("\n🤖 SQL AGENT - NATURAL LANGUAGE QUERIES (/api/sql-agent)")  # NEW
    print("  FROM: sql_agent_routes.py → sql_agent.py")
    print("  POST   /api/sql-agent/query                  - Natural language to SQL + execute ⚡")
    print("  GET    /api/sql-agent/schema                 - Get user table schema ⚡")
    
    print("\n⚡ = Requires Session (X-Session-Id header)")
    
    print("\n✅ SYSTEM ENDPOINTS")
    print("  GET    /health                               - Health check")
    print("  GET    /                                     - Root endpoint")
    
    print("\n📚 DOCUMENTATION")
    print("  GET    /docs                                 - Swagger UI (Interactive)")
    print("  GET    /redoc                                - ReDoc (Alternative docs)")
    print("  GET    /openapi.json                         - OpenAPI JSON schema")
    
    print("\n🔗 QUICK LINKS")
    print("  http://localhost:8000/docs                   - Swagger UI")
    print("  http://localhost:8000/redoc                  - ReDoc")
    print("  http://localhost:8000/health                 - Health Check")
    
    print("\n📁 FILE STRUCTURE")
    print("  ├── auth.py                     (Core authentication logic)")
    print("  ├── auth_routes.py              (Authentication routes)")
    print("  ├── data_ingestion.py           (Core data ingestion logic)")
    print("  ├── data_ingestion_routes.py    (Data ingestion routes)")
    print("  ├── sql_agent.py                (SQL generation logic)")  # NEW
    print("  ├── sql_agent_routes.py         (SQL agent routes)")  # NEW
    print("  ├── session_manager.py          (Session management core)")
    print("  ├── session_middleware.py       (Session middleware)")
    print("  ├── data_cleaner.py             (Data cleaning utilities)")
    print("  ├── summarize.py                (AI summarization utilities)")
    print("  └── main.py                     (This file)")
    
    print("\n🗄️  DATABASE CONFIGURATION")
    print("  📌 User Database: NeonDB (PostgreSQL)")
    print("     - User authentication & profiles")
    print("     - Data tables & metadata")
    print("     - SQL query execution")  # NEW
    
    print("\n  📌 Session Database: Supabase (PostgreSQL)")
    print("     - Master session table (session_master)")
    print("     - Individual session tables (session_sess_...)")
    print("     - Activity logs & audit trails")
    print("     - SQL query generation logs")  # NEW
    
    print("\n🔐 SESSION MANAGEMENT")
    print("  ✅ Custom session ID generation (cryptographically secure)")
    print("  ✅ Unique session table per login/registration")
    print("  ✅ Complete activity logging (requests, responses, timestamps)")
    print("  ✅ IP address & user agent tracking")
    print("  ✅ Session validation & expiration")
    print("  ✅ Audit trail for all operations")
    print("  ✅ SQL query generation and execution logs")  # NEW
    
    print("\n🤖 SQL AGENT FEATURES")  # NEW
    print("  ✅ Natural language to SQL conversion")
    print("  ✅ Context-aware query generation (uses data summary)")
    print("  ✅ Table schema analysis")
    print("  ✅ Query validation (SELECT only)")
    print("  ✅ Safe query execution")
    print("  ✅ Full session logging of queries")
    
    print("\n⚙️  SESSION WORKFLOW")
    print("  1️⃣  User registers/logs in")
    print("  2️⃣  System generates unique session_id (sess_...)")
    print("  3️⃣  Creates dedicated session table in Supabase")
    print("  4️⃣  User uploads data file")
    print("  5️⃣  AI generates data summary")
    print("  6️⃣  User queries data using natural language")  # NEW
    print("  7️⃣  SQL agent generates and executes SQL")  # NEW
    print("  8️⃣  All actions logged to session table")
    print("  9️⃣  Logout invalidates session")
    
    print("\n⚠️  REQUIREMENTS")
    print("  ✅ PostgreSQL database (NeonDB) - User data")
    print("  ✅ PostgreSQL database (Supabase) - Session tracking")
    print("  ✅ LM Studio running on http://127.0.0.1:1234 (AI summarization & SQL generation)")
    print("  ✅ Email configuration (.env file)")
    print("  ✅ Session database credentials in .env")
    
    print("\n📋 USAGE EXAMPLE")
    print("  1. Register:     POST /api/auth/register/initiate")
    print("  2. Verify:       POST /api/auth/register/verify")
    print("     Response:     { \"session_id\": \"sess_abc123...\" }")
    print("  3. Upload Data:  POST /api/data/upload-file (with X-Session-Id)")
    print("  4. Query Data:   POST /api/sql-agent/query")  # NEW
    print("     Body:         { \"user_query\": \"Show top 10 sales\", \"execute\": true }")  # NEW
    print("  5. Get Results:  Returns SQL + execution results")  # NEW
    print("  6. Logout:       POST /api/auth/logout (with X-Session-Id)")
    
    print("\n🎯 SQL AGENT EXAMPLE QUERIES")  # NEW
    print("  • \"Show me the top 5 rows\"")
    print("  • \"What is the average sales value?\"")
    print("  • \"Count how many records have status = 'active'\"")
    print("  • \"Find all entries where amount > 1000\"")
    print("  • \"Group by category and sum the totals\"")
    
    print("\n" + "="*80)
    print("🎉 APPLICATION READY")
    print("="*80 + "\n")



@app.on_event("shutdown")
async def shutdown_event():
    """Print shutdown information"""
    print("\n" + "="*80)
    print("🛑 INTEGRATED PLATFORM API - SHUTDOWN")
    print("="*80)
    print(f"Shutdown at: {datetime.utcnow().isoformat()}")
    print("✅ All active sessions remain in database for audit")
    print("✅ Session data preserved in Supabase")
    print("✅ SQL query logs preserved in session tables")  # NEW
    print("="*80 + "\n")
