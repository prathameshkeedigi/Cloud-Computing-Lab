"""
Locust workload for the Library Management System.

API under test: GET /borrow/check?member_id=..&book_id=..  on the Borrow Service.
Each request is an end-to-end, multi-service request:
    Locust (client) -> Borrow Service -> Member Service + Book Service
It is read-only, so the database does not change during the test and every
workload level sees the same conditions.

wait_time = constant(0): each simulated user sends its next request as soon as the
previous one finishes, so "number of users" = "number of concurrent requests".

Run interactively (web UI at http://127.0.0.1:8089):
    locust -f loadtest/locustfile.py --host http://127.0.0.1:8003
"""

import random

from locust import HttpUser, constant, task


class LibraryUser(HttpUser):
    wait_time = constant(0)

    @task
    def check_borrow(self):
        member_id = random.randint(1, 5)
        book_id = random.randint(1, 10)
        self.client.get(f"/borrow/check?member_id={member_id}&book_id={book_id}",
                        name="/borrow/check")
