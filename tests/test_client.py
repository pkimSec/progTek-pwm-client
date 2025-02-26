import pytest
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000/api"
ADMIN_EMAIL = "admin@localhost"
ADMIN_PASSWORD = "ErvWr9PtY3AqqoaZ"

@pytest.fixture
def admin_token():
    """Fixture to get admin token for authenticated requests"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def test_user_credentials():
    """Fixture to create and return test user credentials"""
    return {
        "email": f"test_user_{datetime.now().timestamp()}@test.com",
        "password": "TestPassword123!"
    }

@pytest.fixture
def registered_test_user(admin_token, test_user_credentials):
    """Fixture to create a test user with valid credentials"""
    # Get invite code
    invite_response = requests.post(
        f"{BASE_URL}/invite",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert invite_response.status_code == 201
    invite_code = invite_response.json()["invite_code"]
    
    # Register new user
    register_data = {
        "email": test_user_credentials["email"],
        "password": test_user_credentials["password"],
        "invite_code": invite_code
    }
    register_response = requests.post(
        f"{BASE_URL}/register",
        json=register_data
    )
    assert register_response.status_code == 201
    return test_user_credentials

class TestAuthentication:
    def test_login_success(self, registered_test_user):
        """Test successful login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": registered_test_user["email"],
                "password": registered_test_user["password"]
            }
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "user_id" in response.json()
        assert "role" in response.json()
        assert response.json()["role"] == "user"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": "invalid@email.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["message"]

    def test_login_missing_fields(self):
        """Test login with missing required fields"""
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": "test@email.com"
                # Missing password field
            }
        )
        
        assert response.status_code == 400
        assert "Missing email or password" in response.json()["message"]

class TestUserManagement:
    def test_create_invite_as_admin(self, admin_token):
        """Test creating invite code as admin"""
        response = requests.post(
            f"{BASE_URL}/invite",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        assert "invite_code" in response.json()
        assert len(response.json()["invite_code"]) > 0

    def test_register_new_user(self, admin_token):
        """Test registering a new user with valid invite code"""
        # Get invite code
        invite_response = requests.post(
            f"{BASE_URL}/invite",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        invite_code = invite_response.json()["invite_code"]
        
        # Register new user
        register_data = {
            "email": f"new_user_{datetime.now().timestamp()}@test.com",
            "password": "NewUserPass123!",
            "invite_code": invite_code
        }
        response = requests.post(
            f"{BASE_URL}/register",
            json=register_data
        )
        
        assert response.status_code == 201
        assert "User registered successfully" in response.json()["message"]

    def test_register_with_invalid_invite(self):
        """Test registration with invalid invite code"""
        register_data = {
            "email": "test@email.com",
            "password": "TestPass123!",
            "invite_code": "invalid_invite_code"
        }
        response = requests.post(
            f"{BASE_URL}/register",
            json=register_data
        )
        
        assert response.status_code == 400
        assert "Invalid invite code" in response.json()["message"]

class TestSessionManagement:
    def test_logout(self, registered_test_user):
        """Test user logout"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": registered_test_user["email"],
                "password": registered_test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        
        # Then logout
        response = requests.post(
            f"{BASE_URL}/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    def test_token_validation(self, registered_test_user):
        """Test token validation using debug endpoint"""
        # Login to get token
        login_response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": registered_test_user["email"],
                "password": registered_test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        
        # Verify token
        response = requests.get(
            f"{BASE_URL}/debug/token",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "user_id" in response.json()
        assert "email" in response.json()
        assert response.json()["email"] == registered_test_user["email"]
        assert response.json()["role"] == "user"
