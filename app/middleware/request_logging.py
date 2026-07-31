import logging
import time
import uuid

from fastapi import Request

logger = logging.getLogger(__name__)


async def request_logging_middleware(request: Request, call_next):
    """
    Logs every request as a structured line:
    request_id | method | path | status | duration_ms | ip
    Adds X-Request-ID to every response.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration=%sms ip=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request.client.host if request.client else "unknown",
    )
    response.headers["X-Request-ID"] = request_id
    return response
