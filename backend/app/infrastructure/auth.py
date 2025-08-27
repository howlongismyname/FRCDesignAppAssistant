"""Authentication utilities for the Design Assistant."""

import hashlib
import hmac
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus
import base64
import secrets

try:
    import jwt
except ImportError:
    jwt = None

from .config import SecurityConfig


logger = logging.getLogger(__name__)


class OnshapeAuthenticator:
    """Handles Onshape OAuth authentication."""
    
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
    
    def build_auth_headers(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        content_type: str = "application/json"
    ) -> Dict[str, str]:
        """Build OAuth authentication headers for Onshape API requests."""
        
        # Build the query string
        query_string = ""
        if query_params:
            # Sort parameters and encode them
            sorted_params = sorted(query_params.items())
            query_string = urlencode(sorted_params, quote_via=quote_plus)
        
        # Create nonce and timestamp
        nonce = self._generate_nonce()
        timestamp = str(int(time.time()))
        
        # Build base string for signature
        base_string_params = {
            "oauth_consumer_key": self.access_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_nonce": nonce,
            "oauth_version": "1.0"
        }
        
        # Add query parameters to signature parameters
        if query_params:
            base_string_params.update(query_params)
        
        # Sort all parameters for base string
        sorted_params = sorted(base_string_params.items())
        param_string = urlencode(sorted_params, quote_via=quote_plus)
        
        # Build base string
        base_string = f"{method.upper()}&{quote_plus(path)}&{quote_plus(param_string)}"
        
        # Create signature
        signing_key = f"{quote_plus(self.secret_key)}&"  # No token secret for two-legged OAuth
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode('utf-8'),
                base_string.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # Build authorization header
        auth_params = {
            "oauth_consumer_key": self.access_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_nonce": nonce,
            "oauth_version": "1.0",
            "oauth_signature": signature
        }
        
        auth_string = "OAuth " + ", ".join([
            f'{key}="{quote_plus(str(value))}"' 
            for key, value in sorted(auth_params.items())
        ])
        
        return {
            "Authorization": auth_string,
            "Content-Type": content_type,
            "Accept": "application/json"
        }
    
    def _generate_nonce(self) -> str:
        """Generate a unique nonce for the request."""
        return secrets.token_hex(16)


class ApiKeyAuth:
    """Simple API key authentication for internal API endpoints."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_key_hash = self._hash_key(api_key) if api_key else None
    
    def _hash_key(self, key: str) -> str:
        """Hash the API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def validate_key(self, provided_key: str) -> bool:
        """Validate a provided API key."""
        if not self.api_key_hash or not provided_key:
            return False
        
        provided_hash = self._hash_key(provided_key)
        return hmac.compare_digest(self.api_key_hash, provided_hash)
    
    def extract_key_from_header(self, authorization_header: str) -> Optional[str]:
        """Extract API key from Authorization header."""
        if not authorization_header:
            return None
        
        # Support both "Bearer <key>" and "ApiKey <key>" formats
        parts = authorization_header.split(" ", 1)
        if len(parts) != 2:
            return None
        
        scheme, key = parts
        if scheme.lower() in ("bearer", "apikey"):
            return key
        
        return None


class JWTAuth:
    """JWT token authentication."""
    
    def __init__(self, secret: str, algorithm: str = "HS256", expiry_hours: int = 24):
        if jwt is None:
            raise ImportError("PyJWT is required for JWT authentication")
        
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_hours = expiry_hours
    
    def create_token(self, payload: Dict[str, Any]) -> str:
        """Create a JWT token."""
        now = datetime.utcnow()
        token_payload = {
            "iat": now,
            "exp": now + timedelta(hours=self.expiry_hours),
            **payload
        }
        
        return jwt.encode(token_payload, self.secret, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def extract_token_from_header(self, authorization_header: str) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        if not authorization_header:
            return None
        
        parts = authorization_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]


class WebhookAuth:
    """Webhook signature validation."""
    
    def __init__(self, secret: str):
        self.secret = secret.encode('utf-8')
    
    def generate_signature(self, payload: bytes, timestamp: str) -> str:
        """Generate signature for webhook payload."""
        message = timestamp.encode('utf-8') + b'.' + payload
        signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        return f"sha256={signature}"
    
    def validate_signature(
        self, 
        payload: bytes, 
        timestamp: str, 
        signature: str
    ) -> bool:
        """Validate webhook signature."""
        expected_signature = self.generate_signature(payload, timestamp)
        return hmac.compare_digest(signature, expected_signature)
    
    def validate_timestamp(self, timestamp: str, tolerance_seconds: int = 300) -> bool:
        """Validate webhook timestamp is within tolerance."""
        try:
            webhook_time = int(timestamp)
            current_time = int(time.time())
            
            return abs(current_time - webhook_time) <= tolerance_seconds
        except (ValueError, TypeError):
            return False


class AuthenticationError(Exception):
    """Authentication-related error."""
    pass


class AuthorizationError(Exception):
    """Authorization-related error.""" 
    pass


class AuthManager:
    """Centralized authentication manager."""
    
    def __init__(self, security_config: SecurityConfig):
        self.security_config = security_config
        
        # Initialize authentication methods
        self.api_key_auth = None
        if security_config.api_key:
            self.api_key_auth = ApiKeyAuth(security_config.api_key)
        
        self.jwt_auth = None
        if security_config.jwt_secret:
            self.jwt_auth = JWTAuth(
                security_config.jwt_secret,
                expiry_hours=security_config.jwt_expiry_hours
            )
    
    def authenticate_request(self, authorization_header: str) -> Optional[Dict[str, Any]]:
        """Authenticate a request using available methods."""
        if not authorization_header:
            return None
        
        # Try JWT authentication first
        if self.jwt_auth:
            token = self.jwt_auth.extract_token_from_header(authorization_header)
            if token:
                payload = self.jwt_auth.validate_token(token)
                if payload:
                    return {
                        "type": "jwt",
                        "payload": payload,
                        "user_id": payload.get("sub"),
                        "permissions": payload.get("permissions", [])
                    }
        
        # Try API key authentication
        if self.api_key_auth:
            api_key = self.api_key_auth.extract_key_from_header(authorization_header)
            if api_key and self.api_key_auth.validate_key(api_key):
                return {
                    "type": "api_key",
                    "payload": {"api_key": True},
                    "permissions": ["full_access"]  # API keys get full access
                }
        
        return None
    
    def create_jwt_token(self, user_id: str, permissions: list = None) -> str:
        """Create JWT token for user."""
        if not self.jwt_auth:
            raise AuthenticationError("JWT authentication not configured")
        
        payload = {
            "sub": user_id,
            "permissions": permissions or []
        }
        
        return self.jwt_auth.create_token(payload)
    
    def check_permission(self, auth_data: Dict[str, Any], required_permission: str) -> bool:
        """Check if authenticated user has required permission."""
        if not auth_data:
            return False
        
        permissions = auth_data.get("permissions", [])
        
        # Full access overrides specific permissions
        if "full_access" in permissions:
            return True
        
        return required_permission in permissions