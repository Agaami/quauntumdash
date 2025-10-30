# import psycopg2
# from psycopg2.extras import RealDictCursor
# import pandas as pd
# from fastapi import FastAPI, HTTPException, BackgroundTasks, status
# from fastapi.security import HTTPBearer
# from pydantic import BaseModel, EmailStr
# from passlib.context import CryptContext
# import uuid
# from typing import Optional, Dict
# from datetime import datetime, timedelta
# import jwt
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import random
# import string
# import threading
# import time
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Database Configuration
# CONNECTION_STRING = os.getenv("DATABASE_URL")

# # Gmail SMTP Configuration
# GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
# GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT"))

# # JWT Configuration
# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = os.getenv("ALGORITHM")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# # OTP Configuration
# OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES"))
# REGISTRATION_OTP_EXPIRY_SECONDS = int(os.getenv("REGISTRATION_OTP_EXPIRY_SECONDS"))
# OTP_LENGTH = int(os.getenv("OTP_LENGTH"))


# # Thread-Safe Cache Implementation
# class ThreadSafeCache:
#     """Thread-safe cache with automatic expiry cleanup"""
    
#     def __init__(self):
#         self._cache: Dict[str, Dict] = {}
#         self._lock = threading.RLock()  # Reentrant lock for nested calls
#         self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
#         self._cleanup_thread.start()
    
#     def set(self, key: str, value: Dict, ttl_seconds: int = 300) -> bool:
#         """Set cache item with TTL"""
#         try:
#             with self._lock:
#                 self._cache[key] = {
#                     'data': value,
#                     'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds),
#                     'created_at': datetime.utcnow()
#                 }
#                 return True
#         except Exception as e:
#             print(f"Cache set error: {e}")
#             return False
    
#     def get(self, key: str) -> Optional[Dict]:
#         """Get cache item if not expired"""
#         with self._lock:
#             if key not in self._cache:
#                 return None
            
#             item = self._cache[key]
#             if datetime.utcnow() > item['expires_at']:
#                 del self._cache[key]
#                 return None
            
#             return item['data']
    
#     def delete(self, key: str) -> bool:
#         """Delete cache item"""
#         try:
#             with self._lock:
#                 if key in self._cache:
#                     del self._cache[key]
#                     return True
#                 return False
#         except Exception as e:
#             print(f"Cache delete error: {e}")
#             return False
    
#     def exists(self, key: str) -> bool:
#         """Check if key exists and not expired"""
#         return self.get(key) is not None
    
#     def update(self, key: str, updates: Dict) -> bool:
#         """Update specific fields in cached item"""
#         try:
#             with self._lock:
#                 if key not in self._cache:
#                     return False
                
#                 item = self._cache[key]
#                 if datetime.utcnow() > item['expires_at']:
#                     del self._cache[key]
#                     return False
                
#                 item['data'].update(updates)
#                 return True
#         except Exception as e:
#             print(f"Cache update error: {e}")
#             return False
    
#     def _cleanup_expired(self):
#         """Background cleanup of expired items"""
#         while True:
#             try:
#                 time.sleep(30)  # Run every 30 seconds
#                 current_time = datetime.utcnow()
#                 with self._lock:
#                     expired_keys = [
#                         key for key, item in self._cache.items()
#                         if current_time > item['expires_at']
#                     ]
#                     for key in expired_keys:
#                         del self._cache[key]
                    
#                     if expired_keys:
#                         print(f"Cleaned up {len(expired_keys)} expired cache items")
#             except Exception as e:
#                 print(f"Cleanup error: {e}")
#                 time.sleep(60)


# # Initialize global cache
# cache = ThreadSafeCache()


# # Database Connection
# def get_db_connection():
#     """Establish connection to NeonDB PostgreSQL database"""
#     try:
#         conn = psycopg2.connect(CONNECTION_STRING)
#         return conn
#     except Exception as e:
#         print(f"DB connection error: {e}")
#         return None


