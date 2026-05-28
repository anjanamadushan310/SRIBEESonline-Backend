"""
FreshCart FastAPI Backend - API v1 Module
"""
from app.api.v1 import auth
from app.api.v1.router import router

__all__ = ["auth", "router"]
