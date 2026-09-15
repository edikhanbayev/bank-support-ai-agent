import re

POLICIES = [
    {
        "id": "POL-DISPUTE-001",
        "title": "Unrecognized card transaction",
        "keywords": {
            "unrecognized",
            "unknown",
            "card",
            "transaction",
            "fraud",
            "merchant",
            "dispute"
        },
        "text": (
            "Customers who do not recognize a card "
            "transaction should report it to support. "
            "Support may create a dispute case after "
            "the transaction and customer identity "
            "have been verified."
        )
    },
    {
        "id": "POL-PENDING-001",
        "title": "Pending transaction",
        "keywords": {
            "pending",
            "transaction",
            "card",
            "merchant"
        },
        "text": (
            "Pending card transactions have not yet "
            "been fully settled. Customers should "
            "normally wait until the transaction is "
            "posted before opening a standard dispute."
        )
    },
    {
        "id": "POL-REFUND-001",
        "title": "Merchant refund",
        "keywords": {
            "refund",
            "merchant",
            "purchase",
            "returned"
        },
        "text": (
            "Merchant refunds may require several "
            "business days to appear after the "
            "merchant initiates the refund."
        )
    }
]

def search_policies(query: str) -> list[dict]:

    query_tokens = set(
        re.findall(
            r"[a-zA-Z]+",
            query.lower()
        )
    )

    scored = []

    for policy in POLICIES:

        score = len(
            query_tokens.intersection(
                policy["keywords"]
            )
        )

        if score > 0:
            scored.append(
                (score, policy)
            )

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        policy
        for _, policy in scored[:2]
    ]