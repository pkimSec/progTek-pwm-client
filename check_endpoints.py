import requests
import argparse
import sys
import os

def check_endpoint(base_url, endpoint, token=None):
    """Check if an endpoint exists and is accessible"""
    url = f"{base_url}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        status = response.status_code
        
        if status == 404:
            return False, f"Endpoint {endpoint} NOT FOUND (404)"
        else:
            return True, f"Endpoint {endpoint} exists (status: {status})"
    except requests.RequestException as e:
        return False, f"Error accessing {endpoint}: {str(e)}"

def login(base_url, email, password):
    """Login to get a token"""
    url = f"{base_url}/api/login"
    try:
        response = requests.post(
            url, 
            json={"email": email, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Login failed with status {response.status_code}")
            try:
                print(f"Error: {response.json()}")
            except:
                print(f"Response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error during login: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Check API endpoints")
    parser.add_argument("--url", default="http://localhost:5000", help="Base URL of the API server")
    parser.add_argument("--email", default="admin@localhost", help="Admin email")
    parser.add_argument("--password", help="Admin password")
    
    args = parser.parse_args()
    
    # Get password from args or environment
    password = args.password or os.environ.get("ADMIN_PASSWORD")
    if not password:
        print("Please provide admin password with --password or ADMIN_PASSWORD environment variable")
        sys.exit(1)
    
    # Login to get token
    print(f"Logging in to {args.url} as {args.email}...")
    token = login(args.url, args.email, password)
    if not token:
        print("Failed to get token. Exiting.")
        sys.exit(1)
    
    print(f"Successfully logged in and got token")
    
    # Endpoints to check
    endpoints = [
        # General API endpoints
        "/api/login",
        "/api/logout",
        "/api/register",
        "/api/invite",
        "/api/debug/token",
        
        # Vault endpoints
        "/api/vault/salt",
        "/api/vault/setup",
        "/api/vault/entries",
    ]
    
    # Check each endpoint
    print("\nChecking endpoints:")
    print("-" * 50)
    
    for endpoint in endpoints:
        need_auth = endpoint != "/api/login"
        success, message = check_endpoint(
            args.url, 
            endpoint, 
            token if need_auth else None
        )
        status = "✓" if success else "✗"
        print(f"{status} {message}")
    
    print("-" * 50)

if __name__ == "__main__":
    main()