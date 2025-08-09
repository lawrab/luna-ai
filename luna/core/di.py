"""
Dependency injection container for L.U.N.A.
"""
import asyncio
import inspect
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, Generic, Optional, Type, TypeVar, Union

from .types import Service, ServiceStatus
from .logging import get_logger


T = TypeVar('T')
logger = get_logger(__name__)


class Singleton:
    """Marker class for singleton services."""
    pass


class Container:
    """
    Simple dependency injection container with async support.
    """
    
    def __init__(self, name: str = "luna-container"):
        self.name = name
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._services: Dict[str, Service] = {}
        self._status = ServiceStatus.INITIALIZING
        self._lock = asyncio.Lock()
    
    def register_factory(self, interface: Type[T], factory: Callable[..., T]) -> None:
        """Register a factory function for an interface."""
        self._factories[interface] = factory
        logger.debug(f"Registered factory for {interface.__name__}")
    
    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Register a singleton instance."""
        self._singletons[interface] = instance
        logger.debug(f"Registered singleton for {interface.__name__}")
    
    def register_service(self, service: Service) -> None:
        """Register a service for lifecycle management."""
        self._services[service.name] = service
        logger.debug(f"Registered service: {service.name}")
    
    async def get(self, interface: Type[T]) -> T:
        """Get an instance of the requested interface."""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check if we have a cached instance
        if interface in self._instances:
            return self._instances[interface]
        
        # Check if we have a factory
        if interface not in self._factories:
            raise ValueError(f"No factory registered for {interface.__name__}")
        
        factory = self._factories[interface]
        
        # Create instance with dependency injection
        async with self._lock:
            # Double-check after acquiring lock
            if interface in self._instances:
                return self._instances[interface]
            
            instance = await self._create_instance(factory)
            
            # Cache the instance
            self._instances[interface] = instance
            
            # If it's a service, register it
            if isinstance(instance, Service):
                self._services[instance.name] = instance
            
            return instance
    
    async def _create_instance(self, factory: Callable) -> Any:
        """Create an instance using the factory with dependency injection."""
        sig = inspect.signature(factory)
        kwargs = {}
        
        # Resolve dependencies
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                # Skip 'self' parameter
                if param_name == 'self':
                    continue
                    
                try:
                    dependency = await self.get(param.annotation)
                    kwargs[param_name] = dependency
                except ValueError:
                    # Dependency not found, use default if available
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        logger.warning(f"Could not resolve dependency {param.annotation} for {factory}")
        
        # Call the factory
        if asyncio.iscoroutinefunction(factory):
            return await factory(**kwargs)
        else:
            return factory(**kwargs)
    
    async def start_all_services(self) -> None:
        """Start all registered services."""
        self._status = ServiceStatus.INITIALIZING
        logger.info("Starting all services...")
        
        for service_name, service in self._services.items():
            try:
                logger.debug(f"Starting service: {service_name}")
                await service.start()
                logger.debug(f"Service {service_name} started successfully")
            except Exception as e:
                logger.error(f"Failed to start service {service_name}: {e}")
                self._status = ServiceStatus.FAILED
                raise
        
        self._status = ServiceStatus.HEALTHY
        logger.info("All services started successfully")
    
    async def stop_all_services(self) -> None:
        """Stop all registered services."""
        logger.info("Stopping all services...")
        
        # Stop services in reverse order
        for service_name, service in reversed(list(self._services.items())):
            try:
                logger.debug(f"Stopping service: {service_name}")
                await service.stop()
                logger.debug(f"Service {service_name} stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping service {service_name}: {e}")
        
        self._status = ServiceStatus.SHUTDOWN
        logger.info("All services stopped")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        health_status = {}
        
        for service_name, service in self._services.items():
            try:
                health_status[service_name] = await service.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status[service_name] = False
        
        return health_status
    
    def clear(self) -> None:
        """Clear all registrations and cached instances."""
        self._factories.clear()
        self._instances.clear()
        self._singletons.clear()
        self._services.clear()
        logger.debug("Container cleared")
    
    @asynccontextmanager
    async def lifecycle(self) -> AsyncGenerator['Container', None]:
        """Context manager for container lifecycle."""
        try:
            await self.start_all_services()
            yield self
        finally:
            await self.stop_all_services()


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def register_factory(interface: Type[T], factory: Callable[..., T]) -> None:
    """Register a factory in the global container."""
    get_container().register_factory(interface, factory)


def register_singleton(interface: Type[T], instance: T) -> None:
    """Register a singleton in the global container."""
    get_container().register_singleton(interface, instance)


def register_service(service: Service) -> None:
    """Register a service in the global container."""
    get_container().register_service(service)


async def get_service(interface: Type[T]) -> T:
    """Get a service from the global container."""
    return await get_container().get(interface)


class Injectable:
    """
    Base class for injectable services.
    """
    
    def __init_subclass__(cls, singleton: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Auto-register the class
        if singleton:
            # Will be registered as singleton when first created
            cls._is_singleton = True
        else:
            register_factory(cls, cls)
        
        cls._is_singleton = singleton
    
    @classmethod
    async def create(cls) -> 'Injectable':
        """Factory method for creating instances through DI."""
        container = get_container()
        instance = await container.get(cls)
        
        # If marked as singleton, register it
        if hasattr(cls, '_is_singleton') and cls._is_singleton:
            container.register_singleton(cls, instance)
        
        return instance