from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api as api_module

from app.api import (
    app,
    get_agent,
)

from app.api_dependencies import (
    get_customer_id,
)


FAKE_AGENT = object()

TIMING_HEADER = "X-Process-Time-Ms"


client = TestClient(app)


def completed_result(
    text: str,
):
    """
    Simulate a LangGraph v2 completed result.
    """

    return SimpleNamespace(
        value={
            "messages": [
                SimpleNamespace(
                    content=text
                )
            ]
        },
        interrupts=[],
    )


def approval_required_result():
    """
    Simulate a LangGraph HITL interrupt.
    """

    interrupt = SimpleNamespace(
        value={
            "action_requests": [
                {
                    "name":
                        "create_support_ticket",

                    "args": {
                        "category":
                            "Unrecognized transaction",

                        "description":
                            (
                                "Customer does not "
                                "recognize transaction."
                            ),

                        "transaction_id":
                            "TXN-1001",
                    },

                    "description":
                        (
                            "Tool execution requires "
                            "approval"
                        ),
                }
            ],

            "review_configs": [
                {
                    "action_name":
                        "create_support_ticket",

                    "allowed_decisions": [
                        "approve",
                        "reject",
                    ],
                }
            ],
        }
    )

    return SimpleNamespace(
        value={},
        interrupts=[
            interrupt
        ],
    )


@pytest.fixture(
    autouse=True
)
def configure_test_dependencies(
    monkeypatch,
):
    """
    Every test starts with deterministic dependencies.

    - No real OpenAI call.
    - No real authentication.
    - No real PostgreSQL thread lookup.
    """

    app.dependency_overrides.clear()

    # Fake authenticated customer.
    app.dependency_overrides[
        get_customer_id
    ] = lambda: "CUST-001"

    # Fake LangGraph agent dependency.
    app.dependency_overrides[
        get_agent
    ] = lambda: FAKE_AGENT

    # Do not access the real database during
    # deterministic API tests.
    monkeypatch.setattr(
        api_module,
        "ensure_thread_access",
        lambda thread_id, customer_id: None,
    )

    yield

    app.dependency_overrides.clear()


def test_health():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok"
    }


def test_chat_completed(
    monkeypatch,
):

    def fake_run_agent(
        agent,
        message: str,
        customer_id: str,
        thread_id: str,
    ):

        assert agent is FAKE_AGENT

        assert (
            message
            == "What is my name and account type?"
        )

        assert customer_id == "CUST-001"

        assert (
            thread_id
            == "test-thread-001"
        )

        return completed_result(
            (
                "Your name is Alex Morgan "
                "and your account type "
                "is Premium."
            )
        )

    monkeypatch.setattr(
        api_module,
        "run_agent",
        fake_run_agent,
    )

    response = client.post(
        "/api/v1/chat",

        json={
            "thread_id":
                "test-thread-001",

            "message":
                (
                    "What is my name "
                    "and account type?"
                ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["thread_id"]
        == "test-thread-001"
    )

    assert (
        data["status"]
        == "completed"
    )

    assert (
        "Alex Morgan"
        in data["response"]
    )

    assert data["approval"] is None

    assert (
        data["request_id"]
        .startswith("req-")
    )


def test_chat_returns_approval_required(
    monkeypatch,
):

    monkeypatch.setattr(
        api_module,
        "run_agent",
        lambda **kwargs:
            approval_required_result(),
    )

    response = client.post(
        "/api/v1/chat",

        json={
            "thread_id":
                "hitl-test-001",

            "message":
                (
                    "I don't recognize "
                    "TXN-1001. "
                    "Please open a support "
                    "ticket."
                ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["status"]
        == "approval_required"
    )

    assert data["response"] is None

    assert (
        data["approval"]["name"]
        == "create_support_ticket"
    )

    assert (
        data["approval"]
        ["arguments"]
        ["transaction_id"]
        == "TXN-1001"
    )


def test_thread_access_denied(
    monkeypatch,
):

    # Simulate another authenticated customer.
    app.dependency_overrides[
        get_customer_id
    ] = lambda: "CUST-002"

    def deny_access(
        thread_id: str,
        customer_id: str,
    ):

        assert (
            thread_id
            == "owned-by-cust-001"
        )

        assert (
            customer_id
            == "CUST-002"
        )

        raise PermissionError(
            (
                "Thread does not belong "
                "to authenticated customer."
            )
        )

    monkeypatch.setattr(
        api_module,
        "ensure_thread_access",
        deny_access,
    )

    response = client.post(
        "/api/v1/chat",

        json={
            "thread_id":
                "owned-by-cust-001",

            "message":
                "Hello",
        },
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Thread access denied."
    )


def test_missing_customer_auth():
    """
    Here we deliberately remove our fake auth
    dependency so the real authentication
    dependency is tested.
    """

    app.dependency_overrides.pop(
        get_customer_id,
        None,
    )

    response = client.post(
        "/api/v1/chat",

        json={
            "thread_id":
                "test-thread",

            "message":
                "Hello",
        },
    )

    assert response.status_code == 401


def test_empty_message_rejected():

    response = client.post(
        "/api/v1/chat",

        json={
            "thread_id":
                "test-thread",

            "message":
                "",
        },
    )

    assert response.status_code == 422


def test_request_id_is_generated():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert (
        "X-Request-ID"
        in response.headers
    )

    request_id = (
        response.headers[
            "X-Request-ID"
        ]
    )

    assert request_id

    assert request_id.startswith(
        "req-"
    )


def test_existing_request_id_is_preserved():

    request_id = (
        "test-request-123"
    )

    response = client.get(
        "/health",

        headers={
            "X-Request-ID":
                request_id,
        },
    )

    assert response.status_code == 200

    assert (
        response.headers[
            "X-Request-ID"
        ]
        == request_id
    )


def test_timing_header_is_present():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert (
        TIMING_HEADER
        in response.headers
    )

    timing_value = float(
        response.headers[
            TIMING_HEADER
        ]
    )

    assert timing_value >= 0