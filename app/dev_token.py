from datetime import (
    datetime,
    timedelta,
    timezone
)

import jwt

from app.config import (
    JWT_ALGORITHM,
    JWT_SECRET
)

payload = {
    "sub": "CUST-001",
    "exp": (
        datetime.now(
            timezone.utc
        )
        + timedelta(hours=8)
    )
}


token = jwt.encode(
    payload,
    JWT_SECRET,
    algorithm=JWT_ALGORITHM
)

print(token)