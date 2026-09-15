import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from app.config import MODEL_NAME
from app.context import AgentContext
from app.tools import (
    create_support_ticket,
    get_customer,
    get_transaction,
    search_policy
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
   customer ID.
4. Never reveal information belonging to another
   customer.
5. If a transaction cannot be accessed, do not
   speculate about its owner or contents.
6. Before creating a transaction-related support
   ticket, first retrieve the transaction using
   get_transaction.
7. Use search_policy when answering questions about
   disputes, refunds, pending transactions or
   procedures.
8. create_support_ticket does not perform refunds,
   transfers, chargebacks or other financial actions.
   It only opens a support case.
9. Never claim that money was transferred, refunded
   or reversed unless an appropriate tool explicitly
   confirms it.
10. Never ask for passwords, PINs, CVV codes or
    authentication secrets.
11. When a tool reports an error, explain the
    situation without inventing missing information.
12. Keep answers concise and professional.
13. When answering policy or procedure questions,
    only provide procedural recommendations explicitly
    supported by the output of search_policy.
14. Do not add general banking advice from your own
    knowledge when a policy tool has been used.
15. If the retrieved policy does not contain a requested
    procedure or recommendation, explicitly say that the
    available demo policy does not specify it.
16. Format monetary values as "<amount> <currency>",
    for example "125.50 USD". Do not combine currency
    symbols with ISO currency codes.
"""

model = ChatOpenAI(
    model=MODEL_NAME,
    use_responses_api=True,
    reasoning_effort="low"
)

checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=[
        get_customer,
        get_transaction,
        search_policy,
        create_support_ticket
    ],
    system_prompt=SYSTEM_PROMPT,
    context_schema=AgentContext,
    checkpointer=checkpointer
)

def run_agent(
    message: str,
    customer_id: str,
    thread_id: str
):

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        },
        config=config,
        context=AgentContext(
            customer_id=customer_id
        )
    )

    return result