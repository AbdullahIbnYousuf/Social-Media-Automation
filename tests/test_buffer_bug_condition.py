"""
Bug Condition Exploration Test for Buffer GraphQL Migration

**Validates: Requirements 1.1, 1.2, 1.3**

This test is designed to FAIL on unfixed code to confirm the bug exists.
The test verifies that the current REST API implementation fails with HTTP 401
when attempting to authenticate with OIDC tokens.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected outcome on UNFIXED code: Test FAILS with HTTP 401 error
Expected outcome on FIXED code: Test PASSES with successful post creation
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from hypothesis import given, strategies as st, settings, HealthCheck

from engine import dispatch_payload_to_buffer


class TestBufferBugCondition(unittest.TestCase):
    """
    Bug Condition Exploration: REST API Authentication Failure with OIDC Tokens
    
    This test surfaces counterexamples demonstrating the bug on unfixed code.
    The bug manifests when dispatch_payload_to_buffer() attempts to use the
    REST API endpoint with Bearer token authentication.
    """

    def setUp(self) -> None:
        """Set up test environment with mock credentials."""
        # Ensure environment variables are set for testing
        os.environ["BUFFER_ACCESS_TOKEN"] = "test_token_12345"
        os.environ["BUFFER_PROFILE_ID"] = "test_profile_67890"
        os.environ["GEMINI_API_KEY"] = "test_gemini_key"

    @given(content=st.text(min_size=1, max_size=280))
    @settings(
        max_examples=3,  # Reduced to 3 examples to avoid long test times with retry logic
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=30000  # 30 second deadline per example (accounts for 3 retries with backoff)
    )
    def test_rest_api_authentication_failure_property(self, content: str) -> None:
        """
        Property 1: Bug Condition - REST API Authentication Failure with OIDC Tokens
        
        For any valid content string, the current implementation using the REST API
        endpoint should fail with HTTP 401 error containing "OIDC tokens are not accepted".
        
        This test is EXPECTED TO FAIL on unfixed code, which proves the bug exists.
        
        Scoped PBT Approach: Test concrete failing cases with any valid content string
        using the current REST API endpoint.
        
        Note: This test makes actual HTTP requests to Buffer's API with retry logic.
        Each example may take up to 30 seconds due to exponential backoff (3 retries).
        """
        # This test will make actual HTTP requests to Buffer's API
        # On unfixed code, it should fail with HTTP 401
        # On fixed code (GraphQL), it should succeed
        
        try:
            dispatch_payload_to_buffer(content)
            # If we reach here on unfixed code, the bug doesn't exist
            # On fixed code (GraphQL), this is the expected path
            print(f"\n=== SUCCESS: Post created successfully with content: '{content[:50]}...' ===")
        except requests.exceptions.HTTPError as e:
            # On unfixed code, we expect HTTP 401 error
            error_message = str(e)
            
            # Document the counterexample
            print(f"\n=== COUNTEREXAMPLE FOUND ===")
            print(f"Input: dispatch_payload_to_buffer('{content[:50]}...')")
            print(f"Expected: Successfully create post in Buffer")
            print(f"Actual: Raised HTTPError - {error_message}")
            print(f"===========================\n")
            
            # Verify the error is HTTP 401 (bug condition)
            self.assertIn("401", error_message, 
                         f"Expected HTTP 401 error, got: {error_message}")
            
            # This assertion will fail on unfixed code, confirming the bug exists
            self.fail(f"Bug confirmed: REST API authentication failed with HTTP 401 for content: '{content[:50]}...'")

    def test_graphql_api_request_format_verification(self) -> None:
        """
        Verify the current implementation uses GraphQL API request format.
        
        This test inspects the actual request being made to confirm:
        - Uses GraphQL endpoint
        - Uses application/json content type
        - Sends GraphQL query and variables payload
        - Uses Bearer token authentication
        """
        test_content = "Test content for format verification"
        
        # Mock the requests.post to capture the actual request details
        with patch('engine.requests.post') as mock_post:
            # Configure mock to return a successful GraphQL response body.
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"data": {"createPost": {"post": {"id": "abc123"}}}}'
            mock_response.json.return_value = {
                "data": {
                    "createPost": {
                        "post": {
                            "id": "abc123"
                        }
                    }
                }
            }
            mock_post.return_value = mock_response
            
            dispatch_payload_to_buffer(test_content)
            
            # Verify the request was made with GraphQL format
            self.assertTrue(mock_post.called, "requests.post should have been called")
            
            call_args = mock_post.call_args
            
            # Verify GraphQL endpoint
            url = call_args[0][0] if call_args[0] else call_args[1].get('url')
            self.assertEqual(url, "https://api.buffer.com/graphql",
                           f"Expected GraphQL endpoint, got: {url}")
            
            # Verify headers include Bearer token and JSON content type
            headers = call_args[1].get('headers', {})
            self.assertIn("Authorization", headers)
            self.assertTrue(headers["Authorization"].startswith("Bearer "),
                          f"Expected Bearer token auth, got: {headers.get('Authorization')}")
            self.assertEqual(headers.get("Content-Type"), "application/json",
                           f"Expected JSON content type, got: {headers.get('Content-Type')}")
            
            # Verify payload uses GraphQL query + variables structure.
            payload = call_args[1].get('json', {})
            self.assertIn("query", payload, f"Expected GraphQL query, got keys: {list(payload.keys())}")
            self.assertIn("variables", payload, f"Expected GraphQL variables, got keys: {list(payload.keys())}")

            variables = payload.get("variables", {})
            input_data = variables.get("input", {})
            self.assertEqual(input_data.get("profileId"), "test_profile_67890")
            self.assertEqual(input_data.get("text"), test_content)
            self.assertEqual(input_data.get("shorten"), False)
            
            # Verify timeout is set
            timeout = call_args[1].get('timeout')
            self.assertEqual(timeout, 15, f"Expected timeout=15, got: {timeout}")

    def test_concrete_bug_example(self) -> None:
        """
        Concrete example demonstrating the bug with a specific test case.
        
        This test provides a clear counterexample:
        dispatch_payload_to_buffer('Test content') raises HTTPError with 401 status
        instead of successfully creating a post.
        
        Note: This test makes actual HTTP requests with retry logic (may take ~30 seconds).
        """
        test_content = "Test content for Buffer post"
        
        # On unfixed code, this should raise HTTP 401 error
        # On fixed code (GraphQL), this should succeed without raising an error
        try:
            dispatch_payload_to_buffer(test_content)
            # If we reach here on unfixed code, the bug doesn't exist
            print(f"\n=== SUCCESS: Post created successfully ===")
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            
            # Document the counterexample
            print(f"\n=== COUNTEREXAMPLE FOUND ===")
            print(f"Input: dispatch_payload_to_buffer('{test_content}')")
            print(f"Expected: Successfully create post in Buffer")
            print(f"Actual: Raised HTTPError - {error_message}")
            print(f"Root Cause: REST API endpoint rejects OIDC tokens with HTTP 401")
            print(f"===========================\n")
            
            # Verify it's a 401 error
            self.assertIn("401", error_message)
            
            # This assertion will fail on unfixed code, confirming the bug exists
            self.fail(f"Bug confirmed: REST API authentication failed with HTTP 401")


if __name__ == "__main__":
    unittest.main()
