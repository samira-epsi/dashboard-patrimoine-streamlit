import time
import requests

from api.auth import get_token
from config import BASE_URL


def get(
    endpoint,
    params=None,
    retries=10
):

    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):

        try:

            token = get_token()

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            return response.json()

        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.SSLError
        ) as e:

            status_code = None

            if hasattr(e, "response") and e.response:

                status_code = e.response.status_code

            wait_time = (
                attempt + 1
            ) * 5

            print(
                f"\nTentative {attempt + 1}/{retries}"
            )

            print(
                f"Erreur : {type(e).__name__}"
            )

            if status_code:

                print(
                    f"Status : {status_code}"
                )

            print(
                f"URL : {url}"
            )

            print(
                f"Nouvelle tentative dans "
                f"{wait_time}s..."
            )

            time.sleep(wait_time)

    raise Exception(
        f"Echec après {retries} tentatives : {url}"
    )