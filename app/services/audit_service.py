import logging

logger = logging.getLogger(__name__)

async def write_log(action: str, **kwargs) -> None:
    logger.info("AUDIT STUB: %s | %s", action, kwargs)
