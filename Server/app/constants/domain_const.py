import enum


class HTTPMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class LogDomain(str, enum.Enum):
    AUTH = "auth"
    ADMIN = "admin"
    SENSOR = "sensor"
    ALERTING = "alerting"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    GRAPHQL = "graphql"
    CONFIG = "config"
    DATABASE = "database"
    OTHER = "other"

DOMAIN_ROUTE_MAP = {
    LogDomain.AUTH: ["/auth", "login", "onboard"],
    LogDomain.SENSOR: ["/sensor", "data", "by-sensor"],
    LogDomain.ADMIN: ["/admin", "delete-user", "all-users"],
}


def infer_domain(path: str) -> LogDomain:
    """
    Return the first LogDomain whose keywords are contained in `path`,
    or LogDomain.OTHER if none match.
    """
    for domain, keywords in DOMAIN_ROUTE_MAP.items():
        if any(keyword in path for keyword in keywords):
            return domain
    return LogDomain.OTHER