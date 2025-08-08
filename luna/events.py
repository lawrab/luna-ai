# luna/events.py
"""
Implements a simple publish-subscribe event bus for decoupling components.
"""
from typing import Callable, Dict, List
import asyncio

# A dictionary to hold our event subscribers
_subscribers: Dict[str, List[Callable]] = {}
_event_flags: Dict[str, asyncio.Event] = {}

def subscribe(event_type: str, fn: Callable):
    """Adds a function to the subscriber list for a given event type."""
    if event_type not in _subscribers:
        _subscribers[event_type] = []
    _subscribers[event_type].append(fn)

def publish(event_type: str, *args, **kwargs):
    """Calls all functions subscribed to a given event type."""
    if event_type in _subscribers:
        for fn in _subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(fn):
                    # For async functions, try to create a task if event loop is running
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(fn(*args, **kwargs))
                    except RuntimeError:
                        # No event loop running - skip async functions during shutdown
                        pass
                else:
                    # For sync functions, call directly
                    fn(*args, **kwargs)
            except Exception as e:
                # Don't let subscriber errors break the publisher
                print(f"Error in event subscriber for {event_type}: {e}")
    if event_type in _event_flags:
        try:
            _event_flags[event_type].set()
        except RuntimeError:
            # Event loop might be closed during shutdown
            pass

async def wait_for_event(event_type: str, timeout: float | None = None) -> bool:
    """Waits for a specific event to be published asynchronously.

    Args:
        event_type: The type of event to wait for.
        timeout: The maximum time to wait in seconds. If None, waits indefinitely.

    Returns:
        True if the event was published, False if the timeout occurred.
    """
    if event_type not in _event_flags:
        _event_flags[event_type] = asyncio.Event()
    
    # Clear the flag before waiting to ensure we wait for a *new* event
    _event_flags[event_type].clear()
    try:
        await asyncio.wait_for(_event_flags[event_type].wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False

