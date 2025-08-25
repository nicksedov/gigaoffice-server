#!/usr/bin/env python3
"""
Test Script for Modular Architecture Validation
Tests the new modular structure and basic functionality
"""

import sys
import os
import traceback
from typing import Dict, Any

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_import(module_name: str, description: str) -> bool:
    """Test importing a module and return success status"""
    try:
        exec(f"import {module_name}")
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def test_specific_import(import_statement: str, description: str) -> bool:
    """Test a specific import statement"""
    try:
        exec(import_statement)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def run_architecture_tests() -> Dict[str, Any]:
    """Run comprehensive tests of the modular architecture"""
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    print("=" * 60)
    print("GigaOffice Modular Architecture Validation")
    print("=" * 60)
    
    # Test core modules
    print("\n📦 Testing Core Modules:")
    tests = [
        ("app.core.config", "Core configuration module"),
        ("app.core.security", "Security utilities module"),
        ("app.utils.logger", "Structured logging module"),
        ("app.utils.resource_loader", "Resource loader module"),
    ]
    
    for module, desc in tests:
        results["total_tests"] += 1
        if test_import(module, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test database layer
    print("\n🗄️ Testing Database Layer:")
    tests = [
        ("app.db.session", "Database session management"),
        ("app.db.models", "ORM models"),
        ("app.db.repositories.base", "Base repository"),
        ("app.db.repositories.ai_requests", "AI requests repository"),
        ("app.db.repositories.prompts", "Prompts repository"),
    ]
    
    for module, desc in tests:
        results["total_tests"] += 1
        if test_import(module, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test service layer
    print("\n⚙️ Testing Service Layer:")
    tests = [
        ("app.services.ai.factory", "AI service factory"),
        ("app.services.kafka.service", "Kafka service"),
        ("app.services.prompts.manager", "Prompt manager"),
    ]
    
    for module, desc in tests:
        results["total_tests"] += 1
        if test_import(module, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test models
    print("\n📋 Testing Models:")
    tests = [
        ("from app.models.types import RequestStatus, UserRole", "Shared types"),
        ("from app.models.ai_requests import AIRequestCreate", "AI request models"),
        ("from app.models.users import UserCreate", "User models"),
        ("from app.models.prompts import PromptCreate", "Prompt models"),
        ("from app.models.health import ServiceHealth", "Health models"),
    ]
    
    for statement, desc in tests:
        results["total_tests"] += 1
        if test_specific_import(statement, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test API layer
    print("\n🌐 Testing API Layer:")
    tests = [
        ("app.api.endpoints.health", "Health endpoints"),
        ("app.api.endpoints.ai", "AI processing endpoints"),
        ("app.api.endpoints.prompts", "Prompts endpoints"),
        ("app.api.endpoints.metrics", "Metrics endpoints"),
        ("app.api.router", "Main API router"),
    ]
    
    for module, desc in tests:
        results["total_tests"] += 1
        if test_import(module, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test main application
    print("\n🚀 Testing Main Application:")
    tests = [
        ("app.main", "Main application"),
        ("app.lifespan", "Application lifespan"),
    ]
    
    for module, desc in tests:
        results["total_tests"] += 1
        if test_import(module, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    return results

def test_fastapi_app_creation():
    """Test FastAPI application creation"""
    print("\n🎯 Testing FastAPI Application Creation:")
    try:
        from app.main import app
        print(f"✓ FastAPI application created successfully")
        print(f"  - App title: {app.title}")
        print(f"  - OpenAPI URL: {app.openapi_url}")
        print(f"  - Routes count: {len(app.routes)}")
        return True
    except Exception as e:
        print(f"✗ FastAPI application creation failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ Testing Configuration:")
    try:
        from app.core.config import settings
        print(f"✓ Configuration loaded successfully")
        print(f"  - App name: {settings.app_name}")
        print(f"  - App version: {settings.app_version}")
        print(f"  - Environment: {settings.environment}")
        print(f"  - Database URL configured: {'✓' if settings.database_url else '✗'}")
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        traceback.print_exc()
        return False

def test_models_integration():
    """Test models integration"""
    print("\n📋 Testing Models Integration:")
    try:
        from app.models import RequestStatus, AIRequestCreate, ServiceHealth
        
        # Test enum usage
        status = RequestStatus.PENDING
        print(f"✓ RequestStatus enum works: {status}")
        
        # Test model instantiation
        request_data = {
            "query_text": "Test query",
            "category": "test",
            "priority": 1
        }
        ai_request = AIRequestCreate(**request_data)
        print(f"✓ AIRequestCreate model works: {ai_request.query_text}")
        
        # Test health model
        health = ServiceHealth(uptime=100.0)
        print(f"✓ ServiceHealth model works: {health.status}")
        
        return True
    except Exception as e:
        print(f"✗ Models integration failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    try:
        # Run architecture tests
        results = run_architecture_tests()
        
        # Additional functional tests
        app_creation_success = test_fastapi_app_creation()
        config_success = test_configuration()
        models_success = test_models_integration()
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Architecture Tests: {results['passed']}/{results['total_tests']} passed")
        print(f"FastAPI App Creation: {'✓' if app_creation_success else '✗'}")
        print(f"Configuration Loading: {'✓' if config_success else '✗'}")
        print(f"Models Integration: {'✓' if models_success else '✗'}")
        
        # Overall result
        architecture_success = results['failed'] == 0
        overall_success = all([
            architecture_success,
            app_creation_success,
            config_success,
            models_success
        ])
        
        print(f"\nOVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
        
        if overall_success:
            print("\n🎉 Modular architecture migration completed successfully!")
            print("The GigaOffice server has been successfully refactored to use")
            print("a hierarchical, domain-driven architecture.")
        else:
            print("\n⚠️ Some issues were found. Please review the failed tests above.")
        
        return overall_success
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)