# src/app/notification/notification_service.py

import logging
from typing import Any, Optional

import firebase_admin  # type: ignore
from firebase_admin import credentials, messaging

from src.app.notification.notification_schemas import NotificationServiceResponse

SERVICE_ACCOUNT_PATH = "/app/src/app/utils/firebase/secret_files.json"  # noqa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_or_up_firebase_app() -> None:
    if not firebase_admin._apps:
        logger.info("--------------------------------")
        logger.info("FireBase Started")
        logger.info("--------------------------------")
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return None


def send_push_notification(
    topic: str, title: str, body: str, data: Optional[dict] = None
) -> Optional[str]:
    """
    Send a push notification to a single device via FCM.
    :param registration_token: The device's FCM token
    (passed via the request header).
    :param title: The notification title (string).
    :param body: The notification body (string).
    :param data: Optional dict of extra key-value pairs.
    """
    # check_or_up_firebase_app()
    notification = messaging.Notification(title=title, body=body)

    message = messaging.Message(
        topic=topic,
        notification=notification,
        data=data or {},
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return str(response)
    except Exception as e:
        logger.info(f"Error sending push notification: {str(e)}")
        return None


def subscribe_news(tokens: list[str], topic: str) -> Optional[dict[str, Any]]:
    try:
        # check_or_up_firebase_app()
        response = messaging.subscribe_to_topic(tokens, str(topic))
        if response.failure_count > 0:
            return NotificationServiceResponse(
                data=None, message="Failed to subscribe to the topic", status_code=200
            ).model_dump()
    except Exception as e:
        return NotificationServiceResponse(
            data=None, message=f"Error in subscribe_news: {str(e)}", status_code=500
        ).model_dump()
    return None


def unsubscribe_news(tokens: list[str], topic: str) -> Optional[dict[str, Any]]:
    response = messaging.unsubscribe_from_topic(tokens, topic)
    if response.failure_count > 0:
        return NotificationServiceResponse(
            data=None, message="Failed to Unsubscribe Topic", status_code=200
        ).model_dump()
    return None


unsubscribe_news.__annotations__["return"] = object
