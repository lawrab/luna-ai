"""
Tests for the async event bus system.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from luna.core.events import AsyncEventBus
from luna.core.types import Event, SystemEvent, ServiceStatus


@pytest.mark.asyncio
class TestAsyncEventBus:
    """Test the AsyncEventBus implementation."""
    
    async def test_start_stop(self):
        """Test event bus lifecycle."""
        bus = AsyncEventBus("test-bus")
        
        assert bus.status == ServiceStatus.INITIALIZING
        
        await bus.start()
        assert bus.status == ServiceStatus.HEALTHY
        
        await bus.stop()
        assert bus.status == ServiceStatus.SHUTDOWN
    
    async def test_subscribe_and_publish(self, event_bus):
        """Test basic subscription and publishing."""
        events_received = []
        
        def handler(event):
            events_received.append(event)
        
        # Subscribe to events
        sub_id = event_bus.subscribe("test_event", handler)
        assert isinstance(sub_id, str)
        
        # Publish event
        test_event = Event(type="test_event", payload={"message": "hello"})
        await event_bus.publish(test_event)
        
        # Give handlers time to execute
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].type == "test_event"
        assert events_received[0].payload["message"] == "hello"
    
    async def test_async_handler(self, event_bus):
        """Test async event handlers."""
        events_received = []
        
        async def async_handler(event):
            await asyncio.sleep(0.01)  # Simulate async work
            events_received.append(event)
        
        event_bus.subscribe("async_test", async_handler)
        
        test_event = Event(type="async_test", payload={"data": "async"})
        await event_bus.publish(test_event)
        
        # Give async handler time to complete
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].payload["data"] == "async"
    
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers to same event."""
        handler1_calls = []
        handler2_calls = []
        
        def handler1(event):
            handler1_calls.append(event)
        
        def handler2(event):
            handler2_calls.append(event)
        
        event_bus.subscribe("multi_test", handler1)
        event_bus.subscribe("multi_test", handler2)
        
        test_event = Event(type="multi_test", payload={"count": 1})
        await event_bus.publish(test_event)
        
        await asyncio.sleep(0.1)
        
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
    
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        events_received = []
        
        def handler(event):
            events_received.append(event)
        
        sub_id = event_bus.subscribe("unsub_test", handler)
        
        # Publish first event
        await event_bus.publish(Event(type="unsub_test", payload={"num": 1}))
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        
        # Unsubscribe
        event_bus.unsubscribe(sub_id)
        
        # Publish second event - should not be received
        await event_bus.publish(Event(type="unsub_test", payload={"num": 2}))
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1  # Still only 1
    
    async def test_wait_for_event(self, event_bus):
        """Test waiting for specific events."""
        # Start waiting in background
        wait_task = asyncio.create_task(
            event_bus.wait_for_event("wait_test", timeout=1.0)
        )
        
        # Give wait a moment to set up
        await asyncio.sleep(0.01)
        
        # Publish the event
        test_event = Event(type="wait_test", payload={"waited": True})
        await event_bus.publish(test_event)
        
        # Wait should complete
        received_event = await wait_task
        assert received_event is not None
        assert received_event.type == "wait_test"
        assert received_event.payload["waited"] is True
    
    async def test_wait_for_event_timeout(self, event_bus):
        """Test timeout when waiting for events."""
        # Wait for event that never comes
        received_event = await event_bus.wait_for_event("never_comes", timeout=0.1)
        assert received_event is None
    
    async def test_handler_error_isolation(self, event_bus):
        """Test that errors in handlers don't affect other handlers."""
        good_handler_calls = []
        
        def bad_handler(event):
            raise ValueError("Handler error")
        
        def good_handler(event):
            good_handler_calls.append(event)
        
        event_bus.subscribe("error_test", bad_handler)
        event_bus.subscribe("error_test", good_handler)
        
        # Publish event - bad handler should error but good handler should still run
        await event_bus.publish(Event(type="error_test", payload={"test": True}))
        await asyncio.sleep(0.1)
        
        # Good handler should have received the event
        assert len(good_handler_calls) == 1
    
    async def test_subscription_count(self, event_bus):
        """Test subscription counting."""
        assert event_bus.get_subscription_count() == 0
        assert event_bus.get_subscription_count("specific_event") == 0
        
        def handler1(event):
            pass
        
        def handler2(event):
            pass
        
        sub1 = event_bus.subscribe("event1", handler1)
        sub2 = event_bus.subscribe("event1", handler2)
        sub3 = event_bus.subscribe("event2", handler1)
        
        assert event_bus.get_subscription_count() == 3
        assert event_bus.get_subscription_count("event1") == 2
        assert event_bus.get_subscription_count("event2") == 1
        
        event_bus.unsubscribe(sub1)
        assert event_bus.get_subscription_count("event1") == 1
    
    async def test_temporary_subscription(self, event_bus):
        """Test context manager for temporary subscriptions."""
        events_received = []
        
        def handler(event):
            events_received.append(event)
        
        async with event_bus.temporary_subscription("temp_test", handler):
            await event_bus.publish(Event(type="temp_test", payload={"inside": True}))
            await asyncio.sleep(0.1)
        
        # After context exit, handler should be unsubscribed
        await event_bus.publish(Event(type="temp_test", payload={"outside": True}))
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].payload["inside"] is True
    
    async def test_graceful_shutdown_cancels_handlers(self):
        """Test that shutdown cancels running handlers."""
        bus = AsyncEventBus("shutdown-test")
        await bus.start()
        
        handler_started = asyncio.Event()
        handler_cancelled = False
        
        async def slow_handler(event):
            nonlocal handler_cancelled
            handler_started.set()
            try:
                await asyncio.sleep(10)  # Long-running handler
            except asyncio.CancelledError:
                handler_cancelled = True
                raise
        
        bus.subscribe("slow_event", slow_handler)
        
        # Publish event that starts slow handler
        await bus.publish(Event(type="slow_event"))
        
        # Wait for handler to start
        await handler_started.wait()
        
        # Stop bus - should cancel handler
        await bus.stop()
        
        # Give a moment for cancellation to propagate
        await asyncio.sleep(0.1)
        
        assert handler_cancelled is True