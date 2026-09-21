from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Customer, Transaction


def seed_database():


    with SessionLocal() as session:

        existing_customer = session.scalar(
            select(Customer).where(
                Customer.id == "CUST-001"
            )
        )

        if existing_customer:
            print("Database already seeded.")
            return

        customers = [
            Customer(
                id="CUST-001",
                name="Alex Morgan",
                email="alex@example.com",
                account_type="Premium"
            ),
            Customer(
                id="CUST-002",
                name="Maria Lee",
                email="maria@example.com",
                account_type="Standard"
            )
        ]

        transactions = [
            Transaction(
                id="TXN-1001",
                customer_id="CUST-001",
                merchant="FreshMart",
                amount=Decimal("125.50"),
                currency="USD",
                status="posted",
                created_at=datetime(
                    2026,
                    9,
                    10,
                    12,
                    30
                )
            ),
            Transaction(
                id="TXN-1002",
                customer_id="CUST-001",
                merchant="TechStore",
                amount=Decimal("899.00"),
                currency="USD",
                status="pending",
                created_at=datetime(
                    2026,
                    9,
                    14,
                    17,
                    15
                )
            ),
            Transaction(
                id="TXN-2001",
                customer_id="CUST-002",
                merchant="AirTravel",
                amount=Decimal("540.00"),
                currency="USD",
                status="posted",
                created_at=datetime(
                    2026,
                    9,
                    12,
                    8,
                    0
                )
            )
        ]

        session.add_all(customers)
        session.add_all(transactions)

        session.commit()

        print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()