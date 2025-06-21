from enum import Enum

class WebhookEvent(str, Enum):
    SENSOR_CREATED = "sensor_created"
    SENSOR_DATA_RECEIVED = "sensor_data_received"
    ALERT_TRIGGERED = "alert_triggered"
    SENSOR_STATUS_CHANGED = "sensor_status_changed"
    SENSOR_DELETED = "sensor_deleted"


ROLE_TO_WEBHOOK_EVENTS = {
    "admin": [e.value for e in WebhookEvent],
    "developer": ["sensor_created", "sensor_data_received", "sensor_status_changed"],
    "authenticated": ["sensor_data_received", "alert_triggered","sensor_created", "sensor_status_changed"],
    "guest": [],
}

