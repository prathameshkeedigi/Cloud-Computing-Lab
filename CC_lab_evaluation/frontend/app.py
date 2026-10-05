"""
Library Management System - Streamlit client (frontend).
This is the CLIENT in the architecture: it only calls the REST APIs of the
four microservices. It holds no data of its own.
"""

import os

import pandas as pd
import requests
import streamlit as st

BOOK_URL = os.getenv("BOOK_SERVICE_URL", "http://127.0.0.1:8001")
MEMBER_URL = os.getenv("MEMBER_SERVICE_URL", "http://127.0.0.1:8002")
BORROW_URL = os.getenv("BORROW_SERVICE_URL", "http://127.0.0.1:8003")
NOTIFY_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8004")

st.set_page_config(page_title="Library Management", page_icon="📚", layout="wide")


def api(method, url, **kwargs):
    try:
        r = requests.request(method, url, timeout=5, **kwargs)
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.RequestException as exc:
        return None, f"Cannot reach {url} ({exc.__class__.__name__})"


st.sidebar.title("📚 Library System")
page = st.sidebar.radio("Go to", ["Dashboard", "Books", "Members", "Borrow / Return", "Notifications"])
st.sidebar.caption("Client → Borrow Service → Book / Member / Notification Services")

# ------------------------------------------------------------------ Dashboard
if page == "Dashboard":
    st.title("Library Management System")
    st.write("A microservice application: four FastAPI services, each in its own Docker "
             "container with its own SQLite database.")
    status, err = api("GET", f"{BORROW_URL}/services/status")
    st.subheader("Service health (checked by Borrow Service over the Docker network)")
    if err:
        st.error(err)
    else:
        cols = st.columns(len(status))
        for col, (name, state) in zip(cols, status.items()):
            col.metric(name, "🟢 " + state if state == "healthy" else "🔴 " + state)

    books, _ = api("GET", f"{BOOK_URL}/books")
    members, _ = api("GET", f"{MEMBER_URL}/members")
    borrows, _ = api("GET", f"{BORROW_URL}/borrows")
    c1, c2, c3 = st.columns(3)
    c1.metric("Books", len(books or []))
    c2.metric("Members", len(members or []))
    c3.metric("Active borrows", sum(1 for b in (borrows or []) if not b["returned_at"]))

# ---------------------------------------------------------------------- Books
elif page == "Books":
    st.title("Books  ·  Book Service (port 8001)")
    with st.form("add_book", clear_on_submit=True):
        c1, c2 = st.columns(2)
        title = c1.text_input("Title")
        author = c2.text_input("Author")
        if st.form_submit_button("Add book") and title and author:
            data, err = api("POST", f"{BOOK_URL}/books", json={"title": title, "author": author})
            if data:
                st.success(f"Added book #{data['id']}")
            else:
                st.error(err)
    books, err = api("GET", f"{BOOK_URL}/books")
    if err:
        st.error(err)
    else:
        st.dataframe(pd.DataFrame(books), width="stretch", hide_index=True)

# -------------------------------------------------------------------- Members
elif page == "Members":
    st.title("Members  ·  Member Service (port 8002)")
    with st.form("add_member", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name")
        email = c2.text_input("Email")
        if st.form_submit_button("Add member") and name and email:
            data, err = api("POST", f"{MEMBER_URL}/members", json={"name": name, "email": email})
            if data:
                st.success(f"Added member #{data['id']}")
            else:
                st.error(err)
    members, err = api("GET", f"{MEMBER_URL}/members")
    if err:
        st.error(err)
    else:
        st.dataframe(pd.DataFrame(members), width="stretch", hide_index=True)

# ------------------------------------------------------------- Borrow / Return
elif page == "Borrow / Return":
    st.title("Borrow / Return  ·  Borrow Service (port 8003)")
    st.caption("A borrow request goes Client → Borrow Service → Member Service + Book Service "
               "→ Notification Service, all over the Docker network.")
    books, _ = api("GET", f"{BOOK_URL}/books")
    members, _ = api("GET", f"{MEMBER_URL}/members")
    books, members = books or [], members or []

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Borrow a book")
        m = st.selectbox("Member", members, format_func=lambda x: f"{x['id']} - {x['name']}")
        free = [b for b in books if b["available"]]
        b = st.selectbox("Available book", free, format_func=lambda x: f"{x['id']} - {x['title']}")
        if st.button("Borrow", type="primary") and m and b:
            data, err = api("POST", f"{BORROW_URL}/borrow",
                            json={"member_id": m["id"], "book_id": b["id"]})
            if data:
                st.success(f"Borrow #{data['borrow_id']}: {data['member']} borrowed '{data['book']}'")
                st.info(f"Notification: {data['notification']}")
            else:
                st.error(err)
    with c2:
        st.subheader("Return a book")
        borrows, _ = api("GET", f"{BORROW_URL}/borrows")
        active = [x for x in (borrows or []) if not x["returned_at"]]
        r = st.selectbox("Active borrow", active,
                         format_func=lambda x: f"#{x['id']} - member {x['member_id']}, book {x['book_id']}")
        if st.button("Return") and r:
            data, err = api("POST", f"{BORROW_URL}/return/{r['id']}")
            if data:
                st.success(f"Returned '{data['book']}'")
            else:
                st.error(err)

    st.subheader("Borrow history")
    borrows, _ = api("GET", f"{BORROW_URL}/borrows")
    st.dataframe(pd.DataFrame(borrows or []), width="stretch", hide_index=True)

# --------------------------------------------------------------- Notifications
elif page == "Notifications":
    st.title("Notifications  ·  Notification Service (port 8004)")
    notes, err = api("GET", f"{NOTIFY_URL}/notifications")
    if err:
        st.error(err)
    elif not notes:
        st.info("No notifications yet. Borrow a book to create one.")
    else:
        st.dataframe(pd.DataFrame(notes), width="stretch", hide_index=True)