# # Create User Table
# def create_user_table():
#     """Create user_details table in NeonDB"""
#     create_table_query = """
#     CREATE TABLE IF NOT EXISTS user_details (
#         user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#         name VARCHAR(100) NOT NULL,
#         email VARCHAR(255) NOT NULL UNIQUE,
#         password VARCHAR(255) NOT NULL,
#         user_type VARCHAR(50) NOT NULL,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     );
#     """
    
#     try:
#         conn = get_db_connection()
#         if conn:
#             cursor = conn.cursor()
#             cursor.execute(create_table_query)
#             cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON user_details(email);")
#             conn.commit()
#             cursor.close()
#             conn.close()
#     except Exception as e:
#         print(f"Table creation error: {e}")


# create_user_table()


# # Pydantic Models
# class UserRegistration(BaseModel):
#     name: str
#     email: EmailStr
#     password: str
#     user_type: str


# class VerifyRegistrationOTP(BaseModel):
#     email: EmailStr
#     otp_code: str


# class UserSignin(BaseModel):
#     email: EmailStr
#     password: str


# class RegistrationInitiateResponse(BaseModel):
#     status: bool
#     message: str
#     request_id: str
#     expires_in_seconds: int


# class RegistrationVerifyResponse(BaseModel):
#     status: bool
#     message: str
#     user: Optional[Dict] = None


# class DeleteUserResponse(BaseModel):
#     message: str
#     success: bool
#     deleted_user: Optional[Dict] = None


# # Password Hashing
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt


# # OTP Functions
# def generate_otp(length: int = OTP_LENGTH) -> str:
#     return ''.join(random.choices(string.digits, k=length))


# def send_otp_email(recipient_email: str, otp_code: str, purpose: str, expiry_seconds: int = None) -> bool:
#     """Send OTP via Gmail SMTP"""
#     try:
#         msg = MIMEMultipart()
#         msg['From'] = GMAIL_EMAIL
#         msg['To'] = recipient_email
        
#         expiry_display = f"{expiry_seconds} seconds" if expiry_seconds else f"{OTP_EXPIRY_MINUTES} minutes"
        
#         subjects = {
#             "registration": "🔐 Complete Your Registration - OTP Code",
#             "email_verification": "🔐 Email Verification - OTP Code",
#             "password_reset": "🔑 Password Reset - OTP Code",
#             "login_verification": "🛡️ Login Verification - OTP Code"
#         }
#         msg['Subject'] = subjects.get(purpose, "🔐 OTP Verification")
        
#         html_body = f"""
#         <html>
#             <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif;">
#                 <div style="max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
#                     <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
#                         <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 300;">🔐 OTP Verification</h1>
#                         <p style="color: #e8eaed; margin: 10px 0 0 0; font-size: 16px;">Secure access to your account</p>
#                     </div>
#                     <div style="padding: 40px 30px; background-color: white;">
#                         <h2 style="color: #333; margin: 0 0 20px 0; font-size: 24px;">Hello! 👋</h2>
#                         <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
#                             You requested a verification code for <strong>{purpose.replace('_', ' ').title()}</strong>. 
#                             Here's your secure OTP code:
#                         </p>
#                         <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
#                                     padding: 25px; text-align: center; border-radius: 15px; margin: 30px 0; 
#                                     box-shadow: 0 10px 25px rgba(240, 147, 251, 0.3);">
#                             <h1 style="color: white; letter-spacing: 8px; margin: 0; font-size: 36px; 
#                                       font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
#                                 {otp_code}
#                             </h1>
#                         </div>
#                         <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; 
#                                     padding: 20px; margin: 25px 0;">
#                             <p style="margin: 0; color: #856404; font-size: 14px; line-height: 1.5;">
#                                 <strong>⚠️ Important:</strong><br>
#                                 • This OTP expires in <strong>{expiry_display}</strong><br>
#                                 • Use this code only once<br>
#                                 • Maximum 3 verification attempts allowed
#                             </p>
#                         </div>
#                     </div>
#                     <div style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
#                         <p style="color: #6c757d; font-size: 12px; text-align: center; margin: 0;">
#                             This is an automated email from <strong>Agaami AI Labs</strong><br>
#                             Please do not reply to this email.
#                         </p>
#                     </div>
#                 </div>
#             </body>
#         </html>
#         """
        
