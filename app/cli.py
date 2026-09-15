from uuid import uuid4

from app.agent import run_agent
from app.message_utils import (
    extract_text,
    extract_tool_calls
)


def main():

    customer_id = "CUST-001"
    thread_id = str(uuid4())

    last_message_count = 0

    print("Bank Support AI Agent")
    print(f"Customer: {customer_id}")
    print(f"Thread: {thread_id}")
    print("Type 'exit' to stop.\n")

    while True:

        message = input(
            "You: "
        ).strip()

        if message.lower() == "exit":
            break

        result = run_agent(
            message=message,
            customer_id=customer_id,
            thread_id=thread_id
        )

        messages = result["messages"]

        new_messages = messages[
            last_message_count:
        ]

        extract_tool_calls(new_messages)

        last_message_count = len(
            messages
        )

        response = extract_text(
            messages[-1]
        )

        print(
            f"\nAgent: {response}\n"
        )

if __name__ == "__main__":
    main()