from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable, Deque, Dict, List, Protocol, Any


class MessageHandler(Protocol):
    def __call__(self, topic: str, message: Dict[str, Any]) -> None:
        ...


class MessageBus:
    """Simple in-memory publish/subscribe bus for agent coordination."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[MessageHandler]] = defaultdict(list)
        self._history: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=50))

    def subscribe(self, topic: str, handler: MessageHandler) -> None:
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: MessageHandler) -> None:
        if handler in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(handler)

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        self._history[topic].append(message)
        for handler in list(self._subscribers.get(topic, [])):
            handler(topic, message)

    def history(self, topic: str) -> List[Dict[str, Any]]:
        return list(self._history.get(topic, []))


message_bus = MessageBus()
