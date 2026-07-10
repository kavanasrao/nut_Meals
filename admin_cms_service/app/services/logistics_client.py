"""Client for the upstream Logistics service."""
import uuid

from app.config import get_settings
from app.services.base_client import BaseServiceClient

settings = get_settings()


class LogisticsServiceClient(BaseServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.logistics_service_url)

    async def schedule_return_pickup(self, order_id: uuid.UUID, return_request_id: uuid.UUID) -> dict:
        """Ask Logistics to schedule a reverse-logistics pickup for an approved return."""
        return await self.post(
            "/internal/v1/pickups",
            json={"order_id": str(order_id), "return_request_id": str(return_request_id)},
        )

    async def get_shipment_status(self, logistics_reference: str) -> dict:
        return await self.get(f"/internal/v1/shipments/{logistics_reference}")


def get_logistics_client() -> LogisticsServiceClient:
    return LogisticsServiceClient()
