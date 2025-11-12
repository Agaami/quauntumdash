from fastapi import Request, HTTPException, Header
from typing import Optional
from .session_manager import verify_session, log_session_activity
import json


async def get_session_from_request(
    request: Request,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    """Extract and verify session from request headers"""
    
    # Try to get session ID from header
    session_id = x_session_id
    
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Session ID required. Please login or register first."
        )
    
    # Verify session
    session_data = verify_session(session_id)
    
    if not session_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again."
        )
    
    # Attach session data to request state
    request.state.session = session_data
    request.state.session_id = session_id
    
    return session_data


async def log_request_to_session(
    request: Request,
    response_status: int = None,
    response_body: str = None
):
    """Log request to session table"""
    
    if not hasattr(request.state, 'session_id'):
        return
    
    try:
        # Get request body if available
        try:
            body = await request.body()
            request_body = body.decode('utf-8') if body else None
        except:
            request_body = None
        
        # Get client info
        client_host = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', None)
        
        # Log to session
        log_session_activity(
            session_id=request.state.session_id,
            endpoint=str(request.url.path),
            method=request.method,
            request_path=str(request.url),
            request_body=request_body,
            response_status=response_status,
            response_body=response_body,
            ip_address=client_host,
            user_agent=user_agent,
            additional_info={
                "headers": dict(request.headers),
                "query_params": dict(request.query_params)
            }
        )
        
    except Exception as e:
        print(f"Error logging request to session: {e}")
