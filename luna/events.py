# luna/events.py
"""
Implements a simple publish-subscribe event bus for decoupling components.
"""
from typing import Callable, Dict, List

# A dictionary to hold our event subscribers
_subscribers: Dict[str, List[Callable]] = {}

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
