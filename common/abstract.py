"""
Abstract service classes for the Adstract application.

This module provides base abstract service classes that can be used throughout
the application to maintain consistency in service-based architecture for all entities.

The abstract classes are designed to handle common patterns in Django applications:
- AbstractService: For services that work across multiple models or handle external integrations
- AbstractModelService: For services tied to specific Django models with common CRUD operations
- AbstractServiceView: For API views that enforce the use of service classes

The AbstractModelService includes support for 1-M relationship filtering through the
search_keys parameter, allowing for parent-child entity validation and retrieval.

The AbstractServiceView ensures proper separation of concerns by requiring views to
specify and use service classes for business logic.
"""

from abc import ABC
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.http import Http404
from rest_framework.views import APIView

from common.exceptions.general_exceptions import UserNotSetException

# Type variables for generic typing
ModelType = TypeVar('ModelType', bound=models.Model)
ServiceType = TypeVar('ServiceType', bound='AbstractService')


class AbstractService(ABC):
    """
    Abstract base service class for services that don't need to be tied to a specific model.

    This class provides a foundation for service classes that handle business logic
    without being directly connected to a Django model. Use this for services that
    work across multiple models or handle external integrations.

    Automatic User Context Propagation:
        When a service is instantiated with a user, it automatically scans for all
        class attributes ending with '_service' and propagates the user context to
        those nested services. This ensures that all nested services have access to
        the same user context without manual setup.

        Example:
            class CampaignService(AbstractModelService[Campaign]):
                advertiser_service = AccountAdvertiserService()  # Class field

                def some_method(self):
                    # advertiser_service.user is automatically set when
                    # CampaignService is instantiated with a user
                    return self.advertiser_service.get_advertiser_for_account(self.user)
    """

    def __init__(self, user=None):
        """Initialize the service."""
        self._user = user
        self._set_nested_service_context()

    def _set_nested_service_context(self):
        """
        Automatically set user context for all service fields.

        This method scans for class attributes ending with '_service' and sets
        the user context for each found service instance.
        """
        for attr_name in dir(self.__class__):
            if attr_name.endswith('_service') and not attr_name.startswith('_'):
                service_instance = getattr(self, attr_name, None)
                if service_instance and hasattr(service_instance, 'set_user'):
                    service_instance.set_user(self._user)
                elif service_instance and hasattr(service_instance, 'user'):
                    service_instance.user = self._user

    def set_user(self, user):
        """
        Set the user context for this service and propagate to nested services.

        Args:
            user: The user to set as context
        """
        self._user = user
        self._set_nested_service_context()

    @property
    def user(self):
        """
        Get the user associated with this service, raising a clear exception if
        the user is not set.

        Returns:
            The authenticated user object.

        Raises:
            UserNotSetException: if no user has been set on the service.
        """
        if not hasattr(self, '_user') or self._user is None:
            raise UserNotSetException()
        return self._user

    @property
    def has_user(self):
        """
           Checks if the service has a set user. Returns true if it has.
        """
        return self._user is not None

    def get_service(self, service_class: Type[ServiceType], **kwargs) -> ServiceType:
        """
        Get an instance of another service with user context propagated.

        Args:
            service_class: The service class to instantiate
            **kwargs: Additional arguments to pass to the service constructor

        Returns:
            ServiceType: An instance of the service with user context set

        Example:
            # In a service method:
            advertiser_service = self.get_service(AccountAdvertiserService)
            advertiser = advertiser_service.get_advertiser_for_account(self.user)
        """
        service_instance = service_class(user=self._user, **kwargs)
        return service_instance


