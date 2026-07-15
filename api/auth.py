import time
import requests

from config import (
    CLIENT_ID,
    CLIENT_SECRET,
    TOKEN_URL
)


_cached_token = None
_token_expiration = 0


def get_token():

    global _cached_token
    global _token_expiration

    now = time.time()

    # Si le token existe encore,
    # on le réutilise
    if (
        _cached_token is not None
        and now < _token_expiration
    ):
        return _cached_token

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(
        TOKEN_URL,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    token_data = response.json()

    _cached_token = token_data[
        "access_token"
    ]

    expires_in = token_data.get(
        "expires_in",
        3600
    )

    # On renouvelle 5 min avant expiration
    _token_expiration = (
        now
        + expires_in
        - 300
    )

    print(
        "Nouveau token OAuth récupéré"
    )

    return _cached_token