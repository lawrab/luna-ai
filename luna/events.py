# luna/events.py
"""
Implements a simple publish-subscribe event bus for decoupling components.
"""
from typing import Callable, Dict, List
import threading

# A dictionary to hold our event subscribers
_subscribers: Dict[str, List[Callable]] = {}
_event_flags: Dict[str, threading.Event] = {}

def subscribe(event_type: str, fn: Callable):
    """Adds a function to the subscriber list for a given event type."""
    if event_type not in _subscribers:
        _subscribers[event_type] = []
    _subscribers[event_type].append(fn)

def publish(event_type: str, *args, **kwargs):
    """Calls all functions subscribed to a given event type."""
    if event_type in _subscribers:
        for fn in _subscribers[event_type]:
            fn(*args, **kwargs)
    if event_type in _event_flags:
        _event_flags[event_type].set()

def wait_for_event(event_type: str, timeout: float | None = None) -> bool:
    """Waits for a specific event to be published.

    Args:
        event_type: The type of event to wait for.
        timeout: The maximum time to wait in seconds. If None, waits indefinitely.

    Returns:
        True if the event was published, False if the timeout occurred.
    """
    if event_type not in _event_flags:
        _event_flags[event_type] = threading.Event()
    
    # Clear the flag before waiting to ensure we wait for a *new* event
    _event_flags[event_type].clear()
    return _event_flags[event_type].wait(timeout=timeout)
