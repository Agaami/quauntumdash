from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Request, Depends
from datetime import datetime, timedelta
import uuid
import json


from utils.authentication.auth import (
    UserRegistration,
    VerifyRegistrationOTP,
    UserSignin,
    RegistrationInitiateResponse,
    RegistrationVerifyResponse,
    DeleteUserResponse,
    UserDatabase,
    cache,
    hash_password,
    create_access_token,
    generate_otp,
    send_otp_email,
    REGISTRATION_OTP_EXPIRY_SECONDS,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Import session management utilities
from utils.session.session_manager import (
    create_new_session, 
    log_session_activity,
    verify_session,
    invalidate_session,
    get_session_history
)
from utils.session.session_middleware import get_session_from_request


# Create router with prefix and tags
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}}
)


# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Try to get real IP from headers (for proxy/load balancer scenarios)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client host
    if request.client:
        return request.client.host
    
    return "unknown"


# ==================== REGISTRATION ENDPOINTS ====================


@router.post("/register/initiate", response_model=RegistrationInitiateResponse, status_code=status.HTTP_200_OK)
async def initiate_registration(user_data: UserRegistration, request: Request, background_tasks: BackgroundTasks):
    """
    Step 1: Initiate registration
    - Validates user data
    - Stores pending registration in cache
    - Sends OTP email in background
    - Returns request_id for tracking
    """
    try:
        # Validate required fields
        if not all([user_data.name, user_data.email, user_data.password, user_data.user_type]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are mandatory: name, email, password, user_type"
            )
        
        # Check if email already registered
        if UserDatabase.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if there's already a pending registration
        existing_pending = cache.get(f"pending_registration:{user_data.email}")
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration already in progress. Please verify OTP or wait for expiry."
            )
        
        # Generate request ID and OTP
        request_id = str(uuid.uuid4())
        otp_code = generate_otp()
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Store pending registration in cache
        pending_data = {
            'request_id': request_id,
            'name': user_data.name,
            'email': user_data.email,
            'password': hashed_password,
            'user_type': user_data.user_type,
            'otp_code': otp_code,
            'attempts': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        
        cache.set(
            f"pending_registration:{user_data.email}",
            pending_data,
            ttl_seconds=REGISTRATION_OTP_EXPIRY_SECONDS
        )
        
        print("\n" + "="*60)
        print(f"🚀 REGISTRATION INITIATED")
        print("="*60)
        print(f"Request ID: {request_id}")
        print(f"Email: {user_data.email}")
        print(f"OTP Code: {otp_code}")
        print(f"Expires in: {REGISTRATION_OTP_EXPIRY_SECONDS} seconds")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("="*60 + "\n")
        
        # Send OTP email in background
        background_tasks.add_task(
            send_otp_email,
            user_data.email,
            otp_code,
            "registration",
            REGISTRATION_OTP_EXPIRY_SECONDS
        )
        
        return RegistrationInitiateResponse(
            status=True,
            message=f"OTP sent to {user_data.email}. Please verify within {REGISTRATION_OTP_EXPIRY_SECONDS} seconds.",
            request_id=request_id,
            expires_in_seconds=REGISTRATION_OTP_EXPIRY_SECONDS
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration initiation failed: {e}"
        )



@router.post("/register/verify", response_model=dict, status_code=status.HTTP_201_CREATED)
async def verify_registration(verification: VerifyRegistrationOTP, request: Request):
    """
    Step 2: Verify OTP and complete registration
    - Verifies OTP code
    - Creates user account in database
    - Creates session with unique session_id
    - Logs registration action to session table
    - Returns user details and session_id
    """
    try:
        # Get pending registration from cache
        pending_data = cache.get(f"pending_registration:{verification.email}")
        
        if not pending_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending registration found or OTP expired. Please start registration again."
            )
        
        # Check attempts
        if pending_data['attempts'] >= 3:
            cache.delete(f"pending_registration:{verification.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded. Please start registration again."
            )
        
        # Verify OTP
        if pending_data['otp_code'] != verification.otp_code:
            # Increment attempts
            cache.update(
                f"pending_registration:{verification.email}",
                {'attempts': pending_data['attempts'] + 1}
            )
            
            remaining_attempts = 3 - (pending_data['attempts'] + 1)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP code. {remaining_attempts} attempts remaining."
            )
        
        # OTP is valid - create user
        user_creation_data = {
            'name': pending_data['name'],
            'email': pending_data['email'],
            'password': pending_data['password'],
            'user_type': pending_data['user_type']
        }
        
        try:
            new_user = UserDatabase.create_user(user_creation_data)
            
            # Clean up cache
            cache.delete(f"pending_registration:{verification.email}")
            
            # Get client information
            client_ip = get_client_ip(request)
            user_agent = request.headers.get('user-agent', 'unknown')
            
            # CREATE SESSION
            session_data = create_new_session(
                user_id=str(new_user['user_id']),
                email=new_user['email'],
                session_type="registration",
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            # LOG REGISTRATION ACTION TO SESSION TABLE
            log_session_activity(
                session_id=session_data["session_id"],
                endpoint="/api/auth/register/verify",
                method="POST",
                request_path=str(request.url),
                request_body=json.dumps({"email": verification.email, "otp_verified": True}),
                response_status=201,
                response_body=json.dumps({
                    "message": "Registration completed successfully",
                    "user_id": str(new_user['user_id'])
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                additional_info={
                    "action": "user_registration_completed",
                    "user_type": new_user['user_type'],
                    "registration_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            print(f"\n✅ USER SUCCESSFULLY REGISTERED: {verification.email}")
            print(f"✅ SESSION CREATED: {session_data['session_id']}")
            print(f"✅ SESSION TABLE: {session_data['table_name']}\n")
            
            return {
                "status": True,
                "message": "Registration completed successfully",
                "user": {
                    'user_id': str(new_user['user_id']),
                    'name': new_user['name'],
                    'email': new_user['email'],
                    'user_type': new_user['user_type'],
                    'created_at': new_user['created_at'].isoformat() if new_user['created_at'] else None
                },
                "session_id": session_data["session_id"],
                "session_table": session_data["table_name"]
            }
        
        except Exception as db_error:
            # Clean up cache even on error
            cache.delete(f"pending_registration:{verification.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(db_error)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {e}"
        )



@router.get("/register/status/{email}")
async def check_registration_status(email: str):
    """Check if there's a pending registration for an email"""
    pending = cache.get(f"pending_registration:{email}")
    
    if not pending:
        return {
            "status": "none",
            "message": "No pending registration found"
        }
    
    return {
        "status": "pending",
        "message": "Registration pending OTP verification",
        "request_id": pending['request_id'],
        "attempts_remaining": 3 - pending['attempts'],
        "created_at": pending['created_at']
    }



# ==================== SIGNIN ENDPOINT ====================


@router.post("/signin", response_model=dict)
async def signin_user(credentials: UserSignin, request: Request):
    """
    Sign in user with email and password
    - Authenticates user credentials
    - Creates new session with unique session_id
    - Logs login action to session table
    - Returns user details and session_id
    """
    try:
        user = UserDatabase.authenticate_user(credentials.email, credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get client information
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # CREATE SESSION
        session_data = create_new_session(
            user_id=str(user['user_id']),
            email=user['email'],
            session_type="login",
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # LOG LOGIN ACTION TO SESSION TABLE
        log_session_activity(
            session_id=session_data["session_id"],
            endpoint="/api/auth/signin",
            method="POST",
            request_path=str(request.url),
            request_body=json.dumps({"email": credentials.email}),
            response_status=200,
            response_body=json.dumps({
                "message": "Login successful",
                "user_id": str(user['user_id'])
            }),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "user_login",
                "user_type": user['user_type'],
                "login_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        print(f"\n✅ USER LOGGED IN: {credentials.email}")
        print(f"✅ SESSION CREATED: {session_data['session_id']}")
        print(f"✅ SESSION TABLE: {session_data['table_name']}\n")
        
        return {
            "message": "Login successful",
            "user": user,
            "session_id": session_data["session_id"],
            "session_table": session_data["table_name"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        )



# ==================== SESSION MANAGEMENT ENDPOINTS ====================


@router.post("/logout")
async def logout_user(request: Request, session_data: dict = Depends(get_session_from_request)):
    """
    Logout user and invalidate session
    - Logs logout action to session table
    - Marks session as inactive
    """
    try:
        session_id = request.state.session_id
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # Log logout action
        log_session_activity(
            session_id=session_id,
            endpoint="/api/auth/logout",
            method="POST",
            request_path=str(request.url),
            request_body=None,
            response_status=200,
            response_body=json.dumps({"message": "Logout successful"}),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "user_logout",
                "logout_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Invalidate session
        invalidate_session(session_id)
        
        print(f"\n✅ USER LOGGED OUT")
        print(f"✅ SESSION INVALIDATED: {session_id}\n")
        
        return {
            "message": "Logout successful",
            "session_id": session_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {e}"
        )



@router.get("/session-history")
async def get_user_session_history(
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Get activity history for current session
    - Returns all logged actions for the session
    """
    try:
        session_id = request.state.session_id
        history = get_session_history(session_id)
        
        return {
            "session_id": session_id,
            "user_id": session_data["user_id"],
            "email": session_data["email"],
            "total_activities": len(history),
            "session_created_at": session_data["created_at"],
            "last_activity": session_data["last_activity"],
            "history": history
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session history: {e}"
        )



@router.get("/verify-session")
async def verify_user_session(
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Verify if current session is valid
    - Returns session information
    """
    return {
        "status": "valid",
        "message": "Session is active and valid",
        "session_data": {
            "session_id": session_data["session_id"],
            "user_id": session_data["user_id"],
            "email": session_data["email"],
            "session_type": session_data["session_type"],
            "created_at": str(session_data["created_at"]),
            "last_activity": str(session_data["last_activity"]),
            "is_active": session_data["is_active"]
        }
    }



# ==================== DELETE USER ENDPOINTS ====================


@router.delete("/delete-user/{user_id}", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
async def delete_user_by_id(
    user_id: str, 
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Delete user by user_id (requires active session)
    - Logs deletion action to session table
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Must be a valid UUID."
            )
        
        deleted_user = UserDatabase.delete_user_by_id(user_id)
        
        if not deleted_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Log deletion action
        session_id = request.state.session_id
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')
        
        log_session_activity(
            session_id=session_id,
            endpoint=f"/api/auth/delete-user/{user_id}",
            method="DELETE",
            request_path=str(request.url),
            request_body=None,
            response_status=200,
            response_body=json.dumps({
                "deleted_user_id": user_id,
                "deleted_user_email": deleted_user['email']
            }),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "user_deletion",
                "deleted_user_name": deleted_user['name'],
                "deletion_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return DeleteUserResponse(
            message=f"User {deleted_user['name']} ({deleted_user['email']}) has been successfully deleted",
            success=True,
            deleted_user={
                "user_id": str(deleted_user["user_id"]),
                "name": deleted_user["name"],
                "email": deleted_user["email"],
                "user_type": deleted_user["user_type"],
                "created_at": deleted_user["created_at"].isoformat() if deleted_user["created_at"] else None,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {e}"
        )



@router.delete("/delete-user-by-email/{email}", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
async def delete_user_by_email(
    email: str,
    request: Request,
    session_data: dict = Depends(get_session_from_request)
):
    """
    Delete user by email address (requires active session)
    - Logs deletion action to session table
    """
    try:
        # Validate email format
        if "@" not in email or "." not in email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        deleted_user = UserDatabase.delete_user_by_email(email)
        
        if not deleted_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {email} not found"
            )
        
        # Log deletion action
        session_id = request.state.session_id
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')
        
        log_session_activity(
            session_id=session_id,
            endpoint=f"/api/auth/delete-user-by-email/{email}",
            method="DELETE",
            request_path=str(request.url),
            request_body=None,
            response_status=200,
            response_body=json.dumps({
                "deleted_user_id": str(deleted_user["user_id"]),
                "deleted_user_email": email
            }),
            ip_address=client_ip,
            user_agent=user_agent,
            additional_info={
                "action": "user_deletion_by_email",
                "deleted_user_name": deleted_user['name'],
                "deletion_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return DeleteUserResponse(
            message=f"User {deleted_user['name']} ({deleted_user['email']}) has been successfully deleted",
            success=True,
            deleted_user={
                "user_id": str(deleted_user["user_id"]),
                "name": deleted_user["name"],
                "email": deleted_user["email"],
                "user_type": deleted_user["user_type"],
                "created_at": deleted_user["created_at"].isoformat() if deleted_user["created_at"] else None,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {e}"
        )
