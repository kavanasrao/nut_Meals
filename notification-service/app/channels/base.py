from abc import ABC, abstractmethod

from app.models.message import Message


class ChannelSendError(Exception):
    """Raised by a channel adapter when a send attempt fails."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class BaseChannel(ABC):
    """Common interface every messaging channel adapter must implement."""

    name: str = "base"

    @abstractmethod
    async def send(self, message: Message) -> dict:
        """
        Attempt to deliver `message`. Must raise ChannelSendError on
        failure (retryable=False for permanent failures like invalid
        recipient, so the retry engine can dead-letter immediately).
        Returns a provider response dict on success.
        """
        raise NotImplementedError
