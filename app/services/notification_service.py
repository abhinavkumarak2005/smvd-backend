import logging

logger = logging.getLogger(__name__)

async def send_sms(phone: str, message: str) -> None:
    logger.info("SMS STUB: To=%s Message=%s", phone, message)

async def send_email(email: str, **kwargs) -> None:
    logger.info("EMAIL STUB: To=%s Args=%s", email, kwargs)
