from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Customer, SupportTicket, Transaction, ConversationThread


def find_customer( customer_id: str) -> Customer | None:
    with SessionLocal() as session:
        return session.get(
            Customer,
            customer_id
        )

def find_transaction_for_customer( transaction_id: str, customer_id: str) -> Transaction | None:
    with SessionLocal() as session:
        statement = (
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.customer_id == customer_id
            )
        )
        return session.scalar(statement)

def create_ticket( customer_id: str, transaction_id: str | None, category: str, description: str
) -> SupportTicket:

    with SessionLocal() as session:
        if transaction_id:
            transaction = session.scalar(
                select(Transaction).where(
                    Transaction.id == transaction_id,
                    Transaction.customer_id == customer_id
                )
            )
            if transaction is None:
                raise ValueError(
                    "Transaction does not exist "
                    "or does not belong to customer."
                )

        ticket = SupportTicket(
            id=f"TICKET-{uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            transaction_id=transaction_id,
            category=category,
            description=description,
            status="open",
            created_at=datetime.now(
                timezone.utc
            ).replace(tzinfo=None)
        )

        session.add(ticket)
        session.commit()
        session.refresh(ticket)

        return ticket

def ensure_thread_access(
    thread_id: str,
    customer_id: str,
) -> None:
    """
    Ensure a conversation thread belongs to
    the authenticated customer.

    If the thread does not exist, ownership
    is created for the current customer.

    If it belongs to another customer,
    access is rejected.
    """

    with SessionLocal() as session:

        thread = session.get(
            ConversationThread,
            thread_id,
        )

        if thread is None:

            session.add(
                ConversationThread(
                    id=thread_id,
                    customer_id=customer_id,
                )
            )

            session.commit()

            return

        if (
            thread.customer_id
            != customer_id
        ):
            raise PermissionError(
                "Thread does not belong to "
                "authenticated customer."
            )