"""Manual verification script for Phase 9: Category Management & Supplier-Category Markups.

Requires the FastAPI app running (uvicorn app.main:app --reload) and a populated DB.

Usage:
    python manual_test_phase9.py
"""
import requests
import uuid
from decimal import Decimal
from sqlmodel import select, func
from app.database import get_session
from app.models.category import Category, ProviderCategoryMarkup
from app.models.item import Item, Provider, ProviderListing, ItemType
from app.services.pricing import get_price_final, get_price_detail

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@kasi.co.za"
ADMIN_PASSWORD = "Maurice@12!"

session = requests.Session()
admin_token = None


def login_admin():
    global admin_token
    import time
    for attempt in range(5):
        try:
            resp = session.post(
                f"{BASE_URL}/auth/login",
                data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=5,
            )
            if resp.status_code == 200:
                admin_token = resp.json().get("access_token")
                print(f"  Token acquired: {admin_token[:20]}...")
                return admin_token
        except Exception:
            pass
        print(f"  Login attempt {attempt+1} failed, retrying...")
        time.sleep(2)
    print(f"  Login failed after retries")
    return None


def admin_headers():
    if not admin_token:
        login_admin()
    return {"Authorization": f"Bearer {admin_token}"}


def test_category_crud():
    print("\n=== CATEGORY CRUD ===")

    # 1. List categories
    resp = session.get(f"{BASE_URL}/admin/categories", headers=admin_headers())
    print(f"GET /admin/categories: {resp.status_code}")
    if resp.status_code == 200:
        cats = resp.json()
        print(f"  Found {len(cats)} existing categories")
        for c in cats[:3]:
            print(f"    - {c['name']} (active={c['is_active']})")

    # 2. Create a new category
    resp = session.post(
        f"{BASE_URL}/admin/categories?name=TestCategory&description=For+testing",
        headers=admin_headers(),
    )
    print(f"POST /admin/categories: {resp.status_code}")
    if resp.status_code == 200:
        new_cat = resp.json()
        print(f"  Created: {new_cat['name']} id={new_cat['id']}")
        return new_cat["id"]
    elif resp.status_code == 400:
        print(f"  Already exists (OK): {resp.json().get('detail')}")
        # fetch existing id
        resp2 = session.get(f"{BASE_URL}/admin/categories", headers=admin_headers())
        for c in resp2.json():
            if c["name"] == "TestCategory":
                return c["id"]
    return None


def test_update_category(cat_id):
    print(f"\n=== UPDATE CATEGORY {cat_id} ===")
    resp = session.patch(
        f"{BASE_URL}/admin/categories/{cat_id}?name=TestCategoryRenamed&is_active=true",
        headers=admin_headers(),
    )
    print(f"PATCH /admin/categories/{cat_id}: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  Updated: {resp.json()['name']}")
    else:
        print(f"  {resp.text[:200]}")


def test_delete_category(cat_id):
    print(f"\n=== DELETE CATEGORY {cat_id} ===")
    resp = session.delete(f"{BASE_URL}/admin/categories/{cat_id}", headers=admin_headers())
    print(f"DELETE /admin/categories/{cat_id}: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  {resp.json()['message']}")
    else:
        print(f"  {resp.text[:200]}")


def test_provider_markup_crud():
    print("\n=== PROVIDER MARKUP CRUD ===")
    # get first provider
    resp = session.get(f"{BASE_URL}/admin/providers", headers=admin_headers())
    raw = resp.json()
    if isinstance(raw, dict):
        providers = raw.get("providers") or raw.get("items") or []
    elif isinstance(raw, list):
        providers = raw
    else:
        providers = []
    print(f"  Providers found: {len(providers)}")
    if providers:
        print(f"  First provider keys: {list(providers[0].keys()) if isinstance(providers[0], dict) else type(providers[0])}")
    if not providers:
        print("  SKIP: no providers in DB")
        return
    provider = providers[0]
    pid = provider["id"] if isinstance(provider, dict) else str(provider)
    print(f"  Using provider: {provider.get('name') if isinstance(provider, dict) else provider} ({pid})")

    # list existing markups
    resp = session.get(f"{BASE_URL}/admin/providers/{pid}/markups", headers=admin_headers())
    print(f"GET /admin/providers/{pid}/markups: {resp.status_code}")
    if resp.status_code == 200:
        markups = resp.json()
        print(f"  Existing markups: {len(markups)}")

    # create/update markup
    resp = session.post(
        f"{BASE_URL}/admin/providers/{pid}/markups?category=Tool+Rental&price_markup=15.00",
        headers=admin_headers(),
    )
    print(f"POST /admin/providers/{pid}/markups: {resp.status_code}")
    if resp.status_code == 200:
        m = resp.json()
        print(f"  Upserted: category={m['category']} markup={m['price_markup']}")
    else:
        print(f"  {resp.text[:200]}")

    # list again
    resp = session.get(f"{BASE_URL}/admin/providers/{pid}/markups", headers=admin_headers())
    if resp.status_code == 200:
        markups = resp.json()
        print(f"  Markups after upsert: {len(markups)}")
        for m in markups:
            print(f"    - {m['category']}: {m['price_markup']}")

    # delete markup
    resp = session.delete(
        f"{BASE_URL}/admin/providers/{pid}/markups/Tool+Rental",
        headers=admin_headers(),
    )
    print(f"DELETE /admin/providers/{pid}/markups/Tool Rental: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  {resp.json()['message']}")


def test_price_resolution():
    print("\n=== PRICE RESOLUTION ===")
    db = next(get_session())

    # pick first item with provider_listings
    item = db.exec(select(Item)).first()
    if not item:
        print("  SKIP: no items in DB")
        return
    print(f"  Item: {item.title} (category={item.category}, price_markup={item.price_markup})")

    # get price detail
    detail = get_price_detail(item, db)
    print(f"  price_final={detail['price_final']}")
    print(f"  effective_markup={detail['effective_markup']}")
    print(f"  markup_source={detail['markup_source']}")

    # test override — use the item's actual category, clean up any existing first
    provider_id = item.provider_listings[0].provider_id if item.provider_listings else None
    if provider_id:
        target_cat = item.category
        # remove any pre-existing override for this provider+category
        existing = db.exec(
            select(ProviderCategoryMarkup).where(
                ProviderCategoryMarkup.provider_id == provider_id,
                ProviderCategoryMarkup.category == target_cat,
            )
        ).first()
        if existing:
            db.delete(existing)
            db.commit()

        override = ProviderCategoryMarkup(
            provider_id=provider_id,
            category=target_cat,
            price_markup=Decimal("99.99"),
        )
        db.add(override)
        db.commit()

        detail2 = get_price_detail(item, db)
        print(f"  After override markup={detail2['effective_markup']} source={detail2['markup_source']}")
        assert detail2["effective_markup"] == Decimal("99.99"), f"Override not applied! got {detail2['effective_markup']}"
        assert detail2["markup_source"] == "provider_category", "Source should be provider_category"
        print("  OVERRIDE VERIFIED OK")

        # cleanup
        db.delete(override)
        db.commit()
    else:
        print("  SKIP override: no provider_listings")

    db.close()


def test_item_category_validation():
    print("\n=== ITEM CATEGORY VALIDATION ===")
    # try creating item with invalid category
    resp = session.post(
        f"{BASE_URL}/admin/items",
        json={
            "slug": "test-invalid-cat",
            "title": "Test Invalid Cat",
            "item_type": "SERVICE",
            "category": "FakeCategoryThatDoesNotExist",
            "price_markup": 0,
        },
        headers=admin_headers(),
    )
    print(f"POST /admin/items (bad category): {resp.status_code}")
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        print(f"  400 OK: {detail[:120]}")
        assert "FakeCategoryThatDoesNotExist" in detail or "Valid categories" in detail
        print("  VALIDATION VERIFIED OK")
    else:
        print(f"  Unexpected: {resp.text[:200]}")


def test_public_api():
    print("\n=== PUBLIC API ===")
    resp = session.get(f"{BASE_URL}/items")
    print(f"GET /items: {resp.status_code}")
    if resp.status_code == 200:
        items = resp.json()
        print(f"  Returned {len(items)} items")
        if items:
            first = items[0]
            print(f"  Sample: {first['title']} price_final={first['price_final']} category={first['category']}")
    else:
        print(f"  {resp.text[:200]}")


def test_search_service():
    print("\n=== SEARCH SERVICE ===")
    from app.services.search import search_service
    from app.schemas.search import SearchValidateRequest

    req = SearchValidateRequest(q="test", category="Tool Rental", item_ids=None, location=None)
    result = search_service(req, user_is_authenticated=False)
    print(f"  Search returned {result['total_matches']} matches")
    print(f"  valid_category={result['valid_category']}")
    for item in result["items"][:2]:
        print(f"    - {item['title']} price_final={item['price_final']}")


def test_seed_category_autoreg():
    print("\n=== SEED AUTO-REGISTER CATEGORY ===")
    db = next(get_session())
    # Simulate what seed does
    test_type = f"AutoTestCat_{uuid.uuid4().hex[:6]}"
    existing = db.exec(select(Category).where(Category.name == test_type)).first()
    print(f"  Category '{test_type}' exists before: {existing is not None}")

    # mimic seed logic
    import re
    slug = re.sub(r'[^a-z0-9-]+', '-', test_type.lower()).strip('-')
    if not existing:
        cat = Category(name=test_type, slug=slug)
        db.add(cat)
        db.commit()
        print(f"  Auto-created category: {cat.name}")

    count = db.exec(select(func.count(Category.id))).first()
    print(f"  Total categories in DB: {count}")
    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 9 Manual Verification")
    print("=" * 60)
    print("Ensure the API is running at", BASE_URL)

    try:
        login_admin()
        test_category_crud()
        cat_id = None
        cats_resp = session.get(f"{BASE_URL}/admin/categories", headers=admin_headers())
        if cats_resp.status_code == 200:
            for c in cats_resp.json():
                if c["name"] == "TestCategoryRenamed":
                    cat_id = c["id"]
                    break
        if cat_id:
            test_update_category(cat_id)
            test_delete_category(cat_id)

        test_provider_markup_crud()
        test_price_resolution()
        test_item_category_validation()
        test_public_api()
        test_search_service()
        test_seed_category_autoreg()

        print("\n" + "=" * 60)
        print("All checks completed.")
        print("=" * 60)
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
