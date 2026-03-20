"""
General exceptions for common operations across services.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class UserNotSetException(Exception):
    """Raised when a service operation requires an authenticated user but none is set.

    This exception should be used by service classes to signal that the operation
    cannot proceed because the user context is missing.
    """

    def __init__(self, message: str = "Authenticated user not set on service"):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class GeneralException(APIException):
    """Base exception for general service errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A general service error occurred.'
    default_code = 'general_service_error'


class RecentlyUpdatedException(GeneralException):
    """Exception raised when trying to update an entity too soon after last update"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Entity was updated too recently. Please wait before updating again.'
    default_code = 'recently_updated'

    def __init__(self, entity_id: str, entity_type: str, minutes_left: int, seconds_left: int, detail=None):
        if detail is None:
            if minutes_left > 0:
                detail = (f"{entity_type} with ID {entity_id} was updated recently. "
                          f"Please wait {minutes_left} minutes and {seconds_left} seconds before updating again.")
            else:
                detail = (f"{entity_type} with ID {entity_id} was updated recently. "
                          f"Please wait {seconds_left} seconds before updating again.")
        super().__init__(detail)