class AbstractModelService(AbstractService, Generic[ModelType]):
    """
    Abstract service class for services that are tied to a specific Django model.

    This class provides common model-related functionality
    for services that work with any Django model in the application.

    The model type is automatically inferred from the Generic type parameter,
    so you don't need to specify a separate model field.

    Type Parameters:
        ModelType: The Django model type this service works with.

    Examples:
        class CampaignService(AbstractModelService[Campaign]):
            pass  # No need to specify model = Campaign
    """

    def __init__(self, user=None):
        """Initialize the model service."""
        super().__init__(user=user)  # Initialize user attribute and set context for nested services
        self._model = self._get_model_from_generic()
        if self._model is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must be properly parameterized with a model type. "
                f"Example: class {self.__class__.__name__}(AbstractModelService[YourModel])"
            )

    def _get_model_from_generic(self) -> Optional[Type[ModelType]]:
        """
        Extract the model type from the generic type parameter.

        Returns:
            Optional[Type[ModelType]]: The model class or None if not found.
        """
        # Get the generic bases for this class
        for base in getattr(self.__class__, '__orig_bases__', []):
            # Check if this is our AbstractModelService generic
            if hasattr(base, '__origin__') and base.__origin__ is AbstractModelService:
                # Extract the type argument
                args = getattr(base, '__args__', ())
                if args:
                    model_type = args[0]
                    # Handle forward references and ensure it's a model
                    if isinstance(model_type, str):
                        # This is a forward reference, we can't resolve it here
                        return None
                    if hasattr(model_type, '_meta') and hasattr(model_type._meta, 'model'):
                        return model_type
                    elif issubclass(model_type, models.Model):
                        return model_type
        return None

    @property
    def model(self) -> Type[ModelType]:
        """
        Get the model class for this service.

        Returns:
            Type[ModelType]: The Django model class.
        """
        return self._model

    def get_queryset(self) -> QuerySet[ModelType]:
        """
        Get the base queryset for the model.
        Can be overridden to add default filtering, select_related, etc.

        Returns:
            QuerySet[ModelType]: Base queryset for the model.
        """
        return self.model.objects.all()

    def get_object(self, pk: Union[int, str], search_keys: Dict[str, Any] = None) -> ModelType:
        """
        Retrieve a single object by its primary key with optional additional filters.

        This method is particularly useful for retrieving objects in 1-M relationships
        where you need to ensure the object belongs to a specific parent entity.

        Args:
            pk: The primary key of the object to retrieve.
            search_keys: Optional dictionary of additional filters to apply.
                        Commonly used for filtering by parent objects in 1-M relationships.
                        Example: {'campaign_id': 123, 'advertiser_id': 456}

        Returns:
            ModelType: The retrieved model instance.

        Raises:
            Http404: If the object is not found or doesn't match the search criteria.
            ValueError: If search_keys contains invalid field names.

        Examples:
            # Simple retrieval by ID
            obj = service.get_object(pk=123)

            # Retrieval with parent relationship validation
            # Ensures the ad belongs to the specified campaign and advertiser
            ad = service.get_object(pk=456, search_keys={
                'campaign_id': 123,
                'advertiser_id': 789
            })
        """
        try:
            queryset = self.get_queryset()

            # Build the filter dictionary starting with the primary key
            filters = {'pk': pk}

            # Add search_keys to filters if provided
            if search_keys:
                if not isinstance(search_keys, dict):
                    raise ValueError("search_keys must be a dictionary")
                filters.update(search_keys)

            return queryset.get(**filters)

        except ObjectDoesNotExist:
            # Create a more descriptive error message
            if search_keys:
                search_info = ", ".join([f"{k}={v}" for k, v in search_keys.items()])
                raise Http404(
                    f"{self.model.__name__} with ID {pk} and criteria ({search_info}) not found"
                )
            else:
                raise Http404(f"{self.model.__name__} with ID {pk} not found")
        except Exception as e:
            # Handle potential field errors (e.g., invalid field names in search_keys)
            if "Cannot resolve keyword" in str(e):
                raise ValueError(f"Invalid field in search criteria: {e}")
            raise

    def get_object_or_none(self, pk: Union[int, str], search_keys: Dict[str, Any] = None) -> Optional[ModelType]:
        """
        Retrieve a single object by its primary key with optional additional filters,
        or return None if not found.

        This method is particularly useful for retrieving objects in 1-M relationships
        where you need to ensure the object belongs to a specific parent entity,
        but want to handle missing objects gracefully.

        Args:
            pk: The primary key of the object to retrieve.
            search_keys: Optional dictionary of additional filters to apply.
                        Commonly used for filtering by parent objects in 1-M relationships.
                        Example: {'campaign_id': 123, 'advertiser_id': 456}

        Returns:
            Optional[ModelType]: The retrieved model instance or None if not found.

        Raises:
            ValueError: If search_keys contains invalid field names.

        Examples:
            # Simple retrieval by ID
            obj = service.get_object_or_none(pk=123)

            # Retrieval with parent relationship validation
            ad = service.get_object_or_none(pk=456, search_keys={
                'campaign_id': 123,
                'advertiser_id': 789
            })
            if ad is None:
                # Handle case where ad doesn't exist or doesn't belong to the campaign
                pass
        """
        try:
            queryset = self.get_queryset()

            # Build the filter dictionary starting with the primary key
            filters = {'pk': pk}

            # Add search_keys to filters if provided
            if search_keys:
                if not isinstance(search_keys, dict):
                    raise ValueError("search_keys must be a dictionary")
                filters.update(search_keys)

            return queryset.get(**filters)

        except ObjectDoesNotExist:
            return None
        except Exception as e:
            # Handle potential field errors (e.g., invalid field names in search_keys)
            if "Cannot resolve keyword" in str(e):
                raise ValueError(f"Invalid field in search criteria: {e}")
            raise

    def get_objects(self, search_keys: Dict[str, Any] = None) -> QuerySet[ModelType]:
        """
        Retrieve multiple objects with optional filtering using search keys.

        This method is useful for getting all objects that belong to a specific parent
        in 1-M relationships.

        Args:
            search_keys: Optional dictionary of filters to apply.
                        Example: {'campaign_id': 123, 'advertiser_id': 456}

        Returns:
            QuerySet[ModelType]: Filtered queryset of model instances.

        Raises:
            ValueError: If search_keys contains invalid field names.

        Examples:
            # Get all ads for a specific campaign
            ads = service.get_objects(search_keys={'campaign_id': 123})

            # Get all ads for a specific campaign and advertiser
            ads = service.get_objects(search_keys={
                'campaign_id': 123,
                'advertiser_id': 789
            })
        """
        try:
            queryset = self.get_queryset()

            if search_keys:
                if not isinstance(search_keys, dict):
                    raise ValueError("search_keys must be a dictionary")
                queryset = queryset.filter(**search_keys)

            return queryset

        except Exception as e:
            # Handle potential field errors (e.g., invalid field names in search_keys)
            if "Cannot resolve keyword" in str(e):
                raise ValueError(f"Invalid field in search criteria: {e}")
            raise

    def count_objects(self, **filters) -> int:
        """
        Count objects with optional filtering.

        Args:
            **filters: Optional filters to apply to the queryset.

        Returns:
            int: Number of objects matching the criteria.
        """
        queryset = self.model.objects.filter(**filters) if filters else self.get_queryset()
        return queryset.count()

    def exists(self, **filters) -> bool:
        """
        Check if any objects exist with the given filters.

        Args:
            **filters: Filter parameters for the queryset.

        Returns:
            bool: True if any objects match the criteria.
        """
        return self.model.objects.filter(**filters).exists()


