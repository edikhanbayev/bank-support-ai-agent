import logging
import time

from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
)

from langgraph.checkpoint.postgres import (
    PostgresSaver,
)
from langgraph.types import Command

from app.agent import (
    build_agent,
    run_agent,
)
from app.api_dependencies import (
    get_customer_id,
)
from app.config import (
    CHECKPOINT_DB_URI,
)
from app.context import (
    AgentContext,
)
from app.message_utils import (
    extract_text,
)
from app.schemas import (
    ApprovalAction,
    ApprovalDecisionRequest,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from app.services import (
    ensure_thread_access,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Create one PostgreSQL-backed LangGraph
    checkpointer and one agent for the
    lifetime of the FastAPI application.
    """

    if not CHECKPOINT_DB_URI:
        raise RuntimeError(
            "CHECKPOINT_DB_URI is not configured."
        )

    logger.info(
        "Starting PostgreSQL LangGraph "
        "checkpointer."
    )

    with PostgresSaver.from_conn_string(
        CHECKPOINT_DB_URI
    ) as checkpointer:

        # Checkpoint tables are intentionally
        # initialized separately with:
        #
        # python -m app.setup_checkpointer

        app.state.agent = build_agent(
            checkpointer=checkpointer
        )

        logger.info(
            "Bank Support AI Agent initialized "
            "with PostgreSQL persistence."
        )

        yield

        logger.info(
            "Shutting down Bank Support AI Agent."
        )


app = FastAPI(
    title="Bank Support AI Agent",
    description=(
        "Stateful LLM bank support agent "
        "with tool calling, authorization "
        "and PostgreSQL-backed conversation "
        "state."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------


@app.middleware("http")
async def request_metrics_middleware(
    request: Request,
    call_next,
):
    """
    Measure request duration, expose it in a
    response header and write structured request
    information to the application log.
    """

    start = time.perf_counter()

    response = await call_next(
        request
    )

    duration_ms = (
        time.perf_counter() - start
    ) * 1000

    response.headers[
        "X-Process-Time-Ms"
    ] = f"{duration_ms:.2f}"

    logger.info(
        (
            "method=%s "
            "path=%s "
            "status=%s "
            "duration_ms=%.2f "
            "request_id=%s"
        ),
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        getattr(
            request.state,
            "request_id",
            "-",
        ),
    )

    return response


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next,
):
    """
    Add a request ID to every request.

    Reuse X-Request-ID when supplied.
    Otherwise generate a new identifier.
    """

    request_id = (
        request.headers.get(
            "X-Request-ID"
        )
        or
        f"req-{uuid4().hex[:12]}"
    )

    request.state.request_id = (
        request_id
    )

    response = await call_next(
        request
    )

    response.headers[
        "X-Request-ID"
    ] = request_id

    return response


# ---------------------------------------------------------
# Dependencies
# ---------------------------------------------------------


def get_agent(
    request: Request,
) -> Any:
    """
    Return the application-wide LangGraph agent.

    Keeping this as a FastAPI dependency makes
    it easy to replace during deterministic tests.
    """

    agent = getattr(
        request.app.state,
        "agent",
        None,
    )

    if agent is None:
        raise RuntimeError(
            "Agent is not initialized."
        )

    return agent


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def build_chat_response(
    result: Any,
    request_id: str,
    thread_id: str,
) -> ChatResponse:
    """
    Convert a LangGraph v2 result into our
    public API response.

    Handles both normal completion and HITL
    interrupts.
    """

    if result.interrupts:

        interrupt = (
            result.interrupts[0]
        )

        action_requests = (
            interrupt.value.get(
                "action_requests",
                [],
            )
        )

        if not action_requests:
            logger.error(
                (
                    "HITL interrupt contained "
                    "no action_requests "
                    "request_id=%s "
                    "thread_id=%s"
                ),
                request_id,
                thread_id,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid approval request "
                    "generated by agent."
                ),
            )

        action = (
            action_requests[0]
        )

        return ChatResponse(
            request_id=request_id,
            thread_id=thread_id,
            status="approval_required",
            response=None,
            approval=ApprovalAction(
                name=action["name"],
                arguments=action["args"],
                description=action.get(
                    "description"
                ),
            ),
        )

    messages = result.value.get(
        "messages",
        [],
    )

    if not messages:
        logger.error(
            (
                "Agent returned no messages "
                "request_id=%s "
                "thread_id=%s"
            ),
            request_id,
            thread_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Invalid response generated "
                "by agent."
            ),
        )

    response_text = extract_text(
        messages[-1]
    )

    return ChatResponse(
        request_id=request_id,
        thread_id=thread_id,
        status="completed",
        response=response_text,
        approval=None,
    )


def verify_thread_access(
    thread_id: str,
    customer_id: str,
    request_id: str,
) -> None:
    """
    Enforce authenticated ownership of a
    conversation thread.
    """

    try:

        ensure_thread_access(
            thread_id=thread_id,
            customer_id=customer_id,
        )

    except PermissionError:

        logger.warning(
            (
                "Thread access denied "
                "request_id=%s "
                "thread_id=%s "
                "customer_id=%s"
            ),
            request_id,
            thread_id,
            customer_id,
        )

        raise HTTPException(
            status_code=403,
            detail="Thread access denied.",
        )


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health():
    """
    Basic application liveness endpoint.
    """

    return HealthResponse(
        status="ok"
    )


# ---------------------------------------------------------
# Chat
# ---------------------------------------------------------


@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
)
def chat(
    request_body: ChatRequest,
    request: Request,
    customer_id: Annotated[
        str,
        Depends(get_customer_id),
    ],
    agent: Annotated[
        Any,
        Depends(get_agent),
    ],
):
    """
    Process one customer message through the
    persistent LangGraph agent.
    """

    request_id = (
        request.state.request_id
    )

    try:

        verify_thread_access(
            thread_id=(
                request_body.thread_id
            ),
            customer_id=customer_id,
            request_id=request_id,
        )

        result = run_agent(
            agent=agent,
            message=request_body.message,
            customer_id=customer_id,
            thread_id=(
                request_body.thread_id
            ),
        )

        return build_chat_response(
            result=result,
            request_id=request_id,
            thread_id=(
                request_body.thread_id
            ),
        )

    except HTTPException:
        raise

    except Exception:

        logger.exception(
            (
                "Agent request failed "
                "request_id=%s "
                "thread_id=%s"
            ),
            request_id,
            request_body.thread_id,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The support assistant is "
                "temporarily unavailable."
            ),
        )


# ---------------------------------------------------------
# HITL decision
# ---------------------------------------------------------


@app.post(
    "/api/v1/threads/{thread_id}/decision",
    response_model=ChatResponse,
)
def review_action(
    thread_id: str,
    decision_body:
        ApprovalDecisionRequest,
    request: Request,
    customer_id: Annotated[
        str,
        Depends(get_customer_id),
    ],
    agent: Annotated[
        Any,
        Depends(get_agent),
    ],
):
    """
    Approve or reject an interrupted
    human-in-the-loop action.
    """

    request_id = (
        request.state.request_id
    )

    try:

        verify_thread_access(
            thread_id=thread_id,
            customer_id=customer_id,
            request_id=request_id,
        )

        config = {
            "configurable": {
                "thread_id":
                    thread_id
            }
        }

        decision = {
            "type":
                decision_body.decision
        }

        if (
            decision_body.decision
            == "reject"
        ):

            decision["message"] = (
                decision_body.message
                or
                "User rejected this action."
            )

        result = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        decision
                    ]
                }
            ),
            config=config,
            context=AgentContext(
                customer_id=customer_id
            ),
            version="v2",
        )

        return build_chat_response(
            result=result,
            request_id=request_id,
            thread_id=thread_id,
        )

    except HTTPException:
        raise

    except Exception:

        logger.exception(
            (
                "HITL decision failed "
                "request_id=%s "
                "thread_id=%s"
            ),
            request_id,
            thread_id,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "The support assistant is "
                "temporarily unavailable."
            ),
        )