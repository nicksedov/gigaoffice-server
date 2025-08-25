#!/usr/bin/env python3
"""
Test script to verify email validation functionality
"""

def test_email_validation():
    """Test that EmailStr works correctly after adding email-validator dependency"""
    try:
        # Import the models that use EmailStr
        from app.models.users import UserCreate, UserUpdate, PasswordReset
        from pydantic import ValidationError
        
        print("✓ Successfully imported models with EmailStr")
        
        # Test valid email in UserCreate
        try:
            user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123"
            }
            user = UserCreate(**user_data)
            print(f"✓ Valid email validation works: {user.email}")
        except Exception as e:
            print(f"✗ Valid email validation failed: {e}")
            return False
        
        # Test invalid email in UserCreate
        try:
            user_data = {
                "username": "testuser",
                "email": "invalid-email",
                "password": "SecurePass123"
            }
            user = UserCreate(**user_data)
            print("✗ Invalid email validation should have failed but didn't")
            return False
        except ValidationError:
            print("✓ Invalid email validation correctly failed")
        except Exception as e:
            print(f"✗ Unexpected error during invalid email test: {e}")
            return False
        
        # Test UserUpdate email validation
        try:
            update_data = {"email": "update@example.com"}
            user_update = UserUpdate(**update_data)
            print(f"✓ UserUpdate email validation works: {user_update.email}")
        except Exception as e:
            print(f"✗ UserUpdate email validation failed: {e}")
            return False
        
        # Test PasswordReset email validation
        try:
            reset_data = {"email": "reset@example.com"}
            password_reset = PasswordReset(**reset_data)
            print(f"✓ PasswordReset email validation works: {password_reset.email}")
        except Exception as e:
            print(f"✗ PasswordReset email validation failed: {e}")
            return False
        
        print("\n🎉 All email validation tests passed!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("💡 You may need to install email-validator package:")
        print("   pip install email-validator>=2.0.0")
        print("   or")
        print("   pip install pydantic[email]")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing email validation functionality...")
    print("=" * 50)
    success = test_email_validation()
    if not success:
        print("\n❌ Email validation test failed!")
        exit(1)
    else:
        print("\n✅ Email validation is working correctly!")