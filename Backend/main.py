from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Import routers
from auth_routes import router as auth_router
from data_ingestion_routes import router as data_router

# ==================== FASTAPI APP INITIALIZATION ====================

app = FastAPI(
    title="Integrated Platform API",
    description="User Management + Data Ingestion & AI Summarization",
    version="4.0.0",
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


# ==================== HEALTH CHECK ENDPOINT ====================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Integrated Platform API",
        "version": "4.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with links to all resources"""
    return {
        "message": "Welcome to Integrated Platform API",
        "version": "4.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "services": {
            "authentication": {
                "base_path": "/api/auth",
                "description": "User management with OTP verification",
                "endpoints": {
                    "register_initiate": "/api/auth/register/initiate",
                    "register_verify": "/api/auth/register/verify",
                    "signin": "/api/auth/signin",
                    "delete_user": "/api/auth/delete-user/{user_id}"
                }
            },
            "data_ingestion": {
                "base_path": "/api/data",
                "description": "File upload with automatic AI summarization",
                "endpoints": {
                    "upload_file": "/api/data/upload-file",
                    "get_summary": "/api/data/summarize/{user_id}",
                    "get_table_data": "/api/data/table-data/{user_id}",
                    "delete_table": "/api/data/table-data/{user_id}",
                    "list_tables": "/api/data/list-user-tables"
                }
            }
        }
    }


# ==================== STARTUP AND SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Print startup information"""
    print("\n" + "="*80)
    print("🚀 INTEGRATED PLATFORM API - STARTUP")
    print("="*80)
    
    print("\n📝 AUTHENTICATION MODULE (/api/auth)")
    print("  FROM: auth_routes.py → auth.py")
    print("  POST   /api/auth/register/initiate        - Start registration, send OTP")
    print("  POST   /api/auth/register/verify          - Verify OTP, create account")
    print("  GET    /api/auth/register/status/{email}  - Check registration status")
    print("  POST   /api/auth/signin                   - User login")
    print("  DELETE /api/auth/delete-user/{user_id}    - Delete user by ID")
    print("  DELETE /api/auth/delete-user-by-email/{email} - Delete user by email")
    
    print("\n📊 DATA INGESTION & AI SUMMARIZATION (/api/data)")
    print("  FROM: data_ingestion_routes.py → data_ingestion.py")
    print("  POST   /api/data/upload-file              - Upload CSV/Excel + auto-summarize")
    print("  GET    /api/data/summarize/{user_id}      - Get AI summary")
    print("  GET    /api/data/table-data/{user_id}     - Get table data & metadata")
    print("  DELETE /api/data/table-data/{user_id}     - Delete table")
    print("  GET    /api/data/list-user-tables         - List all tables")
    
    print("\n✅ SYSTEM ENDPOINTS")
    print("  GET    /health                            - Health check")
    print("  GET    /                                  - Root endpoint")
    
    print("\n📚 DOCUMENTATION")
    print("  GET    /docs                              - Swagger UI (Interactive)")
    print("  GET    /redoc                             - ReDoc (Alternative docs)")
    print("  GET    /openapi.json                      - OpenAPI JSON schema")
    
    print("\n🔗 QUICK LINKS")
    print("  http://localhost:8000/docs                - Swagger UI")
    print("  http://localhost:8000/redoc               - ReDoc")
    print("  http://localhost:8000/health              - Health Check")
    
    print("\n📁 FILE STRUCTURE")
    print("  ├── auth.py                  (Core logic)")
    print("  ├── auth_routes.py           (Routes)")
    print("  ├── data_ingestion.py        (Core logic)")
    print("  ├── data_ingestion_routes.py (Routes)")
    print("  ├── data_cleaner.py          (Utilities)")
    print("  ├── summarize.py             (Utilities)")
    print("  └── main.py                  (This file)")
    
    print("\n⚠️  REQUIREMENTS")
    print("  ✅ PostgreSQL database (NeonDB)")
    print("  ✅ LM Studio running on http://127.0.0.1:1234 (for AI summarization)")
    print("  ✅ Email configuration (.env file)")
    
    print("\n" + "="*80 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Print shutdown information"""
    print("\n" + "="*80)
    print("🛑 INTEGRATED PLATFORM API - SHUTDOWN")
    print("="*80 + "\n")
