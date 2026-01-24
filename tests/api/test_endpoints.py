"""Simplified API endpoint tests for FastAPI routes."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestHealthCheck:
    """Health check endpoint tests."""

    def test_health_check_returns_200(self):
        """Test health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.3.0"
        assert "dependencies" in data

    def test_health_check_has_timestamp(self):
        """Test health check includes timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data
        # Verify timestamp is ISO format
        datetime.fromisoformat(data["timestamp"])

    def test_health_check_dependencies(self):
        """Test health check includes dependency status."""
        response = client.get("/health")
        data = response.json()
        assert "dependencies" in data
        assert isinstance(data["dependencies"], dict)
        assert len(data["dependencies"]) > 0


class TestRootEndpoint:
    """Root endpoint tests."""

    def test_root_endpoint(self):
        """Test root endpoint returns metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Phonox API"
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    def test_docs_endpoint_exists(self):
        """Test API docs endpoint exists."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint_exists(self):
        """Test OpenAPI schema endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data


class TestIdentifyEndpointValidation:
    """Test identify endpoint validation without database."""

    def test_identify_missing_image_paths(self):
        """Test identify endpoint rejects request without image_paths."""
        response = client.post(
            "/api/v1/identify",
            json={"user_notes": "Test"},
        )
        # Pydantic validation error
        assert response.status_code == 422

    def test_identify_empty_image_paths(self):
        """Test identify endpoint rejects empty image list."""
        response = client.post(
            "/api/v1/identify",
            json={"image_paths": []},
        )
        # Pydantic validation error - too short
        assert response.status_code == 422

    def test_identify_too_many_images(self):
        """Test identify endpoint rejects >5 images."""
        response = client.post(
            "/api/v1/identify",
            json={"image_paths": [f"/path/to/image{i}.jpg" for i in range(6)]},
        )
        # Pydantic validation error - too long
        assert response.status_code == 422

    def test_identify_valid_request_structure(self):
        """Test identify endpoint accepts valid request structure."""
        # This will fail at database level, but we're testing the request validation
        response = client.post(
            "/api/v1/identify",
            json={
                "image_paths": ["/path/to/image1.jpg"],
                "user_notes": "Test note",
            },
        )
        # Will be 500 because of database, but not 422 validation error
        assert response.status_code != 422


class TestReviewEndpointValidation:
    """Test review endpoint validation."""

    def test_review_accepts_partial_metadata(self):
        """Test review endpoint accepts partial metadata update."""
        response = client.post(
            "/api/v1/identify/test-id/review",
            json={"artist": "Test Artist"},
        )
        # Will fail with 500 (db not available), but request should be valid
        assert response.status_code in [404, 500]  # Not a validation error

    def test_review_accepts_genres(self):
        """Test review endpoint accepts genres list."""
        response = client.post(
            "/api/v1/identify/test-id/review",
            json={"genres": ["Rock", "Pop"]},
        )
        # Will fail with 500 (db not available), but request should be valid
        assert response.status_code in [404, 500]  # Not a validation error

    def test_review_accepts_notes(self):
        """Test review endpoint accepts notes."""
        response = client.post(
            "/api/v1/identify/test-id/review",
            json={"notes": "Test review notes"},
        )
        # Will fail with 500 (db not available), but request should be valid
        assert response.status_code in [404, 500]  # Not a validation error


class TestEndpointExists:
    """Test that all required endpoints are registered."""

    def test_identify_endpoint_exists(self):
        """Test /api/v1/identify endpoint exists."""
        response = client.options("/api/v1/identify")
        # Should not be 404
        assert response.status_code != 404

    def test_get_record_endpoint_exists(self):
        """Test /api/v1/identify/{record_id} endpoint exists."""
        response = client.options("/api/v1/identify/test-id")
        # Should not be 404
        assert response.status_code != 404

    def test_review_endpoint_exists(self):
        """Test /api/v1/identify/{record_id}/review endpoint exists."""
        response = client.options("/api/v1/identify/test-id/review")
        # Should not be 404
        assert response.status_code != 404


class TestAPIDocumentation:
    """Test API documentation."""

    def test_openapi_schema_valid(self):
        """Test OpenAPI schema is valid."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        
        # Check info
        assert data["info"]["title"] == "Phonox API"
        assert "version" in data["info"]

    def test_openapi_includes_all_endpoints(self):
        """Test OpenAPI schema includes all defined endpoints."""
        response = client.get("/openapi.json")
        data = response.json()
        paths = data["paths"]
        
        # Check for main endpoints
        assert "/health" in paths
        assert "/api/v1/identify" in paths
