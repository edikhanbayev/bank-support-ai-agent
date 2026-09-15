import json
import logging

from langchain.tools import ToolRuntime, tool

from app.context import AgentContext
from app.policies import search_policies
from app.services import (
    create_ticket,
    find_customer,
    find_transaction_for_customer
)

logger = logging.getLogger(__name__)

def as_json(data: dict | list) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        default=str
    )


@tool
def get_customer(
    runtime: ToolRuntime[AgentContext]
) -> str:
    """
    Retrieve profile information for the currently
    authenticated bank customer.

    Use this tool when customer profile information
    is required.

    Never use it to retrieve another customer's data.
    """

    try:
        customer_id = runtime.context.customer_id

        customer = find_customer(
            customer_id
        )

        if customer is None:
            return as_json({
                "ok": False,
                "error": "customer_not_found"
            })

        return as_json({
            "ok": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "account_type": customer.account_type
            }
        })

    except Exception:
        logger.exception(
            "get_customer failed"
        )

        return as_json({
            "ok": False,
            "error": "internal_error"
        })


@tool
def get_transaction(
    transaction_id: str,
    runtime: ToolRuntime[AgentContext]
) -> str:
    """
    Retrieve a transaction belonging to the currently
    authenticated customer.

    Args:
        transaction_id:
            Bank transaction identifier such as
            TXN-1001.

    Never expose transactions belonging to another
    customer.
    """

    try:
        customer_id = runtime.context.customer_id

        transaction = (
            find_transaction_for_customer(
                transaction_id,
                customer_id
            )
        )

        if transaction is None:
            return as_json({
                "ok": False,
                "error":
                    "transaction_not_found_or_not_accessible"
            })

        return as_json({
            "ok": True,
            "transaction": {
                "id": transaction.id,
                "merchant": transaction.merchant,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "status": transaction.status,
                "created_at": transaction.created_at
            }
        })

    except Exception:
        logger.exception(
            "get_transaction failed"
        )

        return as_json({
            "ok": False,
            "error": "internal_error"
        })


@tool
def search_policy(
    query: str
) -> str:
    """
    Search the demo bank support policies.

    Use this tool when the customer asks about
    refunds, disputes, pending transactions,
    unrecognized transactions or support procedures.

    Args:
        query:
            Description of the policy topic to search.
    """

    try:
        policies = search_policies(query)

        if not policies:
            return as_json({
                "ok": True,
                "policies": []
            })

        return as_json({
            "ok": True,
            "policies": policies
        })

    except Exception:
        logger.exception(
            "search_policy failed"
        )

        return as_json({
            "ok": False,
            "error": "internal_error"
        })


@tool
def create_support_ticket(
    category: str,
    description: str,
    transaction_id: str | None,
    runtime: ToolRuntime[AgentContext]
) -> str:
    """
    Create a support ticket for the currently
    authenticated customer.

    Use only when the customer explicitly requests
    support escalation or opening a support case.

    If transaction_id is provided, verify the
    transaction with get_transaction before calling
    this tool.

    Args:
        category:
            Short ticket category.

        description:
            Concise description of the customer's
            problem.

        transaction_id:
            Related transaction ID, or null when
            the issue is not related to a transaction.
    """

    try:
        customer_id = runtime.context.customer_id

        ticket = create_ticket(
            customer_id=customer_id,
            transaction_id=transaction_id,
            category=category,
            description=description
        )

        return as_json({
            "ok": True,
            "ticket": {
                "id": ticket.id,
                "status": ticket.status,
                "category": ticket.category,
                "transaction_id":
                    ticket.transaction_id
            }
        })

    except ValueError as exc:

        return as_json({
            "ok": False,
            "error": str(exc)
        })

    except Exception:

        logger.exception(
            "create_support_ticket failed"
        )

        return as_json({
            "ok": False,
            "error": "internal_error"
        })