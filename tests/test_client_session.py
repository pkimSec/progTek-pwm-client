import pytest
import asyncio
import os
from src.api.client import APIClient
from src.api.models import APIError, LoginResponse
from src.utils.config import AppConfig

# Test parameters - can be overridden with environment variables
SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://127.0.0.1:5000")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@localhost")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "vlndGWHrAWAI95US")  # Must be provided to run tests

# Create config fixture
@pytest.fixture
def config():
    """Create app config for testing"""
    config = AppConfig()
    config.api_base_url = SERVER_URL
    return config

@pytest.mark.asyncio
async def test_session_persistence(config):
    """
    Test session persistence by logging in and accessing an endpoint that 
    requires an active session (@requires_active_session decorator).
    
    This test verifies the fix for the 401 errors with session cookies.
    """
    if not ADMIN_PASSWORD:
        pytest.skip("TEST_ADMIN_PASSWORD environment variable not set")
    
    # Create API client with the modified implementation
    client = APIClient(config.api_base_url)
    
    try:
        # Step 1: Log in to the server
        print(f"1. Logging in with {ADMIN_EMAIL}")
        login_response = await client.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert client.is_authenticated
        print("   Login successful!")
        
        # Step 2: Access an endpoint that requires an active session
        # This would fail with 401 if cookies aren't being preserved
        print("2. Accessing endpoint that requires active session (get_vault_salt)")
        try:
            salt = await client.get_vault_salt()
            assert salt, "Failed to get vault salt"
            print(f"   Successfully retrieved vault salt: {salt}")
            print("   Session persistence is working correctly!")
        except APIError as e:
            if e.status_code == 401:
                pytest.fail(
                    "401 Unauthorized: Session cookie is not being maintained between requests. "
                    "The fix for the APIClient is not working correctly."
                )
            else:
                pytest.fail(f"Error retrieving vault salt: {e.message} (status: {e.status_code})")
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_full_workflow(config):
    """
    Test the complete client workflow to verify all operations work 
    with session persistence fixed.
    """
    if not ADMIN_PASSWORD:
        pytest.skip("TEST_ADMIN_PASSWORD environment variable not set")
    
    client = APIClient(config.api_base_url)
    entry_id = None
    
    try:
        print("\n--- Full Client Workflow Test ---")
        
        # Step 1: Login
        print("1. Logging in")
        await client.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert client.is_authenticated
        print("   Login successful!")
        
        # Step 2: Get vault salt
        print("2. Getting vault salt")
        salt = await client.get_vault_salt()
        assert salt, "Failed to get vault salt"
        print(f"   Retrieved vault salt: {salt}")
        
        # Step 3: Try to initialize vault (may fail if already initialized)
        print("3. Setting up vault")
        try:
            await client.setup_vault("test_master_password")
            print("   Vault initialized successfully")
        except APIError as e:
            if e.status_code != 400 or "already initialized" not in e.message.lower():
                pytest.fail(f"Unexpected error during vault setup: {e.message} (status: {e.status_code})")
            print("   Vault was already initialized (expected)")
        
        # Step 4: Create password entry
        print("4. Creating password entry")
        encrypted_data = '{"iv":"dGVzdC1pdg==","ciphertext":"dGVzdC1kYXRh"}'
        entry = await client.create_entry(encrypted_data)
        entry_id = entry.id
        assert entry_id > 0
        print(f"   Created entry with ID: {entry_id}")
        
        # Step 5: List entries
        print("5. Listing entries")
        entries = await client.list_entries()
        assert any(e.id == entry_id for e in entries)
        print(f"   Listed {len(entries)} entries")
        
        # Step 6: Get specific entry
        print("6. Getting specific entry")
        retrieved = await client.get_entry(entry_id)
        assert retrieved.id == entry_id
        print(f"   Retrieved entry {entry_id}")
        
        # Step 7: Update entry
        print("7. Updating entry")
        updated_data = '{"iv":"dXBkYXRlZC1pdg==","ciphertext":"dXBkYXRlZC1kYXRh"}'
        await client.update_entry(entry_id, updated_data)
        print(f"   Updated entry {entry_id}")
        
        # Step 8: Get versions
        print("8. Getting entry versions")
        versions = await client.list_entry_versions(entry_id)
        print(f"   Retrieved {len(versions)} versions for entry {entry_id}")
        
        print("\nAll operations completed successfully!")
        
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        try:
            # Cleanup - delete entry if it was created
            if entry_id and client.is_authenticated:
                print("\nCleaning up: Deleting test entry")
                await client.delete_entry(entry_id)
                print(f"   Deleted entry {entry_id}")
                
                # Logout
                print("Logging out")
                await client.logout()
                print("   Logout successful")
        except:
            pass
            
        if client.session and not client.session.closed:
            await client.close()