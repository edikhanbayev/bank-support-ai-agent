from langgraph.checkpoint.postgres import (
    PostgresSaver
)

from app.config import (
    CHECKPOINT_DB_URI
)


def setup():

    if not CHECKPOINT_DB_URI:
        raise RuntimeError(
            "CHECKPOINT_DB_URI is not configured."
        )

    with PostgresSaver.from_conn_string(
        CHECKPOINT_DB_URI
    ) as checkpointer:

        checkpointer.setup()

    print(
        "LangGraph checkpoint tables ready."
    )


if __name__ == "__main__":
    setup()