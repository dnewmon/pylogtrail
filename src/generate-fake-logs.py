import logging
import json
from datetime import datetime
import traceback

from pylogtrail.client.handlers import PyLogTrailContext

logging.basicConfig(
    level=logging.NOTSET,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

with PyLogTrailContext("localhost:5000", metadata={"service": "test"}):
    # Simple log messages
    logger.info("Application startup complete")
    logger.debug("Connected to database with connection pool size: 5")

    # Log with JSON data
    user_data = {
        "id": "usr_123456",
        "name": "John Smith",
        "email": "john.smith@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True,
            "timezone": "America/New_York",
        },
        "last_login": datetime.now().isoformat(),
    }
    logger.info(f"User profile updated: {json.dumps(user_data, indent=2)}")

    # Very long log message
    logger.warning(
        "Detected unusual traffic pattern from IP 192.168.1.100: Multiple failed login attempts detected with suspicious timing patterns. User agent strings indicate potential automated attack. Rate limiting has been automatically applied. Additional security measures may be required if this pattern continues. Current rate: 457 requests/minute, Normal baseline: 23 requests/minute, Deviation: +1887%. Attack signature matches known botnet patterns. Security team has been notified via incident response system. Temporary IP block applied for 1 hour. Full audit log has been archived to security-events-2024-03-15.log"
    )

    # Exception with stack trace
    try:
        result = 1 / 0
    except Exception as e:
        logger.error(
            "Critical error in calculation module\n"
            + "".join(traceback.format_exception(type(e), e, e.__traceback__))
        )

    # Another complex error scenario
    try:
        invalid_json = "{'broken': json"
        json.loads(invalid_json)
    except Exception as e:
        logger.exception(
            f"Failed to parse configuration file: {str(e)}\nInvalid content: {invalid_json}"
        )
