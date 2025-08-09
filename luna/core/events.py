"""
Modern async event bus implementation with proper error handling and observability.
"""
import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set
from weakref import WeakSet

from .types import Event, EventBus, EventHandler, CorrelationId, ServiceStatus


logger = logging.getLogger(__name__)


class AsyncEventBus:
    """
    Production-ready async event bus with proper error handling,
    subscription management, and observability.
    """
    
    def __init__(self, name: str = "luna-event-bus"):
        self.name = name
        self._subscriptions: Dict[str, Dict[str, EventHandler]] = defaultdict(dict)
        self._event_flags: Dict[str, asyncio.Event] = {}
        self._last_events: Dict[str, Event] = {}
        self._status = ServiceStatus.INITIALIZING
        self._running_tasks: WeakSet = WeakSet()
        self._lock = asyncio.Lock()
        
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    async def start(self) -> None:
        """Start the event bus."""
        self._status = ServiceStatus.HEALTHY
        logger.info(f"Event bus '{self.name}' started")
        
    async def stop(self) -> None:
        """Stop the event bus gracefully."""
        self._status = ServiceStatus.SHUTDOWN
        
        # Cancel all running tasks
        for task in list(self._running_tasks):
            if not task.done():
                task.cancel()
                
        # Wait for all tasks to complete or be cancelled
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            
        # Clear all subscriptions and events
        self._subscriptions.clear()
        self._event_flags.clear()
        self._last_events.clear()
        
        logger.info(f"Event bus '{self.name}' stopped")
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        Errors in handlers don't affect other handlers or the publisher.
        """
        if self._status != ServiceStatus.HEALTHY:
            logger.warning(f"Event bus not healthy, dropping event: {event.type}")
            return
            
        async with self._lock:
            self._last_events[event.type] = event
            
            # Set event flag for wait_for_event
            if event.type in self._event_flags:
                self._event_flags[event.type].set()
        
        # Get subscribers for this event type
        subscribers = self._subscriptions.get(event.type, {})
        if not subscribers:
            logger.debug(f"No subscribers for event type: {event.type}")
            return
            
        logger.debug(f"Publishing event {event.type} to {len(subscribers)} subscribers")
        
        # Execute all handlers concurrently
        tasks = []
        for sub_id, handler in subscribers.items():
            task = asyncio.create_task(
                self._execute_handler_safely(handler, event, sub_id),
                name=f"event-handler-{event.type}-{sub_id[:8]}"
            )
            tasks.append(task)
            self._running_tasks.add(task)
        
        if tasks:
            # Don't wait for handlers to complete - fire and forget
            # But track them for graceful shutdown
            pass
    
    async def _execute_handler_safely(self, handler: EventHandler, event: Event, sub_id: str) -> None:
        """Execute an event handler with proper error handling."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync handler in thread pool to avoid blocking
                await asyncio.to_thread(handler, event)
                
        except asyncio.CancelledError:
            # Handler was cancelled during shutdown
            pass
        except Exception as e:
            logger.error(
                f"Error in event handler {sub_id} for event {event.type}: {e}",
                extra={
                    "event_type": event.type,
                    "event_id": str(event.id),
                    "subscription_id": sub_id,
                    "correlation_id": event.correlation_id.value if event.correlation_id else None,
                },
                exc_info=True
            )
    
    def subscribe(self, event_type: str, handler: EventHandler) -> str:
        """Subscribe to events of a specific type."""
        import uuid
        subscription_id = str(uuid.uuid4())
        
        self._subscriptions[event_type][subscription_id] = handler
        
        logger.debug(f"Subscribed to {event_type} with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription."""
        for event_type, subs in self._subscriptions.items():
            if subscription_id in subs:
                del subs[subscription_id]
                logger.debug(f"Unsubscribed {subscription_id} from {event_type}")
                return
                
        logger.warning(f"Subscription ID {subscription_id} not found")
    
    async def wait_for_event(self, event_type: str, timeout: Optional[float] = None) -> Optional[Event]:
        """Wait for a specific event type to be published."""
        if self._status != ServiceStatus.HEALTHY:
            return None
            
        # Create or get event flag
        if event_type not in self._event_flags:
            self._event_flags[event_type] = asyncio.Event()
        
        event_flag = self._event_flags[event_type]
        event_flag.clear()  # Ensure we wait for a new event
        
        try:
            await asyncio.wait_for(event_flag.wait(), timeout=timeout)
            
            # Return the last event of this type
            async with self._lock:
                return self._last_events.get(event_type)
                
        except asyncio.TimeoutError:
            return None
    
    def get_subscription_count(self, event_type: Optional[str] = None) -> int:
        """Get number of subscriptions (for monitoring/debugging)."""
        if event_type:
            return len(self._subscriptions.get(event_type, {}))
        return sum(len(subs) for subs in self._subscriptions.values())
    
    @asynccontextmanager
    async def temporary_subscription(self, event_type: str, handler: EventHandler):
        """Context manager for temporary subscriptions."""
        sub_id = self.subscribe(event_type, handler)
        try:
            yield sub_id
        finally:
            self.unsubscribe(sub_id)


# Global event bus instance
_event_bus: Optional[AsyncEventBus] = None


def get_event_bus() -> AsyncEventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = AsyncEventBus()
    return _event_bus


async def initialize_event_bus() -> AsyncEventBus:
    """Initialize and start the global event bus."""
    bus = get_event_bus()
    await bus.start()
    return bus


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus."""
    global _event_bus
    if _event_bus is not None:
        await _event_bus.stop()
        _event_bus = None