from uuid import UUID

from app.models.customer_note import CustomerNote
from app.repositories.customer_note_repository import (
    CustomerNoteRepository,
)
from app.schemas.customer_note import (
    CustomerNoteCreate,
    CustomerNoteUpdate,
)


class CustomerNoteService:
    def __init__(
        self,
        repository: CustomerNoteRepository,
    ) -> None:
        self.repository = repository

    async def create_note(
        self,
        data: CustomerNoteCreate,
    ) -> CustomerNote:
        note = CustomerNote(**data.model_dump())
        return await self.repository.create(note)

    async def get_note(
        self,
        note_id: UUID,
    ) -> CustomerNote | None:
        return await self.repository.get_by_id(note_id)

    async def get_customer_notes(
        self,
        customer_id: UUID,
    ) -> list[CustomerNote]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_internal_notes(
        self,
        customer_id: UUID,
    ) -> list[CustomerNote]:
        return await self.repository.get_internal_notes(customer_id)

    async def get_notes_by_author(
        self,
        author_id: UUID,
    ) -> list[CustomerNote]:
        return await self.repository.get_by_author(author_id)

    async def update_note(
        self,
        note_id: UUID,
        data: CustomerNoteUpdate,
    ) -> CustomerNote | None:
        note = await self.repository.get_by_id(note_id)

        if note is None:
            return None

        return await self.repository.update(
            note,
            data.model_dump(exclude_unset=True),
        )

    async def delete_note(
        self,
        note_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(note_id)