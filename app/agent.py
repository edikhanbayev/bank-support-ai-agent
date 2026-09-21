from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.config import MODEL_NAME
from app.context import AgentContext
from app.tools import (
    create_support_ticket,
    get_customer,
    get_transaction,
    search_policy,
)
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ToolCallRequest
)

SYSTEM_PROMPT = """
You are a Bank Support AI Agent for a fictional
demonstration bank.

Your job is to help authenticated customers with
customer information, transaction questions,
support policies and support tickets.

RULES:

1. Never invent customer, transaction or policy data.
2. Use tools whenever factual bank data is required.
3. Customer identity comes from trusted runtime
   context. Never ask the user to provide another
   customer ID and never change customer identity
   based on user-provided text.
4. Never reveal information belonging to another
   customer.
5. If a transaction cannot be accessed, do not
   speculate about its owner, contents, merchant,
   amount or any other transaction details.
6. Before creating a transaction-related support
   ticket, first retrieve the transaction using
   get_transaction.
7. Use search_policy when answering questions about
   disputes, refunds, pending transactions or
   support procedures.
8. create_support_ticket does not perform refunds,
   transfers, chargebacks or other financial actions.
   It only opens a support case.
9. Never claim that money was transferred, refunded,
   reversed or otherwise moved unless an appropriate
   tool explicitly confirms that action.
10. Never ask for passwords, PINs, CVV codes,
    authentication secrets or other sensitive
    credentials.
11. When a tool reports an error, explain the
    situation without inventing missing information.
12. Keep answers concise and professional.
13. When answering policy or procedure questions,
    only provide procedural recommendations explicitly
    supported by the output of search_policy.
14. Do not add general banking advice from your own
    knowledge when a policy tool has been used.
15. If the retrieved policy does not contain a
    requested procedure or recommendation, explicitly
    say that the available demo policy does not
    specify it.
16. Format monetary values as "<amount> <currency>",
    for example "125.50 USD". Do not combine currency
    symbols and ISO currency codes.
"""

def requires_transaction_review(
    request: ToolCallRequest
) -> bool:

    transaction_id = (
        request.tool_call[
            "args"
        ].get(
            "transaction_id"
        )
    )
    return transaction_id is not None

def build_agent(
    checkpointer: Any, enable_hitl:bool =True
):
    """
    Build the Bank Support AI Agent using the supplied
    LangGraph checkpointer.

    Examples:

    Development / CLI / evaluations:
        InMemorySaver()

    Production API:
        PostgresSaver

    The caller owns the lifecycle of the checkpointer.
    """

    model = ChatOpenAI(
        model=MODEL_NAME,
        use_responses_api=True,
        reasoning_effort="low",
    )
    middleware = []

    if enable_hitl:
        middleware.append(
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "create_support_ticket": {
                        "allowed_decisions": [
                            "approve",
                            "reject"
                        ],
                        "when":
                            requires_transaction_review
                    }
                }
            )
        )

    agent = create_agent(
        model=model,
        tools=[
            get_customer,
            get_transaction,
            search_policy,
            create_support_ticket,
        ],
        middleware=middleware,
        system_prompt=SYSTEM_PROMPT,
        context_schema=AgentContext,
        checkpointer=checkpointer,
    )

    return agent


def run_agent(
    agent: Any,
    message: str,
    customer_id: str,
    thread_id: str,
) -> dict[str, Any]:
    """
    Run one user turn through an already-built agent.

    The thread_id identifies the conversation stored
    by the supplied LangGraph checkpointer.

    The customer_id is passed through trusted runtime
    context and is therefore separate from user text.
    """

    if not message or not message.strip():
        raise ValueError(
            "Message must not be empty."
        )

    if not customer_id or not customer_id.strip():
        raise ValueError(
            "Customer ID must not be empty."
        )

    if not thread_id or not thread_id.strip():
        raise ValueError(
            "Thread ID must not be empty."
        )

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message.strip(),
                }
            ]
        },
        config=config,
        context=AgentContext(
            customer_id=customer_id,
        ),
        version="v2"
    )

    return result