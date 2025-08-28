"""Onshape API client adapter."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from decimal import Decimal
from urllib.parse import urlparse

from ..domain.bom import OnshapeReference
from ..domain.errors import OnshapeApiError, RateLimitError, AuthenticationError
from ..application.services import OnshapeApiPort


logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for API calls."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call_allowed(self) -> bool:
        """Check if call is allowed based on circuit breaker state."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class OnshapeClientAdapter:
    """Adapter for Onshape API operations."""
    
    def __init__(
        self,
        base_url: str = "https://cad.onshape.com",
        access_key: str = "",
        secret_key: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.access_key = access_key
        self.secret_key = secret_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay
        
        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker()
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        # Rate limiting state
        self.last_request_time = None
        self.min_request_interval = 0.1  # 100ms between requests
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get_bom_data(
        self, 
        onshape_ref: OnshapeReference,
        configuration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch BOM data from Onshape API."""
        
        # Build API path
        path = f"/api/v6/assemblies/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/bom"
        
        params = {}
        if configuration_id:
            params["configuration"] = configuration_id
        
        try:
            response = await self._make_request("GET", path, params=params)
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get BOM data for {onshape_ref.document_id}: {e}")
            raise OnshapeApiError(f"Failed to fetch BOM data: {e}") from e
    
    async def get_mass_properties(
        self,
        onshape_ref: OnshapeReference
    ) -> Dict[str, Any]:
        """Get mass properties for parts."""
        
        # For parts, we need to use the parts API endpoint
        if onshape_ref.part_id:
            path = f"/api/v6/parts/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/partid/{onshape_ref.part_id}/massproperties"
        else:
            # For assemblies, use assembly mass properties
            path = f"/api/v6/assemblies/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/massproperties"
        
        try:
            response = await self._make_request("GET", path)
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get mass properties for {onshape_ref.part_id or onshape_ref.element_id}: {e}")
            raise OnshapeApiError(f"Failed to fetch mass properties: {e}") from e
    
    async def generate_thumbnail(
        self,
        onshape_ref: OnshapeReference,
        size: str = "300x300",
        view_angle: str = "iso"
    ) -> Dict[str, Any]:
        """Generate thumbnail for a part."""
        
        if not onshape_ref.part_id:
            raise OnshapeApiError("Part ID required for thumbnail generation")
        
        path = f"/api/v6/thumbnails/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/partid/{onshape_ref.part_id}"
        
        params = {
            "sz": size,
            "t": view_angle
        }
        
        try:
            response = await self._make_request("GET", path, params=params)
            
            # Onshape thumbnails are typically PNG images
            thumbnail_data = response.content
            
            return {
                "data": thumbnail_data,
                "metadata": {
                    "size": size,
                    "view_angle": view_angle,
                    "content_type": response.headers.get("content-type", "image/png"),
                    "content_length": len(thumbnail_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {onshape_ref.part_id}: {e}")
            raise OnshapeApiError(f"Failed to generate thumbnail: {e}") from e
    
    async def update_metadata(
        self,
        onshape_ref: OnshapeReference,
        properties: Dict[str, Any]
    ) -> bool:
        """Update metadata properties for a part."""
        
        if not onshape_ref.part_id:
            raise OnshapeApiError("Part ID required for metadata update")
        
        path = f"/api/v6/metadata/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/p/{onshape_ref.part_id}"
        
        # Onshape metadata format
        payload = {
            "properties": [
                {
                    "name": key,
                    "value": str(value) if value is not None else "",
                    "valueType": self._get_property_type(value)
                }
                for key, value in properties.items()
            ]
        }
        
        try:
            response = await self._make_request("POST", path, json=payload)
            return response.status_code in (200, 201, 204)
            
        except Exception as e:
            logger.error(f"Failed to update metadata for {onshape_ref.part_id}: {e}")
            raise OnshapeApiError(f"Failed to update metadata: {e}") from e
    
    async def export_files(
        self,
        onshape_ref: OnshapeReference,
        formats: List[str]
    ) -> List[Dict[str, Any]]:
        """Export files in specified formats."""
        
        exported_files = []
        
        for format_name in formats:
            try:
                file_data = await self._export_single_format(onshape_ref, format_name)
                exported_files.append(file_data)
                
                # Brief pause between exports to respect rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to export {format_name} for {onshape_ref.element_id}: {e}")
                # Continue with other formats rather than failing completely
        
        return exported_files
    
    async def _export_single_format(
        self,
        onshape_ref: OnshapeReference,
        format_name: str
    ) -> Dict[str, Any]:
        """Export a single file format."""
        
        # Map format names to Onshape API formats
        format_mapping = {
            "step": "STEP",
            "iges": "IGES", 
            "stl": "STL",
            "parasolid": "PARASOLID",
            "pdf": "PDF"
        }
        
        api_format = format_mapping.get(format_name.lower(), format_name.upper())
        
        # Determine if this is a part studio or assembly export
        if onshape_ref.part_id:
            # Part studio export
            path = f"/api/v6/partstudios/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/export"
            payload = {
                "format": api_format,
                "partIds": [onshape_ref.part_id]
            }
        else:
            # Assembly export
            path = f"/api/v6/assemblies/d/{onshape_ref.document_id}/{onshape_ref.wvm_type}/{onshape_ref.wvm_id}/e/{onshape_ref.element_id}/export"
            payload = {
                "format": api_format
            }
        
        # Start export
        response = await self._make_request("POST", path, json=payload)
        export_data = response.json()
        
        # Check if we got a direct download or need to poll for completion
        if "href" in export_data:
            # Direct download link
            download_url = export_data["href"]
            
            # Validate download URL for security
            parsed_url = urlparse(download_url)
            if parsed_url.scheme != 'https':
                raise OnshapeApiError("Download URL must use HTTPS")
            
            # Ensure hostname matches expected Onshape domains
            allowed_domains = ['cad.onshape.com', 'onshape.com', 'onshape-public.s3.amazonaws.com']
            if not any(parsed_url.hostname.endswith(domain) for domain in allowed_domains if parsed_url.hostname):
                logger.error(f"Blocked download from untrusted domain: {parsed_url.hostname}")
                raise OnshapeApiError(f"Download from untrusted domain blocked: {parsed_url.hostname}")
            
            file_response = await self._make_request("GET", download_url, use_auth=False)
            
            return {
                "format": format_name,
                "filename": f"export.{format_name.lower()}",
                "data": file_response.content,
                "size_bytes": len(file_response.content),
                "content_type": file_response.headers.get("content-type", "application/octet-stream")
            }
        else:
            # Need to poll for completion (not implemented for now)
            raise OnshapeApiError(f"Export polling not implemented for format {format_name}")
    
    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        use_auth: bool = True
    ) -> httpx.Response:
        """Make authenticated request to Onshape API with retry and circuit breaker."""
        
        if not self.circuit_breaker.call_allowed():
            raise RateLimitError("Circuit breaker is open")
        
        url = f"{self.base_url}{path}"
        
        # Rate limiting - simple time-based approach
        if self.last_request_time:
            elapsed = datetime.now() - self.last_request_time
            if elapsed.total_seconds() < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed.total_seconds()
                await asyncio.sleep(sleep_time)
        
        headers = {}
        if use_auth:
            headers.update(self._build_auth_headers(method, path, params))
        
        # Retry loop with exponential backoff
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.last_request_time = datetime.now()
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=headers
                )
                
                # Handle various response codes
                if response.status_code == 401:
                    self.circuit_breaker.record_failure()
                    raise AuthenticationError("Invalid Onshape credentials")
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("retry-after", self.retry_delay))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    # Server error - might be transient
                    if attempt < self.max_retries:
                        wait_time = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)  # Capped exponential backoff
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.circuit_breaker.record_failure()
                        raise OnshapeApiError(f"Server error: {response.status_code}")
                elif response.status_code >= 400:
                    self.circuit_breaker.record_failure()
                    raise OnshapeApiError(f"API error {response.status_code}: {response.text}")
                
                # Success
                self.circuit_breaker.record_success()
                return response
                
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All retries exhausted
        self.circuit_breaker.record_failure()
        raise OnshapeApiError(f"Request failed after {self.max_retries} retries") from last_exception
    
    def _build_auth_headers(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Build authentication headers for Onshape API."""
        # TODO: Implement OAuth or API key authentication
        # For now, placeholder implementation
        return {
            "Authorization": f"Bearer {self.access_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_property_type(self, value: Any) -> str:
        """Get Onshape property type for a value."""
        if isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, (int, float, Decimal)):
            return "DOUBLE"
        elif isinstance(value, datetime):
            return "DATE"
        else:
            return "STRING"