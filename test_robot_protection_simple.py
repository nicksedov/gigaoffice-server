"""
Simple test for robot protection - syntax and import checks
"""

print("Testing robot protection implementation...\n")

# Test 1: Check robots.py can be imported
try:
    from app.api.robots import robots_router, get_robots_txt
    print("✓ robots.py imports successfully")
    print(f"  - Router registered: {robots_router is not None}")
    print(f"  - Handler function exists: {callable(get_robots_txt)}")
except Exception as e:
    print(f"✗ Failed to import robots.py: {e}")
    exit(1)

# Test 2: Check middleware can be imported
try:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    print("\n✓ SecurityHeadersMiddleware imports successfully")
    print(f"  - Class exists: {SecurityHeadersMiddleware is not None}")
except Exception as e:
    print(f"\n✗ Failed to import SecurityHeadersMiddleware: {e}")
    exit(1)

# Test 3: Verify middleware package
try:
    from app.middleware import SecurityHeadersMiddleware as MwImport
    print("\n✓ Middleware package exports SecurityHeadersMiddleware")
except Exception as e:
    print(f"\n✗ Failed to import from middleware package: {e}")
    exit(1)

# Test 4: Check file structure
import os

files_to_check = [
    (os.path.join("app", "api", "robots.py"), "Robots.txt endpoint"),
    (os.path.join("app", "middleware", "__init__.py"), "Middleware package init"),
    (os.path.join("app", "middleware", "security_headers.py"), "Security headers middleware"),
]

print("\n✓ File structure check:")
base_path = os.path.abspath(os.path.dirname(__file__))
all_exist = True

for file_path, description in files_to_check:
    full_path = os.path.join(base_path, file_path)
    exists = os.path.exists(full_path)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {file_path}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n✗ Some files are missing")
    exit(1)

# Test 5: Verify robots.txt content format
print("\n✓ Testing robots.txt content generation:")
import asyncio

async def test_content():
    content = await get_robots_txt()
    text = content.body.decode('utf-8')
    
    checks = [
        ("User-agent: *" in text, "User-agent directive"),
        ("Disallow: /" in text, "Disallow directive"),
        ("GigaOffice AI Service" in text, "Service description"),
    ]
    
    all_passed = True
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"  {status} {description}")
        if not check:
            all_passed = False
    
    # Check headers
    has_cache = "Cache-Control" in content.headers
    status = "✓" if has_cache else "✗"
    print(f"  {status} Cache-Control header")
    if not has_cache:
        all_passed = False
    
    return all_passed

content_ok = asyncio.run(test_content())
if not content_ok:
    print("\n✗ Content validation failed")
    exit(1)

# Test 6: Verify middleware dispatch method exists
print("\n✓ Testing SecurityHeadersMiddleware implementation:")
import inspect

middleware_methods = inspect.getmembers(SecurityHeadersMiddleware, predicate=inspect.isfunction)
has_dispatch = any(name == 'dispatch' for name, _ in middleware_methods)

status = "✓" if has_dispatch else "✗"
print(f"  {status} dispatch method exists")

if not has_dispatch:
    print("\n✗ Middleware missing dispatch method")
    exit(1)

print("\n" + "="*50)
print("✅ All robot protection implementation checks passed!")
print("="*50)
print("\nImplementation summary:")
print("  • robots.txt endpoint created at /robots.txt")
print("  • Security headers middleware added")
print("  • All files created and properly structured")
print("  • Imports working correctly")
print("\nNote: Full integration test requires running server with all dependencies.")
