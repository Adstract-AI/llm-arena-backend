from rest_framework import status

from common.exceptions.general_exceptions import GeneralException


class ExperimentalArenaException(GeneralException):
    """Base exception for experimental arena request and workflow failures."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Experimental arena request is invalid."
    default_code = "experimental_arena_invalid"


class ExperimentalArenaIncompatibleModelsException(ExperimentalArenaException):
    """Raised when the active model pool cannot satisfy an experiment request."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "No compatible active models are available for this configuration."
    default_code = "experimental_arena_incompatible_models"


class ExperimentalArenaSamplingException(ExperimentalArenaException):
    """Raised when experimental slot values cannot produce a valid comparison."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Failed to sample valid experimental values for this battle."
    default_code = "experimental_arena_sampling_failed"


class ExperimentalArenaMissingSamplingSpecException(ExperimentalArenaException):
    """Raised when experimental sampling configuration is missing from the database."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Experimental parameter sampling configuration is missing."
    default_code = "experimental_arena_missing_sampling_spec"
