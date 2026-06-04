from __future__ import annotations

import os
import requests


GSM_CHEAP_BASE_URL = os.getenv("GSM_CHEAP_BASE_URL", "https://gsmcheap.com")
GSM_CHEAP_USERNAME = os.getenv("GSM_CHEAP_USERNAME")
GSM_CHEAP_PASSWORD = os.getenv("GSM_CHEAP_PASSWORD")

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_ADMIN_TOKEN = os.getenv("BACKEND_ADMIN_TOKEN")

SESSION = requests.Session()


def login() -> None:
    raise NotImplementedError("Provide GSM Cheap login flow/request details")


def fetch_services() -> list[dict]:
    raise NotImplementedError("Use fetch_gsmcheap_v1.py logic here")


def purchase_service(service_id: str, **kwargs) -> dict:
    raise NotImplementedError("Implement GSM Cheap purchase request")


def fulfill_order(order_id: str, credentials: list[dict]) -> None:
    raise NotImplementedError(
        "Call backend admin fulfill endpoint with encrypted credentials"
    )


def run_once() -> None:
    raise NotImplementedError("Poll backend PAID orders and fulfill SERVICE items")


def main() -> None:
    if not all([GSM_CHEAP_USERNAME, GSM_CHEAP_PASSWORD, BACKEND_ADMIN_TOKEN]):
        print("Missing required environment variables")
        return
    run_once()


if __name__ == "__main__":
    main()
