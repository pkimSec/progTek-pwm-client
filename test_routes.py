import aiohttp
import asyncio
import sys
import os

# Get admin credentials from environment or use defaults
SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:5000")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@localhost")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "z_i7EOYDfgJlKPG5")

if not ADMIN_PASSWORD:
    print("Please set TEST_ADMIN_PASSWORD environment variable")
    sys.exit(1)

async def test_endpoints():
    """
    Test if the server endpoints are correctly registered and accessible.
    This will help diagnose 404 errors.
    """
    async with aiohttp.ClientSession() as session:
        # Step 1: Login to get token
        print(f"Testing login to {SERVER_URL}/api/login")
        login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        async with session.post(f"{SERVER_URL}/api/login", json=login_data) as response:
            status = response.status
            print(f"Login status: {status}")
            
            if status == 200:
                login_result = await response.json()
                token = login_result.get("access_token")
                print(f"Successfully received token")
                
                # Test auth-required endpoints
                endpoints = [
                    "/api/logout",
                    "/api/vault/salt",
                    "/api/vault/entries",
                    "/api/vault/setup"
                ]
                
                headers = {"Authorization": f"Bearer {token}"}
                
                for endpoint in endpoints:
                    url = f"{SERVER_URL}{endpoint}"
                    print(f"\nTesting endpoint: {url}")
                    async with session.get(url, headers=headers) as resp:
                        print(f"Status: {resp.status}")
                        print(f"Content-Type: {resp.headers.get('Content-Type', 'None')}")
                        
                        # If we got a 404, the endpoint doesn't exist
                        if resp.status == 404:
                            print("ENDPOINT NOT FOUND - Route is not registered with Flask")
                        
                        # Try to get the response content
                        try:
                            data = await resp.json()
                            print(f"JSON response: {data}")
                        except:
                            try:
                                text = await resp.text()
                                print(f"Text response: {text[:100]}..." if len(text) > 100 else text)
                            except:
                                print("Could not read response")
            else:
                print("Login failed")
                try:
                    error_data = await response.json()
                    print(f"Error: {error_data}")
                except:
                    error_text = await response.text()
                    print(f"Error response: {error_text}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())