class ServiceView(APIView, Generic[ServiceType]):
    """
    Abstract base view class that enforces the use of a service layer.

    This class ensures that views are properly connected to service classes,
    promoting separation of concerns and consistent architecture throughout
    the application.

    Type Parameters:
        ServiceType: The service class type this view uses.

    Attributes:
        service_class: The service class to use. Must be set in subclasses.
    """

    service_class: Type[ServiceType] = None
    _service_instance: Optional[ServiceType] = None

    def __init__(self, **kwargs):
        """
        Initialize the service view.

        Raises:
            NotImplementedError: If service_class is not defined in the subclass.
        """
        super().__init__(**kwargs)
        if self.service_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define a 'service_class' attribute. "
                f"Example: service_class = CampaignService"
            )

    def get_service(self) -> ServiceType:
        """
        Get the service instance for this view.

        This method implements lazy instantiation - the service is created
        only when first accessed and then cached for subsequent calls.
        It also injects the current user from the request into the service.

        Returns:
            ServiceType: An instance of the configured service class with user set.

        Raises:
            NotImplementedError: If service_class is not defined.

        Examples:
            class CampaignView(AbstractServiceView[CampaignService]):
                service_class = CampaignService

                def get(self, request, pk):
                    service = self.get_service()
                    # service.user is now available and set to request.user
                    campaign = service.get_object(pk=pk)
                    return Response(campaign_data)
        """
        if self.service_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define a 'service_class' attribute. "
                f"Example: service_class = CampaignService"
            )

        # Lazy instantiation with caching
        if self._service_instance is None:
            # Instantiate service without user initially
            self._service_instance = self.service_class()

        # Always update user context from current request (authentication may have changed)
        if hasattr(self, 'request') and self.request and hasattr(self.request, 'user'):
            self._service_instance.set_user(self.request.user)

        return self._service_instance

    @property
    def service(self) -> ServiceType:
        """
        Property accessor for the service instance.

        This provides a convenient way to access the service as a property.

        Returns:
            ServiceType: The service instance.

        Examples:
            # Both of these are equivalent:
            service = self.get_service()
            service = self.service
        """
        return self.get_service()

    def ensure_user_context(self):
        """
        Ensure the service has the current user context.

        This method can be called explicitly in view methods to guarantee
        the service has the authenticated user before performing operations.
        """
        if self._service_instance and hasattr(self, 'request') and self.request:
            if hasattr(self.request, 'user'):
                self._service_instance.set_user(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to ensure service class is defined.

        This method is called for every request and ensures that the service
        validation happens early in the request lifecycle.
        """
        # Only validate that service_class is defined, don't instantiate yet
        if self.service_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define a 'service_class' attribute. "
                f"Example: service_class = CampaignService"
            )
        return super().dispatch(request, *args, **kwargs)