from typing import Annotated
import jwt
from fastapi import Header, HTTPException, Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError
)

from app.config import (
    JWT_ALGORITHM,
    JWT_SECRET
)

bearer_scheme = HTTPBearer(
    auto_error=False
)

def get_customer_id(
    credentials:
        HTTPAuthorizationCredentials
        | None
        = Depends(bearer_scheme)
) -> str:

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    try:

        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[
                JWT_ALGORITHM
            ]
        )

    except ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token expired."
        )

    except InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token."
        )

    customer_id = payload.get(
        "sub"
    )

    if not customer_id:

        raise HTTPException(
            status_code=401,
            detail=(
                "Token has no "
                "customer identity."
            )
        )

    return customer_id