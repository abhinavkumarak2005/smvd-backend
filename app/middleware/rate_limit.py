"""
Rate limiting configuration for SMVD backend.

Route-specific limits are applied via the @limiter.limit() decorator
on individual route handlers. The default (100/minute per IP) is
set in main.py when the Limiter is created.

Route-specific rules (applied as decorators in respective routers):
  /api/v1/auth/otp/send        → 3/10minute per IP
  /api/v1/auth/admin/login     → 5/5minute per IP
  POST /api/v1/bookings        → 10/hour per user

NOTE: For production, swap the in-memory storage with Redis:
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Imported by main.py — do not re-instantiate
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
