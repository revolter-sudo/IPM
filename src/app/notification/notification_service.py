# src/app/notification/notification_service.py

import firebase_admin
from firebase_admin import credentials, messaging
import logging
from src.app.notification.notification_schemas import NotificationServiceResponse

SERVICE_ACCOUNT_PATH = "src/app/utils/firebase/ipm-dezok-firebase-adminsdk-fbsvc-717161b8b4.json" # noqa

if not firebase_admin._apps:
    logging.info("--------------------------------")
    logging.info("FireBase Started")
    logging.info("--------------------------------")
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)


def send_push_notification(
        registration_token: str,
        title: str,
        body: str,
        data: dict = None
):
    """
    Send a push notification to a single device via FCM.

    :param registration_token: The device's FCM token 
    (passed via the request header).
    :param title: The notification title (string).
    :param body: The notification body (string).
    :param data: Optional dict of extra key-value pairs.
    """
    notification = messaging.Notification(title=title, body=body)

    message = messaging.Message(
        notification=notification,
        token=registration_token,
        data=data or {},
        android=messaging.AndroidConfig(priority="high")
    )

    try:
        response = messaging.send(message)
        logging.info(f"Successfully sent message: {response}")
        return response
    except Exception as e:
        logging.info(f"Error sending push notification: {str(e)}")
        return None


def subscribe_news(tokens, topic):
    try:
        response = messaging.subscribe_to_topic(tokens, topic)
        if response.failure_count > 0:
            return NotificationServiceResponse(
                data=None
            )
    except Exception as e:
        return NotificationServiceResponse(
            data=None,
            message=f"Error in subscribe_news: {str(e)}",
            status_code=500
        ).model_dump()
