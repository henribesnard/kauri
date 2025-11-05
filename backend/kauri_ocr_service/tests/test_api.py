"""
Tests for OCR API endpoints
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_check():
    """Test liveness check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