#         msg.attach(MIMEText(html_body, 'html'))
        
#         with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#             server.starttls()
#             server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
#             server.send_message(msg)
        
#         return True
    
#     except Exception as e:
#         print(f"Email send error: {e}")
#         return False


# # Database Operations
# class UserDatabase:
#     @staticmethod
#     def email_exists(email: str) -> bool:
#         """Check if email already registered"""
#         try:
#             conn = get_db_connection()
#             if not conn:
#                 return False
            
#             cursor = conn.cursor()
#             cursor.execute("SELECT 1 FROM user_details WHERE email = %s", (email,))
#             exists = cursor.fetchone() is not None
#             cursor.close()
#             conn.close()
#             return exists
#         except Exception as e:
#             print(f"Email check error: {e}")
#             return False
    
#     @staticmethod
#     def create_user(user_data: Dict):
#         """Insert new user into database"""
#         try:
#             conn = get_db_connection()
#             if not conn:
#                 raise Exception("Database connection failed")
            
#             cursor = conn.cursor(cursor_factory=RealDictCursor)
            
#             # Double-check email doesn't exist
#             cursor.execute("SELECT email FROM user_details WHERE email = %s", (user_data['email'],))
#             if cursor.fetchone():
#                 raise Exception("Email already registered")
            
#             insert_query = """
#             INSERT INTO user_details (name, email, password, user_type) 
#             VALUES (%s, %s, %s, %s) 
#             RETURNING user_id, name, email, user_type, created_at
#             """
            
#             cursor.execute(insert_query, (
#                 user_data['name'],
#                 user_data['email'],
#                 user_data['password'],
#                 user_data['user_type']
#             ))
            
#             user_record = cursor.fetchone()
#             conn.commit()
#             cursor.close()
#             conn.close()
            
#             return dict(user_record)
        
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#                 cursor.close()
#                 conn.close()
#             raise Exception(f"User creation failed: {e}")
    
#     @staticmethod
#     def authenticate_user(email: str, password: str):
#         """Authenticate user login"""
#         try:
#             conn = get_db_connection()
#             if not conn:
#                 raise Exception("Database connection failed")
            
#             cursor = conn.cursor(cursor_factory=RealDictCursor)
#             cursor.execute(
#                 "SELECT user_id, name, email, password, user_type, created_at FROM user_details WHERE email = %s",
#                 (email,)
#             )
            
#             user_record = cursor.fetchone()
#             cursor.close()
#             conn.close()
            
#             if not user_record:
#                 return None
            
#             if not verify_password(password, user_record['password']):
#                 return None
            
#             user_data = dict(user_record)
#             del user_data['password']
#             return user_data
        
#         except Exception as e:
#             if conn:
#                 cursor.close()
#                 conn.close()
#             raise Exception(f"Authentication failed: {e}")
    
#     @staticmethod
#     def delete_user_by_id(user_id: str):
#         """Delete user by user_id"""
#         try:
#             conn = get_db_connection()
#             if not conn:
#                 raise Exception("Database connection failed")
            
#             cursor = conn.cursor(cursor_factory=RealDictCursor)
            
#             cursor.execute(
#                 "SELECT user_id, name, email, user_type, created_at FROM user_details WHERE user_id = %s",
#                 (user_id,)
#             )
            
#             user_record = cursor.fetchone()
            
#             if not user_record:
#                 cursor.close()
#                 conn.close()
#                 return None
            
#             cursor.execute("DELETE FROM user_details WHERE user_id = %s", (user_id,))
            
#             deleted_rows = cursor.rowcount
#             conn.commit()
#             cursor.close()
#             conn.close()
            
#             if deleted_rows > 0:
#                 return dict(user_record)
#             else:
#                 return None
        
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#                 cursor.close()
#                 conn.close()
#             raise Exception(f"Error deleting user: {e}")
    
#     @staticmethod
#     def delete_user_by_email(email: str):
#         """Delete user by email"""
#         try:
#             conn = get_db_connection()
#             if not conn:
#                 raise Exception("Database connection failed")
            
#             cursor = conn.cursor(cursor_factory=RealDictCursor)
            
#             cursor.execute(
#                 "SELECT user_id, name, email, user_type, created_at FROM user_details WHERE email = %s",
#                 (email,)
#             )
            
#             user_record = cursor.fetchone()
            
#             if not user_record:
#                 cursor.close()
#                 conn.close()
#                 return None
            
#             cursor.execute("DELETE FROM user_details WHERE email = %s", (email,))
            
#             deleted_rows = cursor.rowcount
#             conn.commit()
#             cursor.close()
#             conn.close()
            
#             if deleted_rows > 0:
#                 return dict(user_record)
#             else:
#                 return None
        
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#                 cursor.close()
#                 conn.close()
#             raise Exception(f"Error deleting user: {e}")


# # FastAPI Application
# app = FastAPI(
#     title="User Management API - Registration Flow",
#     description="Two-step registration: Initiate → Verify",
#     version="4.0.0"
# )


# security = HTTPBearer()


# # ==================== REGISTRATION ENDPOINTS ====================


# @app.post("/register/initiate", response_model=RegistrationInitiateResponse, status_code=status.HTTP_200_OK)
# async def initiate_registration(user_data: UserRegistration, background_tasks: BackgroundTasks):
#     """
#     Step 1: Initiate registration
#     - Validates user data
#     - Stores pending registration in cache
#     - Sends OTP email in background
#     - Returns request_id for tracking
#     """
#     try:
#         # Validate required fields
#         if not all([user_data.name, user_data.email, user_data.password, user_data.user_type]):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="All fields are mandatory: name, email, password, user_type"
#             )
        
#         # Check if email already registered
#         if UserDatabase.email_exists(user_data.email):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Email already registered"
#             )
        
#         # Check if there's already a pending registration for this email
#         existing_pending = cache.get(f"pending_registration:{user_data.email}")
#         if existing_pending:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Registration already in progress. Please verify OTP or wait for expiry."
#             )
        
#         # Generate request ID and OTP
#         request_id = str(uuid.uuid4())
#         otp_code = generate_otp()
        
#         # Hash password
#         hashed_password = hash_password(user_data.password)
        
#         # Store pending registration in cache
#         pending_data = {
#             'request_id': request_id,
#             'name': user_data.name,
#             'email': user_data.email,
#             'password': hashed_password,
#             'user_type': user_data.user_type,
#             'otp_code': otp_code,
#             'attempts': 0,
#             'created_at': datetime.utcnow().isoformat()
#         }
        
#         cache.set(
#             f"pending_registration:{user_data.email}",
#             pending_data,
#             ttl_seconds=REGISTRATION_OTP_EXPIRY_SECONDS
#         )
        
#         print("\n" + "="*60)
#         print(f"🚀 REGISTRATION INITIATED")
#         print("="*60)
#         print(f"Request ID: {request_id}")
#         print(f"Email: {user_data.email}")
#         print(f"OTP Code: {otp_code}")
#         print(f"Expires in: {REGISTRATION_OTP_EXPIRY_SECONDS} seconds")
#         print(f"Timestamp: {datetime.utcnow().isoformat()}")
#         print("="*60 + "\n")
        
#         # Send OTP email in background (non-blocking)
#         background_tasks.add_task(
#             send_otp_email,
#             user_data.email,
#             otp_code,
#             "registration",
#             REGISTRATION_OTP_EXPIRY_SECONDS
#         )
        
#         return RegistrationInitiateResponse(
#             status=True,
#             message=f"OTP sent to {user_data.email}. Please verify within {REGISTRATION_OTP_EXPIRY_SECONDS} seconds.",
#             request_id=request_id,
#             expires_in_seconds=REGISTRATION_OTP_EXPIRY_SECONDS
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Registration initiation failed: {e}"
#         )



# @app.post("/register/verify", response_model=RegistrationVerifyResponse, status_code=status.HTTP_201_CREATED)
# async def verify_registration(verification: VerifyRegistrationOTP):
#     """
#     Step 2: Verify OTP and complete registration
#     - Verifies OTP code
#     - Creates user account in database
#     - Cleans up cache
#     - Returns user details
#     """
#     try:
#         # Get pending registration from cache
#         pending_data = cache.get(f"pending_registration:{verification.email}")
        
#         if not pending_data:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No pending registration found or OTP expired. Please start registration again."
#             )
        
#         # Check attempts
#         if pending_data['attempts'] >= 3:
#             cache.delete(f"pending_registration:{verification.email}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Maximum verification attempts exceeded. Please start registration again."
#             )
        
#         # Verify OTP
#         if pending_data['otp_code'] != verification.otp_code:
#             # Increment attempts
#             cache.update(
#                 f"pending_registration:{verification.email}",
#                 {'attempts': pending_data['attempts'] + 1}
#             )
            
#             remaining_attempts = 3 - (pending_data['attempts'] + 1)
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Invalid OTP code. {remaining_attempts} attempts remaining."
#             )
        
#         # OTP is valid - create user
#         user_creation_data = {
#             'name': pending_data['name'],
#             'email': pending_data['email'],
#             'password': pending_data['password'],
#             'user_type': pending_data['user_type']
#         }
        
#         try:
#             new_user = UserDatabase.create_user(user_creation_data)
            
#             # Clean up cache
#             cache.delete(f"pending_registration:{verification.email}")
            
#             print(f"\n✅ USER SUCCESSFULLY REGISTERED: {verification.email}\n")
            
#             return RegistrationVerifyResponse(
#                 status=True,
#                 message="Registration completed successfully",
#                 user={
#                     'user_id': str(new_user['user_id']),
#                     'name': new_user['name'],
#                     'email': new_user['email'],
#                     'user_type': new_user['user_type'],
#                     'created_at': new_user['created_at'].isoformat() if new_user['created_at'] else None
#                 }
#             )
        
#         except Exception as db_error:
#             # Clean up cache even on error
#             cache.delete(f"pending_registration:{verification.email}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=str(db_error)
#             )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Verification failed: {e}"
#         )



# # ==================== SIGNIN ENDPOINT ====================


# @app.post("/signin", response_model=dict)
# async def signin_user(credentials: UserSignin):
#     """Sign in user with email and password"""
#     try:
#         user = UserDatabase.authenticate_user(credentials.email, credentials.password)
        
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid email or password",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
        
#         access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#         access_token = create_access_token(
#             data={"sub": user["email"]},
#             expires_delta=access_token_expires
#         )
        
#         return {
#             "message": "Login successful",
#             "user": user,
#             "access_token": access_token,
#             "token_type": "bearer"
#         }
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Internal server error: {e}"
#         )



# # ==================== DELETE USER ENDPOINTS ====================


# @app.delete("/delete-user/{user_id}", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
# async def delete_user_by_id(user_id: str):
#     """Delete user by user_id"""
#     try:
#         # Validate UUID format
#         try:
#             uuid.UUID(user_id)
#         except ValueError:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid user ID format. Must be a valid UUID."
#             )
        
#         deleted_user = UserDatabase.delete_user_by_id(user_id)
        
#         if not deleted_user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"User with ID {user_id} not found"
#             )
        
#         return DeleteUserResponse(
#             message=f"User {deleted_user['name']} ({deleted_user['email']}) has been successfully deleted",
#             success=True,
#             deleted_user={
#                 "user_id": str(deleted_user["user_id"]),
#                 "name": deleted_user["name"],
#                 "email": deleted_user["email"],
#                 "user_type": deleted_user["user_type"],
#                 "created_at": deleted_user["created_at"].isoformat() if deleted_user["created_at"] else None,
#                 "deleted_at": datetime.utcnow().isoformat()
#             }
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error deleting user: {e}"
#         )



# @app.delete("/delete-user-by-email/{email}", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
# async def delete_user_by_email(email: str):
#     """Delete user by email address"""
#     try:
#         # Validate email format
#         if "@" not in email or "." not in email:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid email format"
#             )
        
#         deleted_user = UserDatabase.delete_user_by_email(email)
        
#         if not deleted_user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"User with email {email} not found"
#             )
        
#         return DeleteUserResponse(
#             message=f"User {deleted_user['name']} ({deleted_user['email']}) has been successfully deleted",
#             success=True,
#             deleted_user={
#                 "user_id": str(deleted_user["user_id"]),
#                 "name": deleted_user["name"],
#                 "email": deleted_user["email"],
#                 "user_type": deleted_user["user_type"],
#                 "created_at": deleted_user["created_at"].isoformat() if deleted_user["created_at"] else None,
#                 "deleted_at": datetime.utcnow().isoformat()
#             }
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error deleting user: {e}"
#         )



# # ==================== UTILITY ENDPOINTS ====================


# @app.get("/register/status/{email}")
# async def check_registration_status(email: str):
#     """Check if there's a pending registration for an email"""
#     pending = cache.get(f"pending_registration:{email}")
    
#     if not pending:
#         return {
#             "status": "none",
#             "message": "No pending registration found"
#         }
    
#     return {
#         "status": "pending",
#         "message": "Registration pending OTP verification",
#         "request_id": pending['request_id'],
#         "attempts_remaining": 3 - pending['attempts'],
#         "created_at": pending['created_at']
#     }



# def view_all_users():
#     """View all users in the database"""
#     try:
#         conn = get_db_connection()
#         if conn:
#             df = pd.read_sql_query(
#                 "SELECT user_id, name, email, user_type, created_at FROM user_details ORDER BY created_at DESC",
#                 conn
#             )
#             conn.close()
#             return df
#     except Exception as e:
#         print(f"Error fetching users: {e}")
#         return None



# print("\n" + "="*60)
# print("🚀 User Management API - Two-Step Registration")
# print("="*60)
# print("Endpoints:")
# print("  POST   /register/initiate        - Start registration, send OTP")
# print("  POST   /register/verify          - Verify OTP, create account")
# print("  GET    /register/status/{email}  - Check registration status")
# print("  POST   /signin                   - User login")
# print("  DELETE /delete-user/{user_id}    - Delete user by ID")
# print("  DELETE /delete-user-by-email/{email} - Delete user by email")
# print("="*60 + "\n")

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import uuid
from typing import Optional, Dict
from datetime import datetime, timedelta
import jwt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import threading
import time
import os
from dotenv import load_dotenv


load_dotenv()


# ==================== CONFIGURATION ====================

CONNECTION_STRING = os.getenv("DATABASE_URL")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES"))
REGISTRATION_OTP_EXPIRY_SECONDS = int(os.getenv("REGISTRATION_OTP_EXPIRY_SECONDS"))
OTP_LENGTH = int(os.getenv("OTP_LENGTH"))


# ==================== PYDANTIC MODELS ====================

class UserRegistration(BaseModel):
    name: str
    email: EmailStr
    password: str
    user_type: str


class VerifyRegistrationOTP(BaseModel):
    email: EmailStr
    otp_code: str


class UserSignin(BaseModel):
    email: EmailStr
    password: str


class RegistrationInitiateResponse(BaseModel):
    status: bool
    message: str
    request_id: str
    expires_in_seconds: int


