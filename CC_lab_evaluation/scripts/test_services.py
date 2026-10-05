"""
Calls every REST endpoint of the four microservices and prints the responses.
Used for Checkpoint 1 (each service works) and Checkpoint 3 (end-to-end request).

Usage:  python scripts/test_services.py
"""

import json
import sys

import requests

BOOK, MEMBER, BORROW, NOTIFY = ("http://127.0.0.1:8001", "http://127.0.0.1:8002",
                                "http://127.0.0.1:8003", "http://127.0.0.1:8004")
ok = True


def show(method, url, **kw):
    global ok
    try:
        r = requests.request(method, url, timeout=5, **kw)
        body = r.json()
    except Exception as exc:
        ok = False
        print(f"[FAIL] {method} {url} -> {exc}")
        return None
    mark = "PASS" if r.ok else "FAIL"
    ok &= r.ok
    text = json.dumps(body)
    print(f"[{mark}] {method} {url} -> {r.status_code}  {text[:110]}{'...' if len(text) > 110 else ''}")
    return body


print("--- Health checks (one per service) ---")
for url in (BOOK, MEMBER, BORROW, NOTIFY):
    show("GET", f"{url}/health")

print("\n--- Book Service ---")
show("GET", f"{BOOK}/books")
show("GET", f"{BOOK}/books/1")

print("\n--- Member Service ---")
show("GET", f"{MEMBER}/members")
show("GET", f"{MEMBER}/members/1")

print("\n--- Notification Service ---")
show("GET", f"{NOTIFY}/notifications")

print("\n--- Borrow Service: inter-service communication ---")
show("GET", f"{BORROW}/services/status")
show("GET", f"{BORROW}/borrow/check?member_id=1&book_id=2")

print("\n--- End-to-end: borrow then return (touches all 4 services) ---")
books = requests.get(f"{BOOK}/books", timeout=5).json()
free = next((b for b in books if b["available"]), None)
if free:
    res = show("POST", f"{BORROW}/borrow", json={"member_id": 1, "book_id": free["id"]})
    show("GET", f"{BOOK}/books/{free['id']}")          # now available = false
    if res:
        show("POST", f"{BORROW}/return/{res['borrow_id']}")
    show("GET", f"{NOTIFY}/notifications?member_id=1")

print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)
