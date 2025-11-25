"""
SSL Certificate Handler for Kafka Service
Manages SSL certificate validation and context creation
"""

import ssl
from pathlib import Path
from typing import Optional
from loguru import logger

from .config import KafkaConfig


class SSLHandler:
    """Handles SSL certificate validation and context creation for Kafka connections"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize SSL handler with configuration
        
        Args:
            config: Kafka configuration containing SSL settings
        """
        self.config = config
    
    def validate_certificates(self) -> None:
        """
        Validate SSL certificates before use
        
        Raises:
            FileNotFoundError: If certificate files don't exist
            ValueError: If SSL is enabled but required files are missing
        """
        if not self.config.use_ssl or not self.config.ssl_verify_certificates:
            return
        
        logger.info("Validating SSL certificates")
        
        # Check CA certificate file
        if self.config.ssl_cafile:
            ca_path = Path(self.config.ssl_cafile)
            if not ca_path.exists():
                raise FileNotFoundError(f"CA certificate file not found: {self.config.ssl_cafile}")
            if not ca_path.is_file():
                raise ValueError(f"CA certificate path is not a file: {self.config.ssl_cafile}")
            logger.info(f"✓ CA certificate file exists: {self.config.ssl_cafile}")
        else:
            raise ValueError("SSL is enabled but KAFKA_SSL_CAFILE is not set")
        
        # Check client certificate file if provided
        if self.config.ssl_certfile:
            cert_path = Path(self.config.ssl_certfile)
            if not cert_path.exists():
                raise FileNotFoundError(f"Client certificate file not found: {self.config.ssl_certfile}")
            if not cert_path.is_file():
                raise ValueError(f"Client certificate path is not a file: {self.config.ssl_certfile}")
            logger.info(f"✓ Client certificate file exists: {self.config.ssl_certfile}")
        
        # Check private key file if provided
        if self.config.ssl_keyfile:
            key_path = Path(self.config.ssl_keyfile)
            if not key_path.exists():
                raise FileNotFoundError(f"Private key file not found: {self.config.ssl_keyfile}")
            if not key_path.is_file():
                raise ValueError(f"Private key path is not a file: {self.config.ssl_keyfile}")
            logger.info(f"✓ Private key file exists: {self.config.ssl_keyfile}")
        
        logger.info("SSL certificate validation completed successfully")
    
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for Kafka connection
        
        Returns:
            SSL context if SSL is enabled, None otherwise
            
        Raises:
            Exception: If SSL context creation fails
        """
        if not self.config.use_ssl:
            return None
        
        try:
            # Validate certificates first
            self.validate_certificates()
            
            # Create SSL context with certificate verification
            logger.info("Creating SSL context for Kafka connection")
            logger.info(f"  Trusted CA file: {self.config.ssl_cafile}")
            ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.config.ssl_cafile
            )
            
            # Load client certificate and key if provided
            if self.config.ssl_certfile and self.config.ssl_keyfile:
                logger.info("Loading client certificate and key for Kafka connection") 
                logger.info(f"  Client certificate: {self.config.ssl_certfile}")
                logger.info(f"  Private key: {self.config.ssl_keyfile}")
                ssl_context.load_cert_chain(
                    certfile=self.config.ssl_certfile,
                    keyfile=self.config.ssl_keyfile,
                    password=self.config.ssl_password.encode() if self.config.ssl_password else None
                )
            
            logger.info(f"SSL context created successfully (protocol: {ssl_context.protocol})")
            return ssl_context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
