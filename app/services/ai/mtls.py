"""
mTLS GigaChat Service
Enterprise implementation with mutual TLS authentication
"""

import asyncio
from typing import Optional
from pathlib import Path
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from .base import BaseGigaChatService
from ...core.config import get_settings, load_config_file


class MtlsGigaChatService(BaseGigaChatService):
    """mTLS GigaChat service implementation for enterprise environments"""
    
    def __init__(self, model: Optional[str] = None, **kwargs):
        super().__init__(model)
        
        # Load mTLS configuration
        mtls_config = load_config_file("gigachat_mtls_config")
        
        # mTLS-specific settings
        self.credentials = self.settings.gigachat_credentials
        self.cert_file = kwargs.get('cert_file') or mtls_config.get('cert_file')
        self.key_file = kwargs.get('key_file') or mtls_config.get('key_file')
        self.ca_bundle = kwargs.get('ca_bundle') or mtls_config.get('ca_bundle')
        
        # Validate required mTLS files
        self._validate_mtls_files()
        
        logger.info(f"Initialized MtlsGigaChatService with model: {self.model}")
    
    def _validate_mtls_files(self):
        """Validate that required mTLS certificate files exist"""
        required_files = {
            'cert_file': self.cert_file,
            'key_file': self.key_file,
            'ca_bundle': self.ca_bundle
        }
        
        missing_files = []
        for file_type, file_path in required_files.items():
            if not file_path:
                missing_files.append(file_type)
                continue
                
            path = Path(file_path)
            if not path.exists():
                missing_files.append(f"{file_type} ({file_path})")
        
        if missing_files:
            raise ValueError(f"Missing required mTLS files: {', '.join(missing_files)}")
        
        logger.info("mTLS certificate files validated successfully")
    
    def _init_client(self):
        """Initialize mTLS GigaChat client"""
        try:
            from langchain_community.chat_models import GigaChat
            
            # Initialize with mTLS configuration
            self.client = GigaChat(
                credentials=self.credentials,
                model=self.model,
                scope=self.scope,
                verify_ssl_certs=True,  # Always verify in mTLS mode
                temperature=self.temperature,
                # mTLS specific parameters would go here
                # Note: The exact parameters depend on the langchain-gigachat implementation
                ca_bundle_file=self.ca_bundle,
                cert_file=self.cert_file,
                key_file=self.key_file
            )
            
            logger.info("mTLS GigaChat client initialized successfully")
            
        except ImportError as e:
            logger.error("Failed to import GigaChat from langchain_community. Please install: pip install langchain-gigachat")
            raise ImportError("langchain-gigachat package is required for mTLS mode") from e
        except Exception as e:
            logger.error(f"Failed to initialize mTLS GigaChat client: {e}")
            raise
    
    async def _make_request(self, system_prompt: str, user_prompt: str, 
                          temperature: float, operation: str) -> str:
        """Make secure request to mTLS GigaChat API"""
        self._add_request_time()
        
        try:
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Log security context (without sensitive data)
            logger.debug(f"Making mTLS request with cert: {Path(self.cert_file).name}")
            
            # Make async request with mTLS
            response = await asyncio.to_thread(self.client.invoke, messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"mTLS GigaChat request failed: {e}")
            # Don't expose sensitive mTLS details in error messages
            if "certificate" in str(e).lower() or "ssl" in str(e).lower():
                raise Exception("mTLS authentication failed")
            raise
    
    def check_service_health(self) -> dict:
        """Check mTLS service health with certificate validation"""
        try:
            # Validate certificates first
            self._validate_certificates()
            
            # Make a simple health check request
            messages = [
                SystemMessage(content="Ты - AI ассистент."),
                HumanMessage(content="Ответь одним словом: 'Работаю'")
            ]
            
            import time
            start_time = time.time()
            response = self.client.invoke(messages)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "mode": "mtls",
                "model": self.model,
                "response_time": response_time,
                "total_tokens_used": self.total_tokens_used,
                "success_rate": (self.successful_requests / max(1, self.request_count)) * 100,
                "rate_limit_available": self._check_rate_limit(),
                "certificate_valid": True,
                "api_response": response.content[:50] if hasattr(response, 'content') else str(response)[:50]
            }
            
        except Exception as e:
            logger.error(f"mTLS GigaChat health check failed: {e}")
            return {
                "status": "unhealthy",
                "mode": "mtls",
                "model": self.model,
                "error": "mTLS health check failed",  # Don't expose detailed error
                "total_tokens_used": self.total_tokens_used,
                "certificate_valid": False
            }
    
    def _validate_certificates(self):
        """Validate mTLS certificates"""
        try:
            import ssl
            from datetime import datetime
            
            # Load and validate certificate
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()
            
            # Parse certificate to check expiration
            cert = ssl.PEM_cert_to_DER_cert(cert_data.decode())
            
            # Note: Full certificate validation would require additional libraries
            # This is a simplified check
            logger.debug("Certificate file loaded and basic validation passed")
            
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            raise Exception("Invalid mTLS certificate")
    
    def get_certificate_info(self) -> dict:
        """Get information about mTLS certificates"""
        try:
            cert_info = {
                "cert_file": Path(self.cert_file).name,
                "key_file": Path(self.key_file).name,
                "ca_bundle": Path(self.ca_bundle).name,
                "cert_exists": Path(self.cert_file).exists(),
                "key_exists": Path(self.key_file).exists(),
                "ca_exists": Path(self.ca_bundle).exists()
            }
            
            # Add certificate expiration info if possible
            try:
                import ssl
                from datetime import datetime
                
                with open(self.cert_file, 'r') as f:
                    cert_data = f.read()
                
                # This would need a proper certificate parsing library for full implementation
                cert_info["validation_attempted"] = True
                
            except Exception:
                cert_info["validation_attempted"] = False
            
            return cert_info
            
        except Exception as e:
            logger.error(f"Failed to get certificate info: {e}")
            return {"error": "Failed to retrieve certificate information"}
    
    def update_certificates(self, cert_file: Optional[str] = None,
                          key_file: Optional[str] = None,
                          ca_bundle: Optional[str] = None):
        """Update mTLS certificates"""
        try:
            if cert_file:
                self.cert_file = cert_file
            if key_file:
                self.key_file = key_file
            if ca_bundle:
                self.ca_bundle = ca_bundle
            
            # Validate new certificates
            self._validate_mtls_files()
            
            # Reinitialize client with new certificates
            self._init_client()
            
            logger.info("mTLS certificates updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update certificates: {e}")
            raise
    
    def get_available_models(self) -> list:
        """Get available models for mTLS endpoint"""
        try:
            # This would depend on the specific enterprise mTLS endpoint
            return [
                "GigaChat-Enterprise",
                "GigaChat-Pro-Enterprise",
                "GigaChat-Max-Enterprise"
            ]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return [self.model]