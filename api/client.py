import time
import requests

from api.auth import get_token
from config import BASE_URL


RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def get(
    endpoint,
    params=None,
    retries=3,
):

    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):

        try:

            token = get_token()

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60,
            )

            # --------------------------------------------
            # Succès
            # --------------------------------------------
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:

            response = e.response
            status_code = (
                response.status_code
                if response is not None
                else None
            )

            print(
                f"\nErreur HTTP | "
                f"status={status_code} | "
                f"URL={response.url if response is not None else url}"
            )

            # --------------------------------------------
            # Erreurs NON retryables
            #
            # 400, 401, 403, 404...
            # Attendre ne changera rien.
            #
            # On remonte l'HTTPError originale afin que
            # le code appelant puisse lire status_code.
            # --------------------------------------------
            if status_code not in RETRYABLE_STATUS_CODES:
                raise

            # --------------------------------------------
            # Dernière tentative
            # --------------------------------------------
            if attempt == retries - 1:
                raise

            wait_time = (attempt + 1) * 5

            print(
                f"Tentative {attempt + 1}/{retries} échouée. "
                f"Nouvelle tentative dans {wait_time}s..."
            )

            time.sleep(wait_time)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
        ) as e:

            print(
                f"\nErreur réseau | "
                f"{type(e).__name__} | "
                f"URL={url}"
            )

            if attempt == retries - 1:
                raise

            wait_time = (attempt + 1) * 5

            print(
                f"Tentative {attempt + 1}/{retries} échouée. "
                f"Nouvelle tentative dans {wait_time}s..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        f"Echec inattendu lors de l'appel : {url}"
    )