from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    merchant: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )