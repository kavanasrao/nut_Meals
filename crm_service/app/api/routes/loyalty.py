from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.loyalty_repository import LoyaltyRepository
from app.schema.loyalty_transaction import (
    LoyaltyTransactionCreate,
    LoyaltyTransactionResponse,
    LoyaltyTransactionUpdate,
)
from app.services.loyalty_service import LoyaltyService

router = APIRouter(
    prefix="/loyalty",
    tags=["Loyalty"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> LoyaltyService:
    repository = LoyaltyRepository(db)
    return LoyaltyService(repository)


@router.post(
    "/",
    response_model=LoyaltyTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: LoyaltyTransactionCreate,
    service: LoyaltyService = Depends(get_service),
):
    return await service.create_transaction(payload)


@router.get(
    "/{transaction_id}",
    response_model=LoyaltyTransactionResponse,
)
async def get_transaction(
    transaction_id: UUID,
    service: LoyaltyService = Depends(get_service),
):
    transaction = await service.get_transaction(transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction


@router.get("/customer/{customer_id}")
async def get_customer_transactions(
    customer_id: UUID,
    service: LoyaltyService = Depends(get_service),
):
    return await service.get_customer_transactions(customer_id)


@router.get("/customer/{customer_id}/balance")
async def get_balance(
    customer_id: UUID,
    service: LoyaltyService = Depends(get_service),
):
    return {
        "customer_id": customer_id,
        "balance": await service.get_current_balance(customer_id),
    }


@router.put(
    "/{transaction_id}",
    response_model=LoyaltyTransactionResponse,
)
async def update_transaction(
    transaction_id: UUID,
    payload: LoyaltyTransactionUpdate,
    service: LoyaltyService = Depends(get_service),
):
    transaction = await service.update_transaction(
        transaction_id,
        payload,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: UUID,
    service: LoyaltyService = Depends(get_service),
):
    deleted = await service.delete_transaction(transaction_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return {
        "message": "Transaction deleted successfully",
    }