class RegistrationVerifyResponse(BaseModel):
    status: bool
    message: str
    user: Optional[Dict] = None


class DeleteUserResponse(BaseModel):
    message: str
    success: bool
    deleted_user: Optional[Dict] = None


# ==================== THREAD-SAFE CACHE ====================

class ThreadSafeCache:
    """Thread-safe cache with automatic expiry cleanup"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def set(self, key: str, value: Dict, ttl_seconds: int = 300) -> bool:
        """Set cache item with TTL"""
        try:
            with self._lock:
                self._cache[key] = {
                    'data': value,
                    'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds),
                    'created_at': datetime.utcnow()
                }
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cache item if not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            if datetime.utcnow() > item['expires_at']:
                del self._cache[key]
                return None
            
            return item['data']
    
    def delete(self, key: str) -> bool:
        """Delete cache item"""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and not expired"""
        return self.get(key) is not None
    
    def update(self, key: str, updates: Dict) -> bool:
        """Update specific fields in cached item"""
        try:
            with self._lock:
                if key not in self._cache:
                    return False
                
                item = self._cache[key]
                if datetime.utcnow() > item['expires_at']:
                    del self._cache[key]
                    return False
                
                item['data'].update(updates)
                return True
        except Exception as e:
            print(f"Cache update error: {e}")
            return False
    
    def _cleanup_expired(self):
        """Background cleanup of expired items"""
        while True:
            try:
                time.sleep(30)
                current_time = datetime.utcnow()
                with self._lock:
                    expired_keys = [
                        key for key, item in self._cache.items()
                        if current_time > item['expires_at']
                    ]
                    for key in expired_keys:
                        del self._cache[key]
                    
                    if expired_keys:
                        print(f"Cleaned up {len(expired_keys)} expired cache items")
            except Exception as e:
                print(f"Cleanup error: {e}")
                time.sleep(60)


cache = ThreadSafeCache()


# ==================== DATABASE OPERATIONS ====================

def get_db_connection():
    """Establish connection to PostgreSQL database"""
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        return conn
    except Exception as e:
        print(f"DB connection error: {e}")
        return None


def create_user_table():
    """Create user_details table"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS user_details (
        user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        user_type VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(create_table_query)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON user_details(email);")
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Table creation error: {e}")


create_user_table()


# ==================== PASSWORD & JWT ====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ==================== OTP FUNCTIONS ====================

def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate random OTP"""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(recipient_email: str, otp_code: str, purpose: str, expiry_seconds: int = None) -> bool:
    """Send OTP via Gmail SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = recipient_email
        
        expiry_display = f"{expiry_seconds} seconds" if expiry_seconds else f"{OTP_EXPIRY_MINUTES} minutes"
        
        subjects = {
            "registration": "🔐 Complete Your Registration - OTP Code",
            "email_verification": "🔐 Email Verification - OTP Code",
            "password_reset": "🔑 Password Reset - OTP Code",
            "login_verification": "🛡️ Login Verification - OTP Code"
        }
        msg['Subject'] = subjects.get(purpose, "🔐 OTP Verification")
        
        html_body = f"""
        <html>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 300;">🔐 OTP Verification</h1>
                        <p style="color: #e8eaed; margin: 10px 0 0 0; font-size: 16px;">Secure access to your account</p>
                    </div>
                    <div style="padding: 40px 30px; background-color: white;">
                        <h2 style="color: #333; margin: 0 0 20px 0; font-size: 24px;">Hello! 👋</h2>
                        <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                            You requested a verification code for <strong>{purpose.replace('_', ' ').title()}</strong>. 
                            Here's your secure OTP code:
                        </p>
                        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                                    padding: 25px; text-align: center; border-radius: 15px; margin: 30px 0; 
                                    box-shadow: 0 10px 25px rgba(240, 147, 251, 0.3);">
                            <h1 style="color: white; letter-spacing: 8px; margin: 0; font-size: 36px; 
                                      font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                                {otp_code}
                            </h1>
                        </div>
                        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; 
                                    padding: 20px; margin: 25px 0;">
                            <p style="margin: 0; color: #856404; font-size: 14px; line-height: 1.5;">
                                <strong>⚠️ Important:</strong><br>
                                • This OTP expires in <strong>{expiry_display}</strong><br>
                                • Use this code only once<br>
                                • Maximum 3 verification attempts allowed
                            </p>
                        </div>
                    </div>
                    <div style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                        <p style="color: #6c757d; font-size: 12px; text-align: center; margin: 0;">
                            This is an automated email from <strong>Agaami AI Labs</strong><br>
                            Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"Email send error: {e}")
        return False


# ==================== USER DATABASE CLASS ====================

class UserDatabase:
    @staticmethod
    def email_exists(email: str) -> bool:
        """Check if email already registered"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_details WHERE email = %s", (email,))
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return exists
        except Exception as e:
            print(f"Email check error: {e}")
            return False
    
    @staticmethod
    def create_user(user_data: Dict):
        """Insert new user into database"""
        try:
            conn = get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT email FROM user_details WHERE email = %s", (user_data['email'],))
            if cursor.fetchone():
                raise Exception("Email already registered")
            
            insert_query = """
            INSERT INTO user_details (name, email, password, user_type) 
            VALUES (%s, %s, %s, %s) 
            RETURNING user_id, name, email, user_type, created_at
            """
            
            cursor.execute(insert_query, (
                user_data['name'],
                user_data['email'],
                user_data['password'],
                user_data['user_type']
            ))
            
            user_record = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            return dict(user_record)
        
        except Exception as e:
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            raise Exception(f"User creation failed: {e}")
    
    @staticmethod
    def authenticate_user(email: str, password: str):
        """Authenticate user login"""
        try:
            conn = get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT user_id, name, email, password, user_type, created_at FROM user_details WHERE email = %s",
                (email,)
            )
            
            user_record = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not user_record:
                return None
            
            if not verify_password(password, user_record['password']):
                return None
            
            user_data = dict(user_record)
            del user_data['password']
            return user_data
        
        except Exception as e:
            if conn:
                cursor.close()
                conn.close()
            raise Exception(f"Authentication failed: {e}")
    
    @staticmethod
    def delete_user_by_id(user_id: str):
        """Delete user by user_id"""
        try:
            conn = get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT user_id, name, email, user_type, created_at FROM user_details WHERE user_id = %s",
                (user_id,)
            )
            
            user_record = cursor.fetchone()
            
            if not user_record:
                cursor.close()
                conn.close()
                return None
            
            cursor.execute("DELETE FROM user_details WHERE user_id = %s", (user_id,))
            
            deleted_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            if deleted_rows > 0:
                return dict(user_record)
            else:
                return None
        
        except Exception as e:
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            raise Exception(f"Error deleting user: {e}")
    
    @staticmethod
    def delete_user_by_email(email: str):
        """Delete user by email"""
        try:
            conn = get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT user_id, name, email, user_type, created_at FROM user_details WHERE email = %s",
                (email,)
            )
            
            user_record = cursor.fetchone()
            
            if not user_record:
                cursor.close()
                conn.close()
                return None
            
            cursor.execute("DELETE FROM user_details WHERE email = %s", (email,))
            
            deleted_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            if deleted_rows > 0:
                return dict(user_record)
            else:
                return None
        
        except Exception as e:
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            raise Exception(f"Error deleting user: {e}")


def view_all_users():
    """View all users in the database"""
    try:
        conn = get_db_connection()
        if conn:
            df = pd.read_sql_query(
                "SELECT user_id, name, email, user_type, created_at FROM user_details ORDER BY created_at DESC",
                conn
            )
            conn.close()
            return df
    except Exception as e:
        print(f"Error fetching users: {e}")
        return None
