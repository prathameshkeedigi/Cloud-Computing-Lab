<div align="center">

# Lab Evaluation — Build, Deploy and Analyze a Containerized Microservice Application Under Varying Workloads
### Library Management System · 4 FastAPI Microservices · Docker Compose · Locust

**Course:** Cloud Computing Laboratory — Lab Evaluation (5 marks)
**Stack:** Python FastAPI (services) · Streamlit (client) · SQLite (one database per service) · Docker + Docker Compose · Locust (load testing)
**Platform:** Windows 11 · Docker Desktop 29.8.0 (WSL2) · Docker Compose v5.5.1 · 16 logical CPUs · 16 GB RAM

![Services](https://img.shields.io/badge/Microservices-4-7c3aed)
![Docker](https://img.shields.io/badge/Docker-Compose-2563eb)
![Load test](https://img.shields.io/badge/Locust-1%2C2%2C4%2C8%2C16%20users-16a34a)
![Failures](https://img.shields.io/badge/Failed%20requests-0%20of%2041%2C220-16a34a)
![Peak](https://img.shields.io/badge/Peak%20throughput-160.8%20req%2Fs-ea580c)

</div>

---

## Abstract

This lab evaluation builds a small **Library Management System** as four independent microservices:
- **Book Service** manages the book catalogue.
- **Member Service** manages library members.
- **Borrow Service** issues and returns books.
- **Notification Service** records messages sent to members.

Each service is a **FastAPI** application with its **own SQLite database** and its **own Dockerfile**. All four are deployed with **Docker Compose** on a shared network called `library-net`, with a **Streamlit** web page as the client. The services talk to each other using **Docker service names** (for example `http://book-service:8001`).

The end-to-end API `GET /borrow/check` goes Client → Borrow → Member + Book. It was load-tested with **Locust** at five workload levels (1, 2, 4, 8 and 16 concurrent users, 60 s each) while `docker stats` recorded CPU and memory for every container.

**Results:**
- **No request failed**: 0 out of 41,220.
- Throughput rose from **89.5 req/s** with 1 user to a peak of **160.8 req/s** with 2–4 users. After that it **levelled off and dropped slightly** to 147.5 req/s at 16 users.
- Over the same range, average response time grew from **11.0 ms to 108.2 ms**, roughly doubling every time the number of users doubled.
- The **Borrow Service** was the bottleneck. It used about **1.2–1.3 CPU cores** under load, while each of the other services stayed under 0.5 core.
- **Memory stayed flat** (~260–270 MiB in total).
- The measurements agree with **Little's Law** (users = throughput × response time) to within 1 %.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Aim and Objectives](#2-aim-and-objectives)
3. [Basic Concepts](#3-basic-concepts)
4. [Application Design](#4-application-design)
5. [Experimental Setup](#5-experimental-setup)
6. [Methodology and Workflow](#6-methodology-and-workflow)
7. [Checkpoint 1 — Design and Develop the Microservices](#7-checkpoint-1--design-and-develop-the-microservices)
8. [Checkpoint 2 — Containerize and Deploy the Application](#8-checkpoint-2--containerize-and-deploy-the-application)
9. [Checkpoint 3 — Microservice Communication](#9-checkpoint-3--microservice-communication)
10. [Checkpoint 4 — Varying Workloads and Monitoring](#10-checkpoint-4--varying-workloads-and-monitoring)
11. [Checkpoint 5 — Results and Performance Analysis](#11-checkpoint-5--results-and-performance-analysis)
12. [Discussion — Answers to the Manual's Questions](#12-discussion--answers-to-the-manuals-questions)
13. [Observations and Limitations](#13-observations-and-limitations)
14. [Troubleshooting and Issues Encountered](#14-troubleshooting-and-issues-encountered)
15. [Important Terms](#15-important-terms)
16. [Conclusion](#16-conclusion)
17. [Repository Structure and How to Run](#17-repository-structure-and-how-to-run)
18. [References](#18-references)

---

## 1. Introduction

A **monolithic** application puts every feature into one program. A **microservice** application splits it into **small, independent services**. Each service:
- does **one job**;
- has **its own database**;
- talks to the others through **REST APIs**;
- can be built, deployed and scaled **separately**.

**Docker** packages each service with everything it needs into an **image**, and runs it as an isolated **container**. **Docker Compose** starts all the containers together from one file, places them on a shared network, and lets them find each other by name.

The goal of this evaluation is to **demonstrate Docker**: containerising, deploying, connecting, load-testing and monitoring a microservice application. The application itself is kept deliberately simple.

---

## 2. Aim and Objectives

**Aim** (from the lab manual): To develop a microservice-based application, containerize and deploy the services using Docker, establish inter-service communication, generate varying workloads, monitor resource utilization, and analyze application performance.

**Objectives:**

| # | Objective | Checkpoint |
|:-:|:--|:-:|
| 1 | Design independent microservices with clear responsibilities and REST APIs, and test each one on its own | CP1 |
| 2 | Write a Dockerfile per service, build the images and deploy them with Docker Compose | CP2 |
| 3 | Connect the services on one Docker network and show an end-to-end request across services | CP3 |
| 4 | Load-test at 5 workload levels (1, 2, 4, 8, 16 concurrent requests) and record response time, throughput, failures, CPU and memory | CP4 |
| 5 | Build the observation table and graphs, analyse the results and explain them | CP5 |

### Evaluation checkpoint compliance

| CP | Requirement (1 mark each) | Where it is shown |
|:-:|:--|:--|
| 1 | Design and develop the microservices, with working REST APIs | [Section 7](#7-checkpoint-1--design-and-develop-the-microservices); screenshots 01–22 |
| 2 | Separate Dockerfiles, images built, Docker Compose deployment, containers running | [Section 8](#8-checkpoint-2--containerize-and-deploy-the-application); screenshots 23–26 |
| 3 | Shared network, calls by service name, end-to-end request | [Section 9](#9-checkpoint-3--microservice-communication); screenshots 18–20, 27–34 |
| 4 | 5 workload levels, response time, throughput, failures, CPU and memory | [Section 10](#10-checkpoint-4--varying-workloads-and-monitoring); screenshots 35–45 |
| 5 | Observation table, graphs, comparison, bottleneck, explanation | [Sections 11–12](#11-checkpoint-5--results-and-performance-analysis); Figs. 1–9 |

> **Note on the number of services.** The manual asks for **exactly three** microservices. This project uses **four**. The fourth, the Notification Service, was added as an extension to show a request that fans out to more than two services (`POST /borrow` touches all four). The required **minimum architecture**, *Client → Service 1 → Service 2 / Service 3*, is fully met: Client → Borrow Service → Member Service / Book Service. The workload test uses exactly this three-service path.

---

## 3. Basic Concepts

### 3.1 Key Docker terms

| Term | Meaning | In this project |
|:--|:--|:--|
| **Dockerfile** | A recipe for building an image | One per service in `services/<name>/Dockerfile` |
| **Image** | A read-only package: OS base + Python + libraries + code | `library-app/book-service:1.0`, etc. |
| **Container** | A running instance of an image | `book-service`, `member-service`, … |
| **Docker Compose** | Starts many containers from one YAML file | `docker-compose.yml` |
| **Network** | A virtual network that lets containers talk to each other | `library-net` (bridge, 172.18.0.0/16) |
| **Service name / DNS** | Compose registers each service name in Docker's built-in DNS | `http://book-service:8001` |
| **Volume** | Storage that survives when the container is deleted | `book-data`, `member-data`, … (SQLite files) |
| **Healthcheck** | A command Docker runs to check that a container is working | Calls `/health` every 5 s |

### 3.2 Performance metrics

| Metric | Meaning | Better if |
|:--|:--|:--|
| **Concurrency** | Number of requests in progress at the same time (Locust users) | — |
| **Response time** | Time from sending a request to getting the reply (average, median, 95th percentile) | Lower |
| **Throughput** | Requests completed per second (req/s) | Higher |
| **Failed requests** | Requests that returned an error or timed out | 0 |
| **CPU %** | CPU used by a container (100 % = one full CPU core) | Lower for the same work |
| **Memory (MiB)** | RAM used by a container | Lower / stable |
| **Little's Law** | $N = X \times R$: users = throughput × response time | Used to check that the data is consistent |

---

## 4. Application Design

### 4.1 Domain and services

**Domain:** Library Management. This is one of the domains suggested in the manual, chosen because it has only a few tables and one natural request that crosses several services.

| Service | Port | Responsibility | Database | REST endpoints |
|:--|:-:|:--|:--|:--|
| **Book Service** | 8001 | Book catalogue and availability | `books.db` | `GET /health`, `GET /books`, `POST /books`, `GET /books/{id}`, `PATCH /books/{id}/availability` |
| **Member Service** | 8002 | Library members (students) | `members.db` | `GET /health`, `GET /members`, `POST /members`, `GET /members/{id}` |
| **Borrow Service** | 8003 | Issue and return books; **entry point** that calls the other three | `borrows.db` | `GET /health`, `GET /services/status`, `GET /borrow/check`, `POST /borrow`, `POST /return/{id}`, `GET /borrows` |
| **Notification Service** | 8004 | Record messages sent to members | `notifications.db` | `GET /health`, `POST /notifications`, `GET /notifications` |
| *Streamlit client* | 8501 | Web interface (the **Client**, not a microservice) | — | Calls the four APIs |

The databases are seeded on first start with 10 books and 5 members.

### 4.2 Architecture

```mermaid
flowchart LR
    U([User / Browser]) --> FE[Streamlit Client<br/>:8501]
    L([Locust<br/>load generator]) --> BO
    FE --> BO[Borrow Service<br/>:8003<br/>borrows.db]
    FE --> BK
    FE --> ME
    FE --> NO
    BO -- "http://member-service:8002" --> ME[Member Service<br/>:8002<br/>members.db]
    BO -- "http://book-service:8001" --> BK[Book Service<br/>:8001<br/>books.db]
    BO -- "http://notification-service:8004" --> NO[Notification Service<br/>:8004<br/>notifications.db]
    subgraph net [Docker network: library-net]
      FE
      BO
      BK
      ME
      NO
    end
    style BO fill:#ede9fe
    style BK fill:#dbeafe
    style ME fill:#dcfce7
    style NO fill:#ffedd5
```

### 4.3 Request flows

| Request | Path | Services involved | Used for |
|:--|:--|:-:|:--|
| `GET /borrow/check?member_id&book_id` | Client → Borrow → Member + Book | 3 | **Workload test** (read-only, so the data never changes during the test) |
| `POST /borrow` | Client → Borrow → Member → Book (check + update) → Notification | **4** | Full end-to-end demo |
| `POST /return/{id}` | Client → Borrow → Book (update) → Notification | 3 | End-to-end demo |
| `GET /services/status` | Borrow → `/health` of the other 3 | 4 | Communication demo / dashboard |

```mermaid
sequenceDiagram
    participant C as Client (Streamlit / Locust)
    participant B as Borrow Service
    participant M as Member Service
    participant K as Book Service
    participant N as Notification Service
    C->>B: POST /borrow {member_id, book_id}
    B->>M: GET /members/{id}
    M-->>B: member (active?)
    B->>K: GET /books/{id}
    K-->>B: book (available?)
    B->>K: PATCH /books/{id}/availability {false}
    B->>B: save borrow in borrows.db
    B->>N: POST /notifications
    N-->>B: notification saved
    B-->>C: 201 {borrow_id, member, book, notification}
```

---

## 5. Experimental Setup

| Item | Value |
|:--|:--|
| Host | Windows 11 laptop, 16 logical CPUs, 16 GB RAM |
| Docker | Docker Desktop, Engine 29.8.0 (WSL2 backend), Docker Compose v5.5.1 |
| Base image | `python:3.12-slim` |
| Backend | FastAPI + Uvicorn (1 worker per service), `sqlite3` (built into Python), `httpx` (service-to-service calls) |
| Client | Streamlit, `requests`, pandas |
| Load tool | **Locust 2.46.6** (headless mode, run on the host) |
| Monitoring | `docker stats --no-stream`, sampled continuously during each workload |
| Analysis | Python 3.13, pandas, matplotlib |
| Resource limits | None. Each container may use any of the host's CPUs; the memory limit shown by Docker is 7.664 GiB |

**Docker images built:**

| Image | Disk usage | Content size |
|:--|--:|--:|
| `library-app/book-service:1.0` | 212 MB | 51.5 MB |
| `library-app/member-service:1.0` | 212 MB | 51.5 MB |
| `library-app/borrow-service:1.0` | 214 MB | 52.0 MB |
| `library-app/notification-service:1.0` | 212 MB | 51.5 MB |
| `library-app/frontend:1.0` (client) | 778 MB | 179 MB |

The service images are small because they contain only FastAPI and Uvicorn (plus httpx for Borrow). The frontend is larger because Streamlit depends on pandas, numpy and pyarrow.

---

## 6. Methodology and Workflow

The work followed the manual's workflow:

```mermaid
flowchart LR
    A[DEVELOP<br/>4 FastAPI services] --> B[CONTAINERIZE<br/>4 Dockerfiles]
    B --> C[DEPLOY<br/>docker compose up]
    C --> D[CONNECT<br/>library-net + service names]
    D --> E[LOAD TEST<br/>Locust W1-W5]
    E --> F[MONITOR<br/>docker stats]
    F --> G[ANALYZE<br/>table + graphs]
    G --> H[DEMONSTRATE]
```

The screenshots were renamed in the order they were taken (`01` … `45`) and grouped by checkpoint in [`screenshots/`](screenshots).

---

## 7. Checkpoint 1 — Design and Develop the Microservices

### 7.1 Implementation

Every service follows the same simple pattern: a FastAPI app, a SQLite file created at start-up, and plain SQL queries. Below is the core of the Book Service ([`services/book_service/main.py`](services/book_service/main.py)):

```python
DB_PATH = os.getenv("DB_PATH", "data/books.db")      # each service owns its database

app = FastAPI(title="Book Service", version="1.0", lifespan=lifespan)

@app.get("/health")
def health():
    return {"service": "book-service", "status": "healthy"}

@app.get("/books/{book_id}")
def get_book(book_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row_to_book(row)
```

The Borrow Service reads the other services' addresses from **environment variables**. The same code runs locally (`http://127.0.0.1:8001`) and in Docker (`http://book-service:8001`):

```python
BOOK_URL   = os.getenv("BOOK_SERVICE_URL",   "http://127.0.0.1:8001")
MEMBER_URL = os.getenv("MEMBER_SERVICE_URL", "http://127.0.0.1:8002")
NOTIFY_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8004")

@app.get("/borrow/check")
def check_borrow(member_id: int, book_id: int):
    member = fetch_member(member_id)      # -> Member Service
    book = fetch_book(book_id)            # -> Book Service
    return {"member": member["name"], "book": book["title"],
            "can_borrow": member["active"] and book["available"]}
```

### 7.2 Running each service independently

Each service was started in its own terminal, without Docker:

```bash
cd services/book_service         && python -m uvicorn main:app --port 8001
cd services/member_service       && python -m uvicorn main:app --port 8002
cd services/notification_service && python -m uvicorn main:app --port 8004
cd services/borrow_service       && python -m uvicorn main:app --port 8003
python scripts/test_services.py   # calls every endpoint -> "ALL CHECKS PASSED"
```

Every endpoint was then run from the Swagger UI (`http://127.0.0.1:<port>/docs`), which FastAPI generates automatically.

### 7.3 API test results

| Service | Endpoint tested | Response | Screenshot |
|:--|:--|:--|:-:|
| Book | `GET /health` | 200 `{"service":"book-service","status":"healthy"}` | 02 |
| Book | `GET /books` | 200, list of books | 03 |
| Book | `POST /books` | New book added | 04 |
| Book | `GET /books/11` | 200 `{"id":11,"title":"Vedant","author":"Krishna","available":true}` | 05 |
| Book | `PATCH /books/11/availability` | 200, `available: false` | 06 |
| Member | `GET /health`, `GET /members`, `GET /members/1` | 200, member data | 08, 09, 11 |
| Member | `POST /members` | **201 Created** | 10 |
| Notification | `GET /health` | 200 healthy | 13 |
| Notification | `POST /notifications` | **201**, id 5 | 14 |
| Notification | `GET /notifications?member_id=1` | 200, borrow / return messages | 15 |
| Borrow | `GET /services/status` | All 4 services `"healthy"` | 18 |
| Borrow | `GET /borrow/check?member_id=1&book_id=1` | `can_borrow: true` (Aarav Sharma, Clean Code) | 19 |
| Borrow | `POST /borrow`, `POST /return/2`, `GET /borrows` | Borrow #2 issued and returned ("Introduction to Algorithms") | 20–22 |

### 7.4 Screenshots — Checkpoint 1

| | |
|:-:|:-:|
| <img src="screenshots/CP1_Microservices/01_book_swagger_endpoints.png" width="100%"><br><em>01 — Book Service: 5 endpoints</em> | <img src="screenshots/CP1_Microservices/02_book_get_health.png" width="100%"><br><em>02 — Book: GET /health</em> |
| <img src="screenshots/CP1_Microservices/03_book_get_books.png" width="100%"><br><em>03 — Book: GET /books</em> | <img src="screenshots/CP1_Microservices/04_book_post_add_book.png" width="100%"><br><em>04 — Book: POST /books</em> |
| <img src="screenshots/CP1_Microservices/05_book_get_book_by_id.png" width="100%"><br><em>05 — Book: GET /books/11</em> | <img src="screenshots/CP1_Microservices/06_book_patch_availability.png" width="100%"><br><em>06 — Book: PATCH availability</em> |
| <img src="screenshots/CP1_Microservices/07_member_swagger_endpoints.png" width="100%"><br><em>07 — Member Service: 4 endpoints</em> | <img src="screenshots/CP1_Microservices/08_member_get_health.png" width="100%"><br><em>08 — Member: GET /health</em> |
| <img src="screenshots/CP1_Microservices/09_member_get_members.png" width="100%"><br><em>09 — Member: GET /members</em> | <img src="screenshots/CP1_Microservices/10_member_post_add_member.png" width="100%"><br><em>10 — Member: POST /members (201)</em> |
| <img src="screenshots/CP1_Microservices/11_member_get_member_by_id.png" width="100%"><br><em>11 — Member: GET /members/1</em> | <img src="screenshots/CP1_Microservices/12_notification_swagger_endpoints.png" width="100%"><br><em>12 — Notification Service: 3 endpoints</em> |
| <img src="screenshots/CP1_Microservices/13_notification_get_health.png" width="100%"><br><em>13 — Notification: GET /health</em> | <img src="screenshots/CP1_Microservices/14_notification_post_notification.png" width="100%"><br><em>14 — Notification: POST (201)</em> |
| <img src="screenshots/CP1_Microservices/15_notification_get_notifications.png" width="100%"><br><em>15 — Notification: GET by member</em> | <img src="screenshots/CP1_Microservices/16_borrow_swagger_endpoints.png" width="100%"><br><em>16 — Borrow Service: 6 endpoints</em> |
| <img src="screenshots/CP1_Microservices/17_borrow_get_health.png" width="100%"><br><em>17 — Borrow: GET /health</em> | <img src="screenshots/CP1_Microservices/18_borrow_services_status.png" width="100%"><br><em>18 — Borrow: GET /services/status</em> |
| <img src="screenshots/CP1_Microservices/19_borrow_check.png" width="100%"><br><em>19 — Borrow: GET /borrow/check</em> | <img src="screenshots/CP1_Microservices/20_borrow_post_borrow.png" width="100%"><br><em>20 — Borrow: POST /borrow</em> |
| <img src="screenshots/CP1_Microservices/21_borrow_post_return.png" width="100%"><br><em>21 — Borrow: POST /return/2</em> | <img src="screenshots/CP1_Microservices/22_borrow_get_borrows.png" width="100%"><br><em>22 — Borrow: GET /borrows</em> |

✅ **Completion condition met:** all four microservices work on their own, and their APIs return the expected responses.

---

## 8. Checkpoint 2 — Containerize and Deploy the Application

### 8.1 Dockerfile (one per service)

All four service Dockerfiles follow the same pattern. Only the port changes. Here is [`services/borrow_service/Dockerfile`](services/borrow_service/Dockerfile):

```dockerfile
FROM python:3.12-slim                         # small official Python base image

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .                       # copied first so this layer is cached
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .                                # application code

EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

| Line | Why it is there |
|:--|:--|
| `FROM python:3.12-slim` | Small Debian image with Python already installed (~50 MB of content) |
| `COPY requirements.txt` before `COPY main.py` | When only the code changes, Docker reuses the cached `pip install` layer, so rebuilds are fast |
| `--no-cache-dir` | Keeps pip's download cache out of the image (smaller image) |
| `--host 0.0.0.0` | Listen on all interfaces so other containers and the host can reach the service (`127.0.0.1` would only be reachable from inside the container) |

Dependency files: `fastapi` and `uvicorn` for every service, plus `httpx` for Borrow ([`requirements.txt`](services/borrow_service/requirements.txt)). Each service folder also has a `.dockerignore` that keeps local databases and `__pycache__` out of the image.

### 8.2 docker-compose.yml (key parts)

Full file: [`docker-compose.yml`](docker-compose.yml)

```yaml
services:
  book-service:
    build: ./services/book_service
    image: library-app/book-service:1.0
    container_name: book-service
    ports: ["8001:8001"]
    environment:
      DB_PATH: /data/books.db
    volumes: [book-data:/data]                  # SQLite file survives restarts
    networks: [library-net]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
      interval: 5s

  borrow-service:
    build: ./services/borrow_service
    environment:
      BOOK_SERVICE_URL: http://book-service:8001             # service names, not IPs
      MEMBER_SERVICE_URL: http://member-service:8002
      NOTIFICATION_SERVICE_URL: http://notification-service:8004
    depends_on:                                              # start only after the others are healthy
      book-service:         {condition: service_healthy}
      member-service:       {condition: service_healthy}
      notification-service: {condition: service_healthy}
  # member-service, notification-service and frontend are configured the same way

networks:
  library-net:
    driver: bridge
```

### 8.3 Build and deploy commands

```bash
docker compose build              # builds 5 images: 4 services + frontend
docker images library-app/*       # lists the images
docker compose up -d              # creates the network, 4 volumes and 5 containers
docker ps                         # all Up; the 4 services show (healthy)
```

**Result:**
- **Build:** all 5 images built in about 31 s (cached).
- **`docker compose up -d`:** created `library-net`, 4 volumes and the containers.
- **`docker ps`:** showed **book-service, member-service, notification-service and borrow-service as `Up (healthy)`**, and `library-frontend` as `Up`.
- **Start order:** borrow-service started last, because of `depends_on: service_healthy`.

### 8.4 Screenshots — Checkpoint 2

| | |
|:-:|:-:|
| <img src="screenshots/CP2_Docker_build_deploy/23_docker_compose_build.png" width="100%"><br><em>23 — <code>docker compose build</code>: 5 images Built</em> | <img src="screenshots/CP2_Docker_build_deploy/24_docker_images.png" width="100%"><br><em>24 — <code>docker images library-app/*</code></em> |
| <img src="screenshots/CP2_Docker_build_deploy/25_docker_compose_up.png" width="100%"><br><em>25 — <code>docker compose up -d</code>: network + volumes created</em> | <img src="screenshots/CP2_Docker_build_deploy/26_docker_ps_healthy.png" width="100%"><br><em>26 — <code>docker ps</code>: 4 services healthy</em> |

✅ **Completion condition met:** the service images were built and all microservices run as containers.

---

## 9. Checkpoint 3 — Microservice Communication

### 9.1 One network, discovery by service name

Docker Compose created the user-defined bridge network **`library-net`** (subnet `172.18.0.0/16`, gateway `172.18.0.1`) and connected all five containers to it:

| Container | IP on `library-net` |
|:--|:--|
| book-service | 172.18.0.2 |
| member-service | 172.18.0.3 |
| notification-service | 172.18.0.4 |
| borrow-service | 172.18.0.5 |
| library-frontend | 172.18.0.6 |

The code **never uses these IP addresses**. Docker runs a built-in DNS server, so the name `book-service` resolves to the right container even if its IP changes after a restart. This was shown directly from inside the Borrow container:

```bash
docker exec borrow-service python -c "import urllib.request;print(urllib.request.urlopen('http://book-service:8001/health').read())"
# b'{"service":"book-service","status":"healthy"}'
```

> **Why not `localhost`?** Inside a container, `localhost` means *that container itself*. The Borrow container has nothing listening on port 8001, so `http://localhost:8001` would fail. Service names are the correct way to reach another container.

### 9.2 End-to-end requests

| Test | Result | Evidence |
|:--|:--|:-:|
| Borrow pings the 3 other services over the network | All 4 report `"healthy"` | 18, 30 |
| `GET /borrow/check` (Borrow → Member + Book) | `{"member":"Aarav Sharma","book":"Clean Code","can_borrow":true}` | 19 |
| `POST /borrow` from the Streamlit page (all 4 services) | Borrow recorded, book marked unavailable, notification created | 33, 34 |
| `POST /return` | Book available again, "You returned …" notification | 33, 34 |

On the Streamlit **Notifications** page, the Notification Service stored the messages *"You borrowed 'Clean Code' (borrow #1)"*, *"You returned 'Clean Code'"* and so on. These could only appear if the Borrow container had reached the Notification container over `library-net`.

### 9.3 Screenshots — Checkpoint 3

| | |
|:-:|:-:|
| <img src="screenshots/CP3_Communication/27_network_inspect_config.png" width="100%"><br><em>27 — <code>docker network inspect library-net</code>: bridge, 172.18.0.0/16</em> | <img src="screenshots/CP3_Communication/28_network_inspect_containers.png" width="100%"><br><em>28 — All 5 containers on the network</em> |
| <img src="screenshots/CP3_Communication/29_docker_exec_service_name_call.png" width="100%"><br><em>29 — Borrow container calls <code>http://book-service:8001</code> by name</em> | <img src="screenshots/CP3_Communication/30_streamlit_dashboard_health.png" width="100%"><br><em>30 — Streamlit dashboard: all services healthy</em> |
| <img src="screenshots/CP3_Communication/31_streamlit_books.png" width="100%"><br><em>31 — Books page (Book Service)</em> | <img src="screenshots/CP3_Communication/32_streamlit_members.png" width="100%"><br><em>32 — Members page (Member Service)</em> |
| <img src="screenshots/CP3_Communication/33_streamlit_borrow_return.png" width="100%"><br><em>33 — Borrow / Return page and borrow history</em> | <img src="screenshots/CP3_Communication/34_streamlit_notifications.png" width="100%"><br><em>34 — Notifications created by the Borrow Service</em> |

✅ **Completion condition met:** the services communicate by service name, and the end-to-end requests return successfully to the client.

---

## 10. Checkpoint 4 — Varying Workloads and Monitoring

### 10.1 API chosen for the workload test

**`GET /borrow/check?member_id=<1-5>&book_id=<1-10>`** on the Borrow Service. It was chosen because:

1. **It crosses services.** Every request makes the Borrow Service call the Member Service and the Book Service, so it tests the containers *and* the network between them.
2. **It is read-only.** No data changes, so every workload level sees exactly the same conditions. Using `POST /borrow` instead would run out of available books within seconds.
3. **It matches the manual's minimum architecture:** Client → Service 1 → Service 2 / Service 3.

### 10.2 Locust workload

[`loadtest/locustfile.py`](loadtest/locustfile.py):

```python
class LibraryUser(HttpUser):
    wait_time = constant(0)          # send the next request as soon as the last one returns

    @task
    def check_borrow(self):
        member_id = random.randint(1, 5)
        book_id = random.randint(1, 10)
        self.client.get(f"/borrow/check?member_id={member_id}&book_id={book_id}",
                        name="/borrow/check")
```

With `wait_time = constant(0)`, each Locust user always has exactly one request in progress, so **number of users = number of concurrent requests**.

### 10.3 Automated run of the five levels

[`loadtest/run_workloads.py`](loadtest/run_workloads.py) runs the five levels one after another:
- For each level, it runs Locust in headless mode for **60 s**, with a 10 s pause between levels.
- At the same time, a background thread runs `docker stats --no-stream` in a loop and tags each sample with the current workload. That gave about **30 samples per container per level**.

| Test | Concurrent users | Duration | Started (IST) |
|:-:|:-:|:-:|:-:|
| W1 | 1 | 60 s | 00:01:28 |
| W2 | 2 | 60 s | 00:02:40 |
| W3 | 4 | 60 s | 00:03:53 |
| W4 | 8 | 60 s | 00:05:06 |
| W5 | 16 | 60 s | 00:06:19 |

```bash
docker stats book-service member-service borrow-service notification-service   # live view (terminal 2)
python loadtest/run_workloads.py                                                # W1-W5 (terminal 1)
```

**Outputs:**
- [`results/observation_table.csv`](results/observation_table.csv)
- [`results/container_usage.csv`](results/container_usage.csv)
- the raw Locust files and every `docker stats` sample in [`results/raw/`](results/raw)

Before the scripted run, the **Locust web UI** was used for a 1-minute demo with 8 users. It gave **148 req/s at 53.97 ms average** (screenshots 35–36). Those numbers closely match the scripted W4 result (149.9 req/s, 53.2 ms), which shows the measurements repeat well.

### 10.4 Live monitoring snapshots

| Moment | book | member | borrow | notification | Screenshot |
|:--|--:|--:|--:|--:|:-:|
| **Idle** (before the test) | 0.18 % | 0.32 % | 0.18 % | 0.24 % | 37 |
| **During W1** (1 user) | 36.74 % | 35.03 % | 54.03 % | 15.27 % | 38 |
| **During W5** (16 users) | 35.71 % | 34.79 % | **126.66 %** | 0.18 % | 43 |

During W5, the PIDS column also rose for borrow-service, from 2 to **17**. Uvicorn runs normal (`def`) endpoints in a thread pool, so more concurrent requests mean more threads.

### 10.5 Screenshots — Checkpoint 4

| | |
|:-:|:-:|
| <img src="screenshots/CP4_Load_testing/35_locust_ui_statistics_8_users.png" width="100%"><br><em>35 — Locust UI statistics (8 users): 11,984 requests, 0 fails</em> | <img src="screenshots/CP4_Load_testing/36_locust_ui_charts_8_users.png" width="100%"><br><em>36 — Locust UI charts: ~148 RPS, median ~52 ms</em> |
| <img src="screenshots/CP4_Load_testing/37_docker_stats_idle_before_test.png" width="100%"><br><em>37 — <code>docker stats</code> idle baseline</em> | <img src="screenshots/CP4_Load_testing/38_docker_stats_during_W1.png" width="100%"><br><em>38 — <code>docker stats</code> during W1</em> |
| <img src="screenshots/CP4_Load_testing/39_locust_W1_1_user.png" width="100%"><br><em>39 — W1, 1 user</em> | <img src="screenshots/CP4_Load_testing/40_locust_W2_2_users.png" width="100%"><br><em>40 — W2, 2 users</em> |
| <img src="screenshots/CP4_Load_testing/41_locust_W3_4_users.png" width="100%"><br><em>41 — W3, 4 users</em> | <img src="screenshots/CP4_Load_testing/42_locust_W4_8_users.png" width="100%"><br><em>42 — W4, 8 users</em> |
| <img src="screenshots/CP4_Load_testing/43_docker_stats_during_W5.png" width="100%"><br><em>43 — <code>docker stats</code> during W5: borrow 126.66 %</em> | <img src="screenshots/CP4_Load_testing/44_locust_W5_16_users.png" width="100%"><br><em>44 — W5, 16 users</em> |

<p align="center">
  <img src="screenshots/CP4_Load_testing/45_observation_table.png" width="90%"><br>
  <em>45 — Final observation table printed by <code>run_workloads.py</code></em>
</p>

✅ **Completion condition met:** performance was measured at all five workload levels, with CPU and memory recorded for every container.

---

## 11. Checkpoint 5 — Results and Performance Analysis

### 11.1 Observation table

| Workload | Concurrency | Total requests | Avg response (ms) | Median (ms) | 95th pct (ms) | Throughput (req/s) | Failed | CPU, all 4 services (%) | Memory, all 4 (MiB) |
|:-:|:-:|--:|--:|--:|--:|--:|:-:|--:|--:|
| W1 | 1 | 5,205 | **11.04** | 11 | 14 | **89.45** | 0 | 128.2 | 269.8 |
| W2 | 2 | 9,348 | **12.32** | 12 | 17 | **160.58** | 0 | 190.5 | 268.4 |
| W3 | 4 | 9,361 | **24.69** | 24 | 35 | **160.83** | 0 | 234.7 | 257.4 |
| W4 | 8 | 8,725 | **53.16** | 52 | 74 | **149.93** | 0 | 230.3 | 270.4 |
| W5 | 16 | 8,581 | **108.19** | 100 | 160 | **147.48** | 0 | 225.7 | 269.1 |
| **Total** | | **41,220** | | | | | **0** | | |

CPU is the sum of the four service containers' average CPU %, where 100 % = one core.

### 11.2 Per-container resource usage

**Average CPU % (maximum sample in brackets):**

| Workload | borrow-service | book-service | member-service | notification-service |
|:-:|--:|--:|--:|--:|
| W1 (1) | **51.0** (113) | 32.1 (94) | 32.2 (90) | 12.8 (69) |
| W2 (2) | **84.0** (147) | 46.9 (105) | 47.1 (104) | 12.5 (69) |
| W3 (4) | **119.9** (182) | 50.3 (107) | 50.9 (109) | 13.6 (66) |
| W4 (8) | **127.1** (191) | 45.3 (102) | 45.8 (105) | 12.1 (67) |
| W5 (16) | **126.6** (189) | 44.0 (101) | 44.1 (100) | 11.0 (68) |

**Average memory (MiB):**

| Workload | borrow-service | book-service | member-service | notification-service |
|:-:|--:|--:|--:|--:|
| W1 | 44.0 | 107.6 | 81.8 | 36.5 |
| W2 | 43.8 | 107.6 | 80.8 | 36.2 |
| W3 | 44.2 | 97.7 | 78.7 | 36.8 |
| W4 | 44.2 | 108.7 | 80.9 | 36.5 |
| W5 | 45.4 | 111.1 | 76.6 | 36.0 |

### 11.3 Response time

<p align="center"><img src="graphs/01_response_time_vs_concurrency.png" width="85%" alt="Response time vs concurrency"></p>

**What the graph shows:**
- From **1 to 2 users**, response time barely changes (11.0 → 12.3 ms). The system has spare capacity, so a second user doesn't have to wait.
- From **2 users onwards**, response time **roughly doubles each time the users double**: 12.3 → 24.7 → 53.2 → 108.2 ms. This is the classic sign of a **saturated** system. Extra requests don't get served faster; they **wait in a queue**.
- The **95th percentile** grows faster than the average (14 → 160 ms). The slowest requests suffer most from queueing.

### 11.4 Throughput

<p align="center"><img src="graphs/02_throughput_vs_concurrency.png" width="85%" alt="Throughput vs concurrency"></p>

**What the graph shows:**
- Going from 1 to 2 users **increased throughput by 80 %** (89.5 → 160.6 req/s).
- Throughput then **stopped growing**. It peaked at **160.8 req/s with 4 users**, which is the **maximum capacity** of this setup for this API.
- With 8 and 16 users, throughput **fell slightly** (149.9 and 147.5 req/s, about 8 % below the peak). With more users, the busy Borrow Service has more threads competing for the same CPU, and the switching between them adds overhead.

### 11.5 CPU utilisation

<p align="center"><img src="graphs/03_cpu_vs_concurrency.png" width="95%" alt="CPU vs concurrency"></p>

**What the graph shows:**
- **Borrow Service** CPU climbs steeply: 51 % → 84 % → 120 % → 127 % → 127 %. From W3 onwards it stays at about **1.2–1.3 cores** and can't go higher. This matches exactly the point where throughput stopped growing.
- **Book and Member Services** rise to about **45–50 %** and then stay level. They are **waiting for work** from the Borrow Service, so they are not the bottleneck.
- **Notification Service** is not used by `/borrow/check` at all, yet it shows a steady **11–14 %**. This is the cost of the **Docker healthcheck**, explained in [Section 12.4](#124-explain-any-performance-degradation-or-failures).

### 11.6 Memory utilisation

<p align="center"><img src="graphs/04_memory_vs_concurrency.png" width="95%" alt="Memory vs concurrency"></p>

**What the graph shows:**
- Memory is **flat** for every container. Going from 1 to 16 users changed total memory by less than ±5 %, from 257 to 270 MiB. Each request is small and short-lived, so memory doesn't build up.
- The differences between containers (book ~108 MiB, member ~80 MiB, borrow ~44 MiB, notification ~36 MiB) were already there **before** the test (screenshot 37: 104.7, 78.1, 42.5 and 35.4 MiB). They come from start-up and file cache, not from the load.
- **Memory was not a limiting factor.** The whole application used under 300 MiB of the 7.66 GiB available.

### 11.7 Throughput vs response time

<p align="center"><img src="graphs/05_throughput_vs_response_time.png" width="85%" alt="Throughput vs response time"></p>

**What the graph shows:** this is the typical "knee" curve of a system under load.
- From W1 to W2, the system moves **right**: more throughput at almost the same response time. That is **useful work**.
- After W2–W3, it moves **straight up**: much higher response time with **no extra throughput**. That is **pure queueing**.
- The best operating point is **2–4 concurrent requests**: maximum throughput at a response time of 12–25 ms.

### 11.8 Successful vs failed requests

<p align="center"><img src="graphs/06_requests_and_failures.png" width="85%" alt="Requests and failures"></p>

**What the graph shows:** all **41,220 requests succeeded (0 failures, 0 exceptions)** at every level. The system got **slower** under load but never **broke**. The highest single response time was 277 ms, far below the 5-second timeout the Borrow Service uses for its downstream calls.

### 11.9 Which microservice uses the most CPU?

<p align="center"><img src="graphs/07_cpu_share_per_service.png" width="85%" alt="CPU share per service"></p>

**What the graph shows:** the Borrow Service's share of the application's total CPU grew from **40 % at W1 to 56 % at W5**. Under load it uses **more CPU than the other three services put together**.

### 11.10 Little's Law check

<p align="center"><img src="graphs/09_littles_law_check.png" width="80%" alt="Little's Law check"></p>

For a closed system (a fixed number of users, each sending one request at a time), **Little's Law** says:

$$
N = X \times R \qquad \text{(users = throughput × average response time)}
$$

| Workload | Real N | X (req/s) | R (s) | N = X × R |
|:-:|:-:|--:|--:|--:|
| W1 | 1 | 89.45 | 0.01104 | **0.99** |
| W2 | 2 | 160.58 | 0.01232 | **1.98** |
| W3 | 4 | 160.83 | 0.02469 | **3.97** |
| W4 | 8 | 149.93 | 0.05316 | **7.97** |
| W5 | 16 | 147.48 | 0.10819 | **15.96** |

The calculated values match the real number of users to **within 1 %**. This confirms that the measured throughput and response times are **consistent with each other**. It also explains *why* response time doubles when users double: once throughput is fixed at about 150–160 req/s, $R = N / X$ has to grow in proportion to $N$.

### 11.11 Summary dashboard

<p align="center"><img src="graphs/08_summary_dashboard.png" width="100%" alt="Summary dashboard"></p>

---

## 12. Discussion — Answers to the Manual's Questions

### 12.1 Compare performance at different workload levels

| Level | Behaviour |
|:--|:--|
| **W1 (1 user)** | **Under-loaded.** Fastest responses (11 ms), but only 89 req/s because one user waits for each reply before sending the next request. |
| **W2 (2 users)** | **Best balance.** Almost the same speed (12 ms) with 80 % more throughput (161 req/s). |
| **W3 (4 users)** | **Saturation point.** Peak throughput (161 req/s), but response time has doubled (25 ms). |
| **W4 (8 users)** | **Overloaded.** No more throughput (150 req/s), and response time doubled again (53 ms). |
| **W5 (16 users)** | **Heavily overloaded.** Throughput 147 req/s, 108 ms average and 160 ms at the 95th percentile. Still **no failures**. |

### 12.2 How does increasing workload affect the application?

1. **Throughput increases only until the bottleneck is full.** Here that happens at about 2–4 concurrent requests and about 160 req/s.
2. **After that, more load only adds waiting time.** Response time grows in proportion to the number of users (Little's Law), and the 95th percentile grows even faster.
3. **Too much concurrency costs a little throughput** (−8 % at 16 users), because of thread switching inside the overloaded service.
4. **CPU rises with load until it hits a ceiling. Memory does not change.**

### 12.3 Which microservice consumes more resources?

**The Borrow Service, by a wide margin.** It averaged **120–127 % CPU** (about 1.2–1.3 cores) from W3 onwards, against **44–51 %** for Book and Member and **11–14 %** for Notification. The reasons:

- **It does the most work per request.** For each `/borrow/check` it accepts the client's request, **makes two outgoing HTTP calls** (to Member and Book), parses two JSON replies, and builds its own response. Book and Member each handle only one simple request and one SQLite lookup.
- **It runs a single Uvicorn worker process.** Because of Python's **Global Interpreter Lock (GIL)**, one Python process can effectively run Python code on only about **one core** at a time. The extra ~20–30 % above 100 % comes from work done outside the GIL, such as network I/O. The Borrow container can't use the host's other 14+ idle cores, so it becomes the **bottleneck** at about 160 req/s.

**For memory,** Book Service used the most (~108 MiB), but this stayed the same at every load level and was already there when idle, so it isn't caused by the workload.

### 12.4 Explain any performance degradation or failures

- **No failures occurred** (0 of 41,220).
- **Degradation seen:**
  1. **Response time grew from 11 ms to 108 ms.** This is queueing at the CPU-saturated Borrow Service: requests wait for a free turn on its ~1.25 cores.
  2. **Throughput fell 8 % after its peak.** With 8–16 users, the Borrow Service's thread pool runs more threads (PIDS rose to 17), and the threads compete for the GIL, which adds switching overhead.
  3. **Long tail.** The 95th percentile (160 ms at W5) is much higher than the median (100 ms), because some requests wait behind longer queues.
- **Hidden overhead found: Docker healthchecks.** Every 5 seconds, Docker runs `python -c "import urllib.request; …"` in **each** container. Starting a new Python interpreter takes a noticeable burst of CPU: notification-service samples spiked to **66–69 %** even though it received no load-test traffic. Averaged over time, that is about **11–14 % CPU per container, continuously**. Fixes: use a longer interval (e.g. 30 s), or a lighter check such as `curl` or `wget` in the image.

### 12.5 How could the bottleneck be removed?

| Option | Expected effect |
|:--|:--|
| Run Borrow with several Uvicorn workers (`--workers 4`) or several container replicas (`docker compose up --scale borrow-service=3` behind a load balancer) | Uses more cores, so throughput should rise well above 160 req/s |
| Use `async def` endpoints with `httpx.AsyncClient` and call Member and Book **in parallel** | Lower response time per request and fewer threads |
| Lighter healthchecks / a longer interval | Frees about 11–14 % CPU per container |
| Cache member/book lookups in Borrow for a few seconds | Fewer downstream calls per request |

---

## 13. Observations and Limitations

**Observations:**

1. Docker made the four services **easy to package and start together** with one command, `docker compose up -d`. The Borrow Service waited for the others to become healthy before starting.
2. **Service-name discovery** on `library-net` worked without any IP addresses in the code.
3. Each service could be **tested on its own** (Swagger UI) and also **as part of the whole system** (Streamlit and the end-to-end requests).
4. Under load, the system **degraded gradually rather than failing**: 0 errors, with response time growing in line with Little's Law.
5. The **busiest service decides the capacity** of the whole application. Here that was the Borrow Service, with 1 Uvicorn worker.

**Limitations:**

| Limitation | Effect |
|:--|:--|
| Locust ran **on the same laptop** as Docker | The load generator and the containers shared the CPU. With 16 logical CPUs and 2–4 cores in use, this had little impact, but a separate machine would be cleaner. |
| **One 60 s run** per level | Small run-to-run differences are possible. The repeat check (Locust UI at 8 users: 148 req/s / 54 ms against scripted W4: 150 req/s / 53 ms) suggests they are small. |
| `docker stats --no-stream` gives **snapshots** about every 2 s | CPU averages are based on about 30 samples per level. Short spikes (such as healthchecks) appear in some samples and not others. |
| **No CPU/memory limits** on the containers | Results depend on this laptop's hardware. Setting `cpus:` / `mem_limit:` in Compose would make them easier to repeat. |
| Docker Desktop runs containers inside a **WSL2 virtual machine** | Adds a small virtualisation overhead compared with native Linux. |
| Locust **console vs CSV** counts differ slightly | Locust saves its CSV at the last 1-second tick, about 0.3 s before it prints the final console summary. The console summaries in the screenshots therefore show a few more requests (e.g. W1: 5,228 against 5,205 in the CSV, under 1 % more). They also show a larger maximum (≈250–370 ms), most likely from requests caught during Locust's own shutdown. The averages, medians and throughput agree to within 1 %. This report uses the CSV values. |
| Exactly 3 services are required; 4 were built | Explained in [Section 2](#2-aim-and-objectives). The load test uses the required 3-service path. |

---

## 14. Troubleshooting and Issues Encountered

### 14.1 Issues actually encountered

| Issue | Cause | Fix |
|:--|:--|:--|
| Running locally, Borrow → other services calls took about 2 s each, and `/services/status` timed out | On Windows, `localhost` resolves to IPv6 `::1` first. Uvicorn listens only on IPv4, so each connection waited about 2 s before falling back to IPv4 | Use `http://127.0.0.1:<port>` as the local default URL. Inside Docker, service names avoid the problem completely |
| Image names like `library/book-service` showed up in `docker images` **without** the `library/` part | `library/` is Docker Hub's namespace for *official* images, so Docker hides it | Renamed the images to `library-app/<service>:1.0` |
| First `docker compose build` took several minutes | First download of `python:3.12-slim` and the Streamlit / pandas wheels | One-off cost. Later builds reuse the cached layers (~31 s) |
| Streamlit printed code text (`st.error(err) if err else st.dataframe(...) DeltaGenerator(...)`) under the Members table (screenshot 32) | Streamlit's **"magic"** feature displays the result of any bare one-line expression, and the one-line `if … else` was treated as one | Rewrote these lines as normal `if / else` blocks in [`frontend/app.py`](frontend/app.py). Rebuild the client with `docker compose up -d --build frontend` |
| Timestamps stored by the services are about 5.5 h behind IST (e.g. `18:14` for 23:44) | Containers use **UTC** by default | Expected. Set `TZ` and install `tzdata` in the image if local time is needed |
| Some Streamlit screenshots show an earlier borrow history than the Swagger screenshots | The Docker containers use **new, empty volumes**, separate from the local `data/` folders used in Checkpoint 1 | Expected. Each environment has its own databases |

### 14.2 General troubleshooting guide

| Problem | Solution |
|:--|:--|
| `port is already allocated` on `docker compose up` | A local Uvicorn is still using the port. Stop it with Ctrl+C, or find it with `netstat -ano \| findstr 8001` |
| A container shows `(unhealthy)` or keeps restarting | `docker compose logs <service>` |
| Borrow returns `503 Cannot reach http://book-service:8001` | The Book container isn't running, or isn't on `library-net`. Check with `docker ps` and `docker network inspect library-net` |
| `docker` commands fail with "cannot connect to the Docker daemon" | Start Docker Desktop and wait for "Engine running" |
| Locust shows many failures | Check that the containers are healthy and that the `--host` URL is right (`http://127.0.0.1:8003`) |
| Changes to code not visible | Rebuild: `docker compose up -d --build` |
| Start again with empty databases | `docker compose down -v` (also deletes the volumes) |

---

## 15. Important Terms

| Term | Meaning |
|:--|:--|
| **Microservice** | A small, independent service that does one job and exposes a REST API |
| **REST API** | A way for programs to communicate over HTTP using URLs and methods (GET, POST, PATCH) |
| **FastAPI / Uvicorn** | Python web framework / the server that runs it |
| **Swagger UI** | Automatic API test page at `/docs`, generated by FastAPI |
| **Docker image / container** | A packaged application / a running copy of it |
| **Docker Compose** | A tool that runs a multi-container application from one YAML file |
| **Bridge network** | A private virtual network for containers on one host |
| **Service discovery** | Finding another service by name (Docker DNS) instead of by IP |
| **Volume** | Persistent storage that survives when a container is deleted |
| **Healthcheck** | A command Docker runs regularly to check that a container works |
| **Locust** | A Python load-testing tool that simulates many users |
| **Concurrency** | Number of requests in progress at the same time |
| **Throughput** | Requests completed per second |
| **Response time / latency** | Time taken to answer one request |
| **95th percentile** | 95 % of requests were faster than this value |
| **Bottleneck** | The slowest part of a system, which limits the capacity of the whole |
| **Saturation** | The point where adding load no longer increases throughput |
| **GIL** | Python's Global Interpreter Lock: one Python process runs Python code on about one core at a time |
| **Little's Law** | Users = throughput × response time |

---

## 16. Conclusion

A Library Management System was built as **four FastAPI microservices**, each with its **own SQLite database and its own Dockerfile**, plus a Streamlit client. All five checkpoints were completed:

- **CP1:** every service ran and was tested **on its own**, with all endpoints returning the expected responses (screenshots 01–22).
- **CP2:** five images were built, and **Docker Compose** deployed all containers. The four services became **healthy**, and the Borrow Service started only after its dependencies were ready.
- **CP3:** all containers joined **`library-net`** and communicated **by service name**. End-to-end requests (`/borrow/check`, `/borrow`, `/return`) worked across three and four services.
- **CP4:** Locust tested **1, 2, 4, 8 and 16 concurrent users** for 60 s each while `docker stats` recorded CPU and memory for every container.
- **CP5:** the analysis shows that:
  - throughput rose from **89.5 to a peak of 160.8 req/s** and then **saturated**;
  - average response time grew from **11 ms to 108 ms**, in line with **Little's Law**;
  - **no request failed** out of 41,220;
  - **memory stayed flat** (~270 MiB in total);
  - the **Borrow Service was the bottleneck** at about 1.25 CPU cores, because it does the most work per request and runs as a single Python worker.

**Key lesson:** Docker makes a multi-service application easy to **package, connect, deploy and observe**. Under load, the **busiest service sets the limit** for the whole system. Scaling that one service (more workers or replicas) is the natural next step, and microservices plus Docker Compose make that possible without touching the other services.

---

## 17. Repository Structure and How to Run

```text
CC_lab_evaluation/
├── README.md                         ← this report
├── docker-compose.yml                ← 4 services + client, network, volumes, healthchecks
├── .gitignore
├── services/
│   ├── book_service/                 ← main.py, Dockerfile, requirements.txt, .dockerignore  (:8001)
│   ├── member_service/               ← same files                                            (:8002)
│   ├── borrow_service/               ← same files (+ httpx)                                  (:8003)
│   └── notification_service/         ← same files                                            (:8004)
├── frontend/                         ← Streamlit client: app.py, Dockerfile, requirements.txt (:8501)
├── loadtest/
│   ├── locustfile.py                 ← workload: GET /borrow/check
│   └── run_workloads.py              ← runs W1–W5 + samples docker stats
├── scripts/
│   ├── test_services.py              ← calls every endpoint (CP1 / CP3)
│   └── generate_graphs.py            ← matplotlib figures (Fig. 1–9)
├── results/
│   ├── observation_table.csv         ← one row per workload
│   ├── container_usage.csv           ← CPU / memory per container per workload
│   └── raw/                          ← Locust CSVs + all docker stats samples
├── graphs/                           ← 9 generated figures
└── screenshots/
    ├── CP1_Microservices/            ← 01–22  Swagger tests of each service
    ├── CP2_Docker_build_deploy/      ← 23–26  build, images, compose up, docker ps
    ├── CP3_Communication/            ← 27–34  network, service-name call, Streamlit
    └── CP4_Load_testing/             ← 35–45  Locust UI, docker stats, W1–W5, table
```

**Run everything:**

```bash
# 1. Deploy (Docker Desktop must be running)
docker compose up -d --build
docker ps                                   # wait until the 4 services are (healthy)

# 2. Use it
#    Streamlit client:  http://localhost:8501
#    Swagger UIs:       http://localhost:8001/docs  (8002, 8003, 8004)
python scripts/test_services.py             # quick check of every endpoint

# 3. Load test + monitoring (about 6 minutes)
pip install locust pandas matplotlib requests
python loadtest/run_workloads.py            # writes results/
python scripts/generate_graphs.py           # writes graphs/

# Optional: Locust web UI at http://localhost:8089
python -m locust -f loadtest/locustfile.py --host http://127.0.0.1:8003

# 4. Stop
docker compose down                         # add -v to delete the databases too
```

---

## 18. References

1. *Lab Evaluation Manual — Build, Deploy and Analyze a Containerized Microservice Application Under Varying Workloads*, Cloud Computing Laboratory.
2. Docker Inc., *Docker Documentation*: Dockerfile reference, Docker Compose file reference, Networking in Compose, `docker stats`.
3. S. Ramírez, *FastAPI Documentation*; Encode, *Uvicorn Documentation*.
4. Locust contributors, *Locust Documentation* (v2.x), https://docs.locust.io.
5. Snowflake Inc., *Streamlit Documentation*.
6. S. Newman, *Building Microservices*, 2nd ed., O'Reilly, 2021.
7. J. D. C. Little, "A proof for the queuing formula L = λW," *Operations Research*, vol. 9, no. 3, pp. 383–387, 1961.

---

<div align="center"><sub>Lab Evaluation · Cloud Computing Laboratory</sub></div>
