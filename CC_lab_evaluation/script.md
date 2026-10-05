# Presentation Script — Library Management Microservices

**Lab evaluation:** Build, Deploy and Analyze a Containerized Microservice Application Under Varying Workloads (5 marks, 5 checkpoints)

This file is the script for the live demonstration. It tells you:

- **DO** — the command to type or the thing to open, in order.
- **SAY** — what to explain, in plain words. Do not read it word for word; understand it and say it in your own words.
- **SHOW** — which screenshot or graph to point at, and which number to read out.
- **IF ASKED** — questions a strict evaluator is likely to ask, with correct answers.

Every number in this script comes from our own measured files (`results/observation_table.csv`, `results/container_usage.csv`) and our screenshots. Nothing is copied from the manual.

The slides in `presentation.pptx` follow the same order as this script.

---

## Contents

0. [Before the evaluator arrives (setup checklist)](#0-before-the-evaluator-arrives-setup-checklist)
1. [Opening — 1 minute](#1-opening--1-minute)
2. [Checkpoint 1 — Design and develop the microservices](#2-checkpoint-1--design-and-develop-the-microservices)
3. [Checkpoint 2 — Containerize and deploy](#3-checkpoint-2--containerize-and-deploy)
4. [Checkpoint 3 — Communication between services](#4-checkpoint-3--communication-between-services)
5. [Checkpoint 4 — Varying workloads and monitoring (most important)](#5-checkpoint-4--varying-workloads-and-monitoring-most-important)
6. [Checkpoint 5 — Results, graphs and analysis (most important)](#6-checkpoint-5--results-graphs-and-analysis-most-important)
7. [Closing — 1 minute](#7-closing--1-minute)
8. [Hard questions and honest answers](#8-hard-questions-and-honest-answers)
9. [Numbers to remember](#9-numbers-to-remember)
10. [Command cheat sheet](#10-command-cheat-sheet)

---

## 0. Before the evaluator arrives (setup checklist)

Do this 10–15 minutes before your turn.

**0.1 Start Docker Desktop.** Open it from the Start menu and wait for **Engine running**.

**0.2 Open the project in VS Code.** *File → Open Folder* →
`C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation`

**0.3 Free the ports for Checkpoint 1.** Checkpoint 1 runs the services *without* Docker, so no container may be using ports 8001–8004. In a terminal:

```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation
docker compose down
```

(`down` keeps the volumes and images. Do **not** add `-v` now unless you want empty databases.)

**0.4 Open 5 terminals** in VS Code (*Terminal → New Terminal*, then the **+** button). Rename them `book`, `member`, `notify`, `borrow`, `main` (right-click → Rename). This makes it look organised and saves time.

**0.5 Open these files in VS Code tabs**, in this order (you will click through them):

1. `services/book_service/main.py`
2. `services/borrow_service/main.py`
3. `services/book_service/Dockerfile`
4. `docker-compose.yml`
5. `loadtest/locustfile.py`
6. `loadtest/run_workloads.py`
7. `results/observation_table.csv`
8. `scripts/generate_graphs.py`

**0.6 Open `presentation.pptx`** and the `graphs/` and `screenshots/` folders in File Explorer.

**0.7 Know which terminal you use.** The VS Code terminal in our screenshots is **cmd**. Every command in this script works in both cmd and PowerShell, unless it says otherwise.

---

## 1. Opening — 1 minute

**SHOW:** slides 1–4 (title, roadmap, aim, architecture).

**SAY:**

> "Our domain is a **Library Management System**. We built it as **four independent microservices** using Python FastAPI, each with its own SQLite database. We containerized each service with its own Dockerfile, deployed all of them with Docker Compose on one Docker network, and connected them by service name. Then we load-tested the system with Locust at five workload levels — 1, 2, 4, 8 and 16 concurrent requests — while monitoring every container with `docker stats`, and analysed the results with an observation table and nine graphs.
>
> I will show it checkpoint by checkpoint, as the manual asks."

**Architecture in one breath (point at slide 4):**

> "The client — a Streamlit web page, or Locust during load testing — sends a request to the **Borrow Service**. The Borrow Service calls the **Member Service** to check the member, the **Book Service** to check the book, and for a real borrow it also calls the **Notification Service**. This matches the manual's minimum architecture: Client → Service 1 → Service 2 / Service 3."

**IF ASKED: "The manual says exactly three services. Why four?"**

> "The required three-service path is fully there: Client → Borrow → Member and Book. Our load test uses exactly this path. We added the Notification Service as an extension, to show one request fanning out to more than two services — `POST /borrow` touches all four. If you prefer, the Notification Service can be ignored; the other three meet every requirement."

---

## 2. Checkpoint 1 — Design and develop the microservices

**Manual's completion condition:** *All microservices are independently working and their APIs can be demonstrated.*

### 2.1 Explain the design (slide 5)

**SAY:**

> "Each service has **one job** and **its own database**. No service reads another service's database; they only talk over HTTP."

| Service | Port | Its one job | Own database | Endpoints |
|:--|:-:|:--|:--|:--|
| Book | 8001 | Book catalogue and availability | `books.db` | `GET /health`, `GET /books`, `GET /books/{id}`, `POST /books`, `PATCH /books/{id}/availability` |
| Member | 8002 | Library members | `members.db` | `GET /health`, `GET /members`, `GET /members/{id}`, `POST /members` |
| Borrow | 8003 | Issue and return books; calls the others | `borrows.db` | `GET /health`, `GET /services/status`, `GET /borrow/check`, `POST /borrow`, `POST /return/{id}`, `GET /borrows` |
| Notification | 8004 | Store messages for members | `notifications.db` | `GET /health`, `POST /notifications`, `GET /notifications` |

**DO:** open `services/book_service/main.py` and point at three things:

1. `DB_PATH = os.getenv("DB_PATH", "data/books.db")` — "the database location comes from an environment variable, so Docker can put it on a volume."
2. `init_db()` — "on first start it creates the table and adds 10 books (seeding)."
3. The `@app.get(...)` / `@app.post(...)` lines — "each decorator is one REST endpoint. FastAPI turns the Python function into an HTTP API and checks the input types with Pydantic."

**DO:** open `services/borrow_service/main.py` and point at:

```python
BOOK_URL = os.getenv("BOOK_SERVICE_URL", "http://127.0.0.1:8001")
```

**SAY:**

> "The Borrow Service does not hard-code where the other services are. Locally it uses 127.0.0.1. In Docker, Compose sets this variable to `http://book-service:8001` — the container's **name**. Same code, two environments."

### 2.2 Run each service on its own (no Docker yet)

**DO:** one command per terminal. Start Borrow **last**, because it calls the others.

Terminal `book`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation\services\book_service
python -m uvicorn main:app --port 8001
```

Terminal `member`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation\services\member_service
python -m uvicorn main:app --port 8002
```

Terminal `notify`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation\services\notification_service
python -m uvicorn main:app --port 8004
```

Terminal `borrow`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation\services\borrow_service
python -m uvicorn main:app --port 8003
```

Each terminal shows `Uvicorn running on http://127.0.0.1:800X`.

**SAY (explain the command):**

> "`uvicorn` is the web server. `main:app` means: in the file `main.py`, use the object called `app`. `--port 8001` is the port it listens on. FastAPI defines *what* each request does; Uvicorn is the program that actually listens on the port and passes requests to FastAPI."

### 2.3 Demonstrate the APIs in Swagger

**DO:** open in the browser, one by one:
`http://127.0.0.1:8001/docs`, `:8002/docs`, `:8004/docs`, `:8003/docs`

**SAY:** "FastAPI generates this test page automatically from our code. Every endpoint can be run from here."

On each page: expand an endpoint → **Try it out** → **Execute**.

| Order | Page | Endpoint | Input | Point at |
|:-:|:--|:--|:--|:--|
| 1 | Book | `GET /books` | — | 10 seeded books, 200 OK |
| 2 | Book | `POST /books` | `{"title": "Demo Book", "author": "Me"}` | **201 Created**, new id |
| 3 | Member | `GET /members/{member_id}` | 1 | one member, `"active": true` |
| 4 | Notification | `GET /notifications` | — | list of messages |
| 5 | Borrow | `GET /services/status` | — | all four `"healthy"` → Borrow can reach the other three |
| 6 | Borrow | `POST /borrow` | `{"member_id": 1, "book_id": 3}` | **201**, a `borrow_id`, and a `notification` text |
| 7 | Book | `GET /books/{book_id}` | 3 | now `"available": false` |
| 8 | Borrow | `POST /return/{borrow_id}` | the id from step 6 | 200, book is available again |

**SAY at step 6 (important):**

> "This one request went Client → Borrow → Member → Book → Notification. Look at the four terminals: a new log line appeared in each one."

If step 6 says *Book is already borrowed* (409), use another `book_id`. That itself shows the business rule works.

**SHOW (backup if something fails):** screenshots `01`–`22` in `screenshots/CP1_Microservices/`.

### 2.4 Automatic test of every endpoint

**DO:** terminal `main`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation
python scripts\test_services.py
```

**SAY:** "This script calls every endpoint of the four services and checks the reply. It ends with `ALL CHECKS PASSED`."

### 2.5 Stop the local services

**DO:** press **Ctrl + C** in terminals `book`, `member`, `notify`, `borrow`.

**SAY:** "Checkpoint 1 is complete. I stop them now because Docker will use the same ports."

### IF ASKED (Checkpoint 1)

| Question | Answer |
|:--|:--|
| What is a microservice? | A small program with one responsibility, its own data, and a network API. It can be started, changed and scaled without touching the others. |
| What is REST? | Using HTTP methods on URLs: `GET` reads, `POST` creates, `PATCH` changes part of something. Data is sent as JSON. |
| Why does each service have its own database? | So services stay independent. If Borrow read `books.db` directly, changing the Book Service's table would break Borrow. They share data only through APIs. |
| What do 200, 201, 404, 409, 422, 503 mean here? | 200 OK; 201 created; 404 not found (unknown member/book); 409 conflict (book already borrowed / already returned); 422 wrong input type (FastAPI validation); 503 another service is unreachable. |
| What does `/health` check? | Only that the process is running and answering HTTP. It does not test the database. Docker uses it for the healthcheck. |
| Why `127.0.0.1` and not `localhost`? | On Windows, `localhost` first tries IPv6 (`::1`); Uvicorn listens on IPv4 only, so each call waited about 2 s before falling back. `127.0.0.1` avoids this. We found this problem ourselves. |
| What happens if Notification is down during a borrow? | The borrow still succeeds; the reply says the notification was not sent. Notification is not essential, so we do not fail the whole request ("graceful degradation"). If Book or Member is down, the borrow fails with 503 and nothing is saved. |

---

## 3. Checkpoint 2 — Containerize and deploy

**Manual's completion condition:** *Docker images are built successfully and all microservices are running as containers.*

### 3.1 Why Docker (30 seconds)

**SAY:**

> "Right now each service needs Python and its libraries installed on this laptop, and four terminals. Docker packages each service — Python, libraries and code — into an **image**. A running copy of an image is a **container**, an isolated process with its own file system and network address. Docker Compose then starts all of them with one command."

### 3.2 Walk through one Dockerfile (slide: Dockerfile)

**DO:** open `services/book_service/Dockerfile`.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**SAY, line by line:**

| Line | What it does | Why |
|:--|:--|:--|
| `FROM python:3.12-slim` | Start from an official image that already has Python 3.12 on a small Debian Linux | `slim` is much smaller than the full Python image |
| `WORKDIR /app` | All later commands run in `/app` inside the image | Keeps files in one place |
| `ENV PYTHONDONTWRITEBYTECODE=1` | Python does not write `.pyc` cache files | Keeps the container clean |
| `ENV PYTHONUNBUFFERED=1` | Python prints logs immediately | So `docker logs` shows lines in real time |
| `COPY requirements.txt .` then `RUN pip install ...` | Copy the library list first and install it | **Layer cache**: if only `main.py` changes, Docker reuses the installed-libraries layer, so rebuilds take seconds |
| `--no-cache-dir` | pip does not keep downloaded files | Smaller image |
| `COPY main.py .` | Add our code | Last, because it changes most often |
| `EXPOSE 8001` | Documents the port the app uses | Documentation only; it does not open the port |
| `CMD [...] --host 0.0.0.0` | The command run when the container starts | `0.0.0.0` means "listen on every network interface". With `127.0.0.1` the service would only accept connections from inside its own container, and port mapping would not reach it |

> "All four services have the same Dockerfile pattern; only the port changes. Borrow's `requirements.txt` also has `httpx`, which it uses to call the others."

### 3.3 Build the images

**DO:** terminal `main`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation
docker compose build
```

**SAY:**

> "Compose reads `docker-compose.yml`, finds a `build:` entry for each service, and builds one image from each Dockerfile. You see `CACHED` because the images were built before and nothing changed in those layers. The first build took a few minutes because it downloaded Python and installed the libraries."

**DO:**
```
docker images "library-app/*"
```

**SAY:** "Five images: the four services and the Streamlit client, all tagged `1.0`. Each service image is about 212 MB on disk."

**SHOW (backup):** screenshots `23_docker_compose_build.png`, `24_docker_images.png`.

### 3.4 Walk through `docker-compose.yml` (slide: Compose)

**DO:** open `docker-compose.yml`, scroll to `borrow-service`.

**SAY, pointing at each key:**

| Key | Meaning |
|:--|:--|
| `build: ./services/borrow_service` | Which folder (Dockerfile) to build from |
| `image: library-app/borrow-service:1.0` | Name and tag for the built image |
| `container_name: borrow-service` | Fixed container name |
| `ports: "8003:8003"` | **Laptop port : container port.** Lets the browser, Swagger and Locust on Windows reach the container |
| `environment: DB_PATH, BOOK_SERVICE_URL ...` | Settings passed in from outside. Here Borrow is told the other services are at `http://book-service:8001` etc. — **service names, not IPs** |
| `volumes: borrow-data:/data` | The SQLite file lives on a Docker **volume**, so data survives when the container is deleted or rebuilt |
| `networks: library-net` | All containers join one private network |
| `healthcheck:` | Every 5 s Docker runs a small Python command that calls `/health`. Timeout 3 s, 10 retries |
| `depends_on: ... condition: service_healthy` | Borrow starts only **after** Book, Member and Notification report healthy. The frontend waits for Borrow |

At the top: `x-healthcheck: &healthcheck` is a **YAML anchor** — the healthcheck timing is written once and reused with `<<: *healthcheck`.

At the bottom: `networks: library-net: driver: bridge` creates the network, and `volumes:` declares the four volumes.

### 3.5 Deploy

**DO:**
```
docker compose up -d
```

**SAY:**

> "`up` creates the network, the volumes and the containers, and starts them in the order set by `depends_on`. `-d` means detached — they run in the background. Watch the order: Book, Member and Notification start, become **Healthy**, and only then Borrow starts."

**DO:**
```
docker ps
```

**SAY, pointing at the columns:**

> "Five containers. STATUS shows `Up ... (healthy)` for the four services — that is the healthcheck result. PORTS shows `0.0.0.0:8001->8001/tcp`: laptop port 8001 is forwarded to the container's port 8001. IMAGE shows each container runs from our `library-app` image."

If a service shows `(health: starting)`, wait 10 seconds and run `docker ps` again.

**SHOW (backup):** `25_docker_compose_up.png`, `26_docker_ps_healthy.png`.

### IF ASKED (Checkpoint 2)

| Question | Answer |
|:--|:--|
| Image vs container? | An image is the read-only package (like a program file). A container is a running instance of it (like a running process). One image can run many containers. |
| Container vs virtual machine? | A VM runs a whole guest operating system on virtual hardware. A container shares the host's Linux kernel and only isolates the process (namespaces for isolation, cgroups for CPU/memory limits). So containers start in seconds and use far less memory. On Windows, Docker Desktop runs these Linux containers inside a light WSL2 virtual machine. |
| `EXPOSE` vs `ports`? | `EXPOSE` only documents the port. `ports: "8001:8001"` in Compose actually publishes it to the laptop. |
| What if I delete a container — is the data lost? | No. The database file is on a named volume (`/data`). `docker compose down` removes containers but keeps volumes. Only `docker compose down -v` deletes them. |
| What is a layer? | Each Dockerfile instruction creates a layer. Layers are cached and shared. That is why we copy `requirements.txt` before `main.py`. |
| Why `0.0.0.0`? | Inside a container, `127.0.0.1` means the container itself. Requests forwarded from the laptop arrive on the container's network interface, so the server must listen on all interfaces. |
| What restarts a crashed container? | We did not set a `restart:` policy, so a crashed container stays stopped (we would see it in `docker ps -a`). In production we would add `restart: unless-stopped`. |
| Where do the images come from? | `python:3.12-slim` is downloaded from Docker Hub; our images are built locally from it. |

---

## 4. Checkpoint 3 — Communication between services

**Manual's completion condition:** *Successful communication between the microservices and an end-to-end request.*

### 4.1 The network

**DO:**
```
docker network inspect library-net
```

**SAY:**

> "Compose created a **user-defined bridge network** called `library-net`, subnet `172.18.0.0/16`. Scroll to `Containers`: all five containers are on it, each with its own IP address, for example book-service `172.18.0.2`. But our code never uses these IPs — they can change on every restart."

**SHOW (backup):** `27_network_inspect_config.png`, `28_network_inspect_containers.png`.

### 4.2 Calling a service by name

**DO:**
```
docker exec borrow-service python -c "import urllib.request;print(urllib.request.urlopen('http://book-service:8001/health').read())"
```

**SAY:**

> "`docker exec` runs a command **inside** the running borrow-service container. From inside, we open `http://book-service:8001/health`. Docker's built-in DNS on the user-defined network turns the name `book-service` into its IP address. The reply is the Book Service's health JSON. This is service discovery by name."

Expected output: `b'{"service":"book-service","status":"healthy"}'`

**SHOW (backup):** `29_docker_exec_service_name_call.png`.

### 4.3 End-to-end request from the client

**DO:** open `http://localhost:8501` (the Streamlit **container**).

1. **Dashboard** — "Borrow Service checked the health of the other three over the Docker network; all green."
2. **Borrow / Return** — choose a member and an available book → **Borrow**.
   **SAY:** "Client → Borrow → Member (is the member active?) → Book (is it available? then mark it borrowed) → Borrow saves the record in its own database → Notification stores a message → the result comes back to the client." Point at the green success box and the blue notification box.
3. **Books** — the book now shows `available = false`.
4. **Notifications** — the new message is at the top.

**DO (proof from the logs):**
```
docker compose logs --tail 5 borrow-service book-service member-service notification-service
```

**SAY:** "Each container's log shows its part of that one request: `POST /borrow` in Borrow, `GET /members/1` in Member, `GET` and `PATCH` in Book, `POST /notifications` in Notification."

**SHOW (backup):** `30`–`34` in `screenshots/CP3_Communication/`.

### 4.4 Optional: fault isolation (strong point, 1 minute)

**DO:**
```
docker stop notification-service
```

Dashboard → `notification-service` shows **unreachable**, others stay green. Borrow a book → it still succeeds, the info box says *Not sent (Notification Service unavailable)*.

```
docker start notification-service
docker ps
```

**SAY:** "One container failed and the rest of the application kept working. In a monolith, one crashed part stops everything."

### IF ASKED (Checkpoint 3)

| Question | Answer |
|:--|:--|
| How does Borrow find Book? | By the name `book-service`, given in the `BOOK_SERVICE_URL` environment variable. Docker's embedded DNS (at `127.0.0.11` inside each container) resolves it on the user-defined network. |
| Why not use `localhost:8001` inside the container? | Inside a container `localhost` is that container itself. Book is in a different container. |
| Does the default bridge network do name resolution? | No. Only user-defined networks have automatic DNS by name. That is why Compose creates `library-net`. |
| How do the services talk? | Plain HTTP with JSON, using the `httpx` library in Borrow. One shared `httpx.Client` keeps connections open (keep-alive), with a 5-second timeout. |
| Is the network reachable from outside? | Only through the published ports (8001–8004, 8501). Container-to-container traffic stays on `library-net`. |
| What if two people borrow the same book at the same moment? | Both could pass the "available" check before either marks it borrowed. A real system would need locking or a conditional update. We did not handle this; it is a known limitation (distributed consistency). |

---

## 5. Checkpoint 4 — Varying workloads and monitoring (most important)

**Manual's completion condition:** *Performance measurements are collected for all workload levels.*

The evaluator will most likely **not** ask you to run the full test. He will look at the screenshots and ask **which command produced each one** and **what each file does**. This section answers exactly that.

### 5.1 Which API we tested, and why (slide: workload design)

**SAY:**

> "We tested `GET /borrow/check?member_id=…&book_id=…` on the Borrow Service. Three reasons:
> 1. **It crosses services.** Every request makes Borrow call Member and Book — so it tests the containers *and* the network between them. It is exactly the manual's Client → Service 1 → Service 2 / Service 3 path.
> 2. **It is read-only.** It changes no data, so all five workload levels run under identical conditions. If we used `POST /borrow`, all 10 books would be borrowed within the first second and every later request would fail with 409.
> 3. **It does real work:** two outgoing HTTP calls, two SQLite reads, JSON parsing."

**Workload levels (exactly the manual's suggestion):**

| Test | Concurrent requests (Locust users) | Duration |
|:-:|:-:|:-:|
| W1 | 1 | 60 s |
| W2 | 2 | 60 s |
| W3 | 4 | 60 s |
| W4 | 8 | 60 s |
| W5 | 16 | 60 s |

10-second pause between levels. Run started 00:01:28 IST on 04-Oct-2026 (W5 started 00:06:19).

### 5.2 Tool: Locust, and `loadtest/locustfile.py`

**DO:** open `loadtest/locustfile.py`.

```python
class LibraryUser(HttpUser):
    wait_time = constant(0)

    @task
    def check_borrow(self):
        member_id = random.randint(1, 5)
        book_id = random.randint(1, 10)
        self.client.get(f"/borrow/check?member_id={member_id}&book_id={book_id}",
                        name="/borrow/check")
```

**SAY, line by line:**

| Line | Meaning |
|:--|:--|
| `class LibraryUser(HttpUser)` | Describes **one simulated user**. Locust creates as many copies as we ask for (`-u`). Each user runs in its own lightweight green thread (gevent). |
| `wait_time = constant(0)` | After a reply arrives, the user sends the next request **immediately**, with no thinking time. So each user always has exactly **one** request in progress. **Number of users = number of concurrent requests.** This is how "1, 2, 4, 8, 16 concurrent requests" from the manual becomes "1, 2, 4, 8, 16 users". |
| `@task` | The action each user repeats in a loop. |
| `random.randint(1, 5)` / `(1, 10)` | A random existing member (1–5) and book (1–10), so we do not hit only one database row. All IDs exist, so a correct reply is always 200. |
| `self.client.get(...)` | Sends the HTTP GET and **measures the time** from sending to receiving the full reply. If the status is not 2xx or the request errors, Locust counts it as a **failure**. |
| `name="/borrow/check"` | Groups all requests under one name, otherwise each different ID combination would be a separate row in the statistics. |

The host (`http://127.0.0.1:8003`, the Borrow container's published port) is given on the command line, not in the file.

### 5.3 Automation: `loadtest/run_workloads.py`

**DO:** open `loadtest/run_workloads.py`.

**SAY:** "Running five levels by hand, and recording `docker stats` at the same time, is error-prone. This script does all of it in one run. It has four parts."

**Part 1 — the settings (top of file):**

```python
WORKLOADS = [("W1", 1), ("W2", 2), ("W3", 4), ("W4", 8), ("W5", 16)]
CONTAINERS = ["book-service", "member-service", "borrow-service", "notification-service"]
```
"The five levels and the four containers to monitor."

**Part 2 — `StatsSampler`, the monitoring thread:**

> "This is a background thread. In a loop, it runs
> `docker stats --no-stream --format "{{json .}}" book-service member-service borrow-service notification-service`.
> `--no-stream` means: take **one** measurement and exit, instead of a live screen. `--format "{{json .}}"` prints each container as one line of JSON so the script can read it. Each call takes about 2 seconds, because Docker measures CPU usage over a short interval. So we get about **30 samples per container per 60-second level** (the CSV shows 30–31).
> For every sample it stores: time, workload label, container name, CPU %, memory (converted to MiB by `to_mib()`), memory %.
> The main program sets `sampler.label = "W3"` when W3 starts and sets it back to `None` during the 10-second pause, so **samples from the pauses are thrown away**. Only samples taken while load was running are kept."

**Part 3 — `run_locust()`, one workload level:**

It runs this command (shown here for W3):

```
python -m locust -f loadtest\locustfile.py --headless -u 4 -r 4 -t 60s --host http://127.0.0.1:8003 --csv results\raw\W3_4u --only-summary --stop-timeout 5
```

| Flag | Meaning |
|:--|:--|
| `-f loadtest\locustfile.py` | Which user behaviour to use |
| `--headless` | No web UI; run from the terminal and stop by itself |
| `-u 4` | 4 users = 4 concurrent requests |
| `-r 4` | Spawn rate: start 4 users per second, so all users are running within 1 second |
| `-t 60s` | Run for 60 seconds, then stop |
| `--host http://127.0.0.1:8003` | Send requests to the Borrow Service container |
| `--csv results\raw\W3_4u` | Save the statistics to CSV files starting with this name (`W3_4u_stats.csv`, `_stats_history.csv`, `_failures.csv`, `_exceptions.csv`) |
| `--only-summary` | Print only the final table, not a table every few seconds |
| `--stop-timeout 5` | When time is up, give requests still in flight up to 5 s to finish |

> "After Locust finishes, the script opens `W3_4u_stats.csv`, takes the **Aggregated** row, and reads: Request Count, Failure Count, Average, Median, 95 %, Max response time and Requests/s."

**Part 4 — `main()`, putting it together:**

1. Start the sampler thread.
2. For each of W1…W5: set the label → run Locust for 60 s → clear the label → print the result dictionary → wait 10 s (cooldown, so one level does not affect the next).
3. Stop the sampler.
4. Save every raw sample to `results/raw/docker_stats_samples.csv`.
5. **Group the samples by workload and container** → average CPU, maximum CPU, average memory, sample count → `results/container_usage.csv`.
6. **Sum the four containers' averages** for each workload → `total_cpu_pct`, `total_mem_mib`, and join them with the Locust numbers → `results/observation_table.csv`.
7. Print the final observation table (screenshot 45).

**The commands we ran for the measurement** (from the project folder, with `docker compose up -d` running):

Terminal 1 — the automated test:
```
python loadtest\run_workloads.py
```
Terminal 2 — a live view for the screenshots:
```
docker stats book-service member-service borrow-service notification-service
```

Defaults used: `--duration 60`, `--cooldown 10`, `--host http://127.0.0.1:8003`.

### 5.4 Monitoring: what `docker stats` shows (slide: docker stats)

**SHOW:** `43_docker_stats_during_W5.png`.

| Column | Meaning | Value for borrow-service in W5 |
|:--|:--|:--|
| CPU % | CPU used, where **100 % = one full core**. This laptop has 16 logical CPUs, so the maximum possible is 1600 %. | **126.66 %** (about 1.27 cores) |
| MEM USAGE / LIMIT | RAM used by the container / the most it may use (no limit set, so it shows the WSL2 VM's memory, 7.664 GiB) | 43.98 MiB / 7.664 GiB |
| MEM % | Memory usage as a percentage of the limit | 0.56 % |
| NET I/O | Total bytes received / sent since the container started (a running total, not a rate) | 45.2 MB / 45 MB |
| BLOCK I/O | Bytes read / written to disk | 9.79 MB / 135 kB |
| PIDS | Number of processes and threads in the container | **17** (it was 3 during W1) |

**SAY:**

> "Borrow is at 127 % while Book and Member are at about 35 %. PIDS rose from 3 to 17 because Uvicorn runs our normal `def` endpoints in a **thread pool** — more concurrent requests, more threads. Notification shows 0.18 % in this snapshot because `/borrow/check` never calls it."

### 5.5 Every Checkpoint 4 screenshot, and the command behind it

This is the table to know by heart.

| # | What it shows | Command that produced it | Numbers to read out |
|:-:|:--|:--|:--|
| 35 | Locust **web UI**, Statistics tab, 8 users | `python -m locust -f loadtest\locustfile.py --host http://127.0.0.1:8003`, then in the browser at `http://localhost:8089`: 8 users, ramp-up 8, Start | 11,984 requests, **0 fails**, median 52 ms, average 53.97 ms, 95 % 74 ms, **148 RPS** |
| 36 | Locust web UI, Charts tab (same run) | same | RPS climbs to ~148 and stays flat; median ~52 ms, 95th ~74 ms; users flat at 8 |
| 37 | `docker stats`, **idle**, before the test | `docker stats book-service member-service borrow-service notification-service` | CPU 0.18–0.32 % for every container; memory 104.7 / 78.1 / 42.5 / 35.4 MiB |
| 38 | `docker stats` **during W1** | same `docker stats` command, terminal 2 | borrow 54.03 %, book 36.74 %, member 35.03 %, notification 15.27 %; borrow PIDS 3 |
| 39 | Console output of **W1** (1 user) | `python loadtest\run_workloads.py`, terminal 1 | Locust table: 5,228 requests, 0 fails, avg 11 ms, 89.09 req/s; then the dictionary from the CSV: 5,205 requests, 11.04 ms, **89.45 req/s** |
| 40 | Console output of W2 (2 users) | same script | (from CSV) 9,348 requests, 12.32 ms, **160.58 req/s** |
| 41 | Console output of W3 (4 users) | same script | 9,361 requests, 24.69 ms, **160.83 req/s** |
| 42 | Console output of W4 (8 users) | same script | 8,725 requests, 53.16 ms, **149.93 req/s** |
| 43 | `docker stats` **during W5** | `docker stats ...`, terminal 2 | borrow **126.66 %**, PIDS 17; book 35.71 %, member 34.79 % |
| 44 | Console output of W5 (16 users) | same script | 8,581 requests, 108.19 ms, **147.48 req/s** |
| 45 | Final **observation table** printed at the end | same script (last lines) | the table in Section 6.1 |

**SAY about screenshots 35–36:**

> "Before the scripted run we did a one-off run in the Locust web UI with 8 users. It gave 148 req/s at 54 ms. The scripted W4, also 8 users, gave 149.9 req/s at 53.2 ms — almost identical. So the measurement repeats well."

**IF ASKED: "Why does screenshot 39 say 5,228 requests but your table says 5,205?"**

> "Two outputs of the same run. Locust writes its CSV at its last one-second tick, about 0.3 seconds before it prints the final console table. In that 0.3 s about 23 more requests completed (1 user × ~89 req/s × 0.3 s ≈ 27). The difference is under 1 %; averages and throughput agree to within 1 %. We used the CSV values everywhere, because those are what the script saved."

**IF ASKED: "Why is the maximum 255 ms on the console but 41 ms in the table?"**

> "Same reason: the console summary includes requests caught during Locust's shutdown, after the CSV was written. The CSV maximum is for the 60-second measurement window."

### 5.6 Optional live demo of Checkpoint 4 (2 minutes, only if he wants to see it run)

Do **not** run `run_workloads.py` live — it takes about 6 minutes and **overwrites** `results/`, which the README and graphs are built from.

Instead show a short live run:

Terminal `notify` (re-use it):
```
docker stats book-service member-service borrow-service notification-service
```

Terminal `main`:
```
cd C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation
python -m locust -f loadtest\locustfile.py --host http://127.0.0.1:8003
```

Browser → `http://localhost:8089` → Number of users **8**, Ramp up **8** → **Start**.

**SAY while it runs:** "RPS goes to about 150 and stays flat. Failures stay at 0. In the `docker stats` terminal, borrow-service rises above 100 % CPU while book and member stay around 35–50 %. This is the bottleneck we analyse in Checkpoint 5." Click **Stop** after ~30 s. Ctrl + C in both terminals.

### IF ASKED (Checkpoint 4)

| Question | Answer |
|:--|:--|
| What is concurrency here? | The number of requests in progress at the same moment. With `wait_time = constant(0)` each Locust user always has exactly one request in progress, so users = concurrency. |
| Throughput vs response time? | Throughput = requests **completed per second** (req/s). Response time = how long **one** request takes, measured by Locust from sending it to receiving the full reply. |
| How is throughput calculated? | Locust's "Requests/s" = total requests ÷ test duration. Example W1: 5,205 ÷ ~58.2 s ≈ 89.45. |
| What does "failed" mean? | Any reply that is not 2xx, a timeout, or a connection error. We had 0 at every level. |
| Why 60 seconds per level? | Long enough to get thousands of requests and about 30 `docker stats` samples per container, short enough to run all five levels in about 6 minutes. |
| Why a 10-second pause? | So the CPU settles and one level's queue does not spill into the next. Samples from the pause are discarded. |
| Is Locust affecting the results, since it runs on the same laptop? | It shares the CPU, but the laptop has 16 logical CPUs and the whole test used only about 2–4 cores, so the effect is small. A separate machine would be cleaner; we list it as a limitation. |
| How is CPU % measured? | Docker reads the container's cgroup CPU counter twice, a short time apart, and divides the CPU time used by the elapsed time. 100 % = one core fully busy. |
| What are the raw files? | `results/raw/W*_stats.csv` (Locust totals), `W*_stats_history.csv` (one row per second), `W*_failures.csv` and `W*_exceptions.csv` (empty — no failures), `docker_stats_samples.csv` (every monitoring sample). |

---

## 6. Checkpoint 5 — Results, graphs and analysis (most important)

**Manual's completion condition:** *Students demonstrate the complete experiment and explain their measured results.*

### 6.1 The observation table (slide: observation table)

**DO:** open `results/observation_table.csv` or show the slide.

| Workload | Concurrency | Total requests | Avg (ms) | Median (ms) | 95th pct (ms) | Throughput (req/s) | Failed | CPU, 4 services (%) | Memory, 4 services (MiB) |
|:-:|:-:|--:|--:|--:|--:|--:|:-:|--:|--:|
| W1 | 1 | 5,205 | 11.04 | 11 | 14 | 89.45 | 0 | 128.2 | 269.8 |
| W2 | 2 | 9,348 | 12.32 | 12 | 17 | 160.58 | 0 | 190.5 | 268.4 |
| W3 | 4 | 9,361 | 24.69 | 24 | 35 | 160.83 | 0 | 234.7 | 257.4 |
| W4 | 8 | 8,725 | 53.16 | 52 | 74 | 149.93 | 0 | 230.3 | 270.4 |
| W5 | 16 | 8,581 | 108.19 | 100 | 160 | 147.48 | 0 | 225.7 | 269.1 |
| **Total** | | **41,220** | | | | | **0** | | |

**SAY — where each column comes from:**

> "Requests, failures, response times and throughput come from Locust's CSV — the **Aggregated** row of `W*_stats.csv`. CPU and memory come from `docker stats`: for each workload we averaged about 30 samples per container, then **added the four containers together**. So CPU 234.7 % at W3 means the four services together used about 2.35 cores on average."

**SAY — how to read it in one minute:**

> "Read it top to bottom.
> - **W1 → W2**: users doubled, throughput went from 89 to 161 req/s (+80 %), response time stayed almost the same (11 → 12 ms). The system had spare capacity.
> - **W2 → W3**: users doubled again, but throughput stayed at 161 — it stopped growing. Response time doubled to 25 ms. This is the **saturation point**.
> - **W3 → W5**: users ×4, throughput even dropped a little to 147, response time ×4 to 108 ms. Extra users only wait in a queue.
> - **Failed = 0** at every level, 41,220 requests in total. The system became slower but never broke.
> - **Memory** stayed at 257–270 MiB — it does not depend on load."

**Per-container table (point at Borrow's column):**

| Workload | borrow-service CPU % | book-service | member-service | notification-service |
|:-:|--:|--:|--:|--:|
| W1 | **51.0** | 32.1 | 32.2 | 12.8 |
| W2 | **84.0** | 46.9 | 47.1 | 12.5 |
| W3 | **119.9** | 50.3 | 50.9 | 13.6 |
| W4 | **127.1** | 45.3 | 45.8 | 12.1 |
| W5 | **126.6** | 44.0 | 44.1 | 11.0 |

| Workload | borrow MiB | book MiB | member MiB | notification MiB |
|:-:|--:|--:|--:|--:|
| W1 | 44.0 | 107.6 | 81.8 | 36.5 |
| W5 | 45.4 | 111.1 | 76.6 | 36.0 |

### 6.2 How the graphs were made

**DO:** open `scripts/generate_graphs.py`.

**SAY:**

> "The graphs are not drawn by hand. This script reads `observation_table.csv` and `container_usage.csv` with **pandas** and draws nine figures with **matplotlib** into the `graphs/` folder. Command: `python scripts\generate_graphs.py`. If the CSVs change, the graphs change.
> In the line graphs the x-axis is **log base 2**, so 1, 2, 4, 8, 16 are evenly spaced — each step is a doubling of the load. The service colours are the same in every figure: Borrow purple, Book blue, Member green, Notification orange."

The first four figures are exactly the manual's four recommended graphs. Figures 5–9 are extra analysis.

### 6.3 Fig. 1 — Concurrent requests vs response time (manual graph 1)

**SHOW:** `graphs/01_response_time_vs_concurrency.png`

**Axes:** x = concurrent users (1–16, log scale). y = response time in ms. Three lines: **average** (blue, labelled), **median** (green dashed), **95th percentile** (red dashed).

**SAY:**

> "From 1 to 2 users the response time is almost flat — 11.0 to 12.3 ms — because the system still has free capacity, so the second user does not wait.
> From 2 users on, the response time **doubles every time the users double**: 12.3 → 24.7 → 53.2 → 108.2 ms. That is the signature of a **saturated** system: the extra requests are not served faster, they wait in a queue in front of the busiest service.
> The red 95th-percentile line grows faster than the average — from 14 to 160 ms. The slowest 5 % of requests suffer most from queueing."

**Terms he may test:**
- *Median*: half the requests were faster than this. W5: 100 ms.
- *95th percentile*: 95 % of requests were faster than this. W5: 160 ms — so 5 % took between 160 ms and the maximum of 277 ms.
- *Why average > median at W5 (108 vs 100)*: a few slow requests pull the average up; the median ignores how slow the slowest ones are.

### 6.4 Fig. 2 — Concurrent requests vs throughput (manual graph 2)

**SHOW:** `graphs/02_throughput_vs_concurrency.png`

**Axes:** x = concurrent users (log scale). y = throughput in requests per second.

**SAY:**

> "With one user we get 89.5 req/s. That number is easy to check: one user waits for each reply, each reply takes about 11 ms, and 1000 ÷ 11 ≈ 90 requests per second.
> With two users throughput rises 80 % to 160.6. Then it stops: 160.8 at 4 users is the **peak — the maximum capacity of this setup for this API**.
> With 8 and 16 users it falls slightly to 149.9 and 147.5 — about 8 % below the peak. With more users, the overloaded Borrow Service runs more threads that compete for the same CPU, and switching between them wastes some time."

**Useful extra:** throughput **per user** falls as users increase: 89 → 80 → 40 → 19 → 9 req/s per user. The total is fixed; it is shared between more users.

### 6.5 Fig. 5 — Throughput vs response time (the "knee")

**SHOW:** `graphs/05_throughput_vs_response_time.png`

**Axes:** x = throughput (req/s). y = average response time (ms). Each point is one workload, labelled W1 (1) … W5 (16).

**SAY:**

> "This puts both measures on one picture. From W1 to W2 the point moves **to the right** — more work done at almost the same speed. That is useful load. After W2–W3 the points go **straight up** — much slower, no extra work done. That is pure queueing. The bend is the **knee**. The best operating point for this system is **2 to 4 concurrent requests**: maximum throughput at 12–25 ms."

### 6.6 Fig. 3 — Concurrent requests vs CPU utilisation (manual graph 3)

**SHOW:** `graphs/03_cpu_vs_concurrency.png`

**Axes:** x = workload W1–W5 (users in brackets). y = average CPU % per container (100 % = one core). Four coloured bars per workload, one per container, with the value on top.

**SAY:**

> "**Borrow (purple)** climbs steeply: 51 → 84 → 120 → 127 → 127 %. From W3 it stays at about 1.2–1.3 cores and cannot go higher. This is exactly where throughput stopped growing in Fig. 2 — so the CPU of the Borrow Service is the **bottleneck**.
> **Book and Member** rise to 45–50 % and then stay flat or even drop slightly. They are not busy — they are waiting for work from Borrow.
> **Notification** is not called by `/borrow/check` at all, yet it shows a steady 11–14 %. That is not our load — it is Docker's **healthcheck** (explained in 6.11)."

### 6.7 Fig. 7 — Which microservice uses the most CPU?

**SHOW:** `graphs/07_cpu_share_per_service.png`

**Axes:** x = workload. y = share of the application's total CPU (each bar adds up to 100 %). Each coloured part = one container's average CPU ÷ the sum of all four.

**SAY:**

> "This answers the manual's question 'which microservice consumes more resources'. Borrow's share grows from **40 % at W1 to 56 % at W5**. Under load it uses more CPU than the other three put together."

How 40 % is calculated: W1 Borrow 51.0 ÷ (51.0 + 32.1 + 32.2 + 12.8 = 128.2) = 39.8 %. W5: 126.6 ÷ 225.7 = 56.1 %.

### 6.8 Fig. 4 — Concurrent requests vs memory utilisation (manual graph 4)

**SHOW:** `graphs/04_memory_vs_concurrency.png`

**Axes:** x = workload. y = average memory in MiB per container. Four bars per workload.

**SAY:**

> "Memory is **flat** for every container. From 1 to 16 users the total stays between 257 and 270 MiB. Each request is small and finishes in milliseconds, so nothing builds up in memory.
> The differences between containers — Book about 108, Member about 80, Borrow about 44, Notification about 36 MiB — were already there **before** the test, at idle (screenshot 37: 104.7, 78.1, 42.5, 35.4 MiB). They are not caused by the load.
> The whole application used under 300 MiB of the 7.66 GiB available. **Memory was not a limiting factor; CPU was.**"

(MiB = mebibyte = 1024 × 1024 bytes. Docker reports MiB.)

### 6.9 Fig. 6 — Successful vs failed requests

**SHOW:** `graphs/06_requests_and_failures.png`

**Axes:** x = workload. y = requests completed in the 60-second window. Green = successful, red = failed (stacked; red is zero height).

**SAY:**

> "All **41,220** requests succeeded at every level — 0 failures, 0 exceptions. The bar heights differ only because throughput differs: W2 and W3 completed the most (about 9,350 each) because that is where throughput peaked. The slowest single request was 277 ms, far below the 5-second timeout our Borrow Service uses for its calls. The system got slower under load, but it never broke."

### 6.10 Fig. 9 — Little's Law check

**SHOW:** `graphs/09_littles_law_check.png`

**Axes:** x = users we set in Locust. y = users calculated from our measurements, N = throughput × average response time. Dotted diagonal = perfect match. Both axes log scale.

**SAY:**

> "Little's Law is a basic rule of queueing: **users in the system = throughput × time each one spends**, N = X × R. For our closed test, N should equal the number of Locust users.
> W3: 160.83 req/s × 0.02469 s = **3.97** ≈ 4 users. All five points sit on the diagonal: 0.99, 1.98, 3.97, 7.97, 15.96 — within 1 %.
> This proves two things. First, our throughput and response-time numbers are **consistent with each other** — they were not mixed up between runs. Second, it explains the response-time graph: once throughput is fixed at about 150–160 req/s, R = N ÷ X, so **doubling N must double R**."

| Workload | Users N | X (req/s) | R (s) | X × R |
|:-:|:-:|--:|--:|--:|
| W1 | 1 | 89.45 | 0.01104 | 0.99 |
| W2 | 2 | 160.58 | 0.01232 | 1.98 |
| W3 | 4 | 160.83 | 0.02469 | 3.97 |
| W4 | 8 | 149.93 | 0.05316 | 7.97 |
| W5 | 16 | 147.48 | 0.10819 | 15.96 |

### 6.11 Fig. 8 — Summary dashboard

**SHOW:** `graphs/08_summary_dashboard.png`

**SAY:** "One-page summary: peak throughput **160.8 req/s at 4 users**; average response time **11 → 108 ms** from W1 to W5; **0 failed of 41,220**; busiest service **Borrow**, about 102 % CPU averaged over all five levels; and the full observation table below."

### 6.12 Answers to the manual's analysis questions

**Q3 — Compare performance at different workload levels.**

| Level | Behaviour |
|:--|:--|
| W1 (1) | Under-loaded. Fastest (11 ms) but only 89 req/s, because one user waits for each reply. |
| W2 (2) | Best balance. Almost the same speed (12 ms), 80 % more throughput (161 req/s). |
| W3 (4) | Saturation point. Peak throughput (161 req/s) but response time doubled (25 ms). |
| W4 (8) | Overloaded. No more throughput (150), response time doubled again (53 ms). |
| W5 (16) | Heavily overloaded. 147 req/s, 108 ms average, 160 ms 95th percentile. Still 0 failures. |

**Q4 — How does increasing workload affect the application?**

1. Throughput rises only until the busiest service is full — here at 2–4 concurrent requests, about 160 req/s.
2. After that, more load only adds waiting time: response time grows in proportion to users (Little's Law), the 95th percentile even faster.
3. Too much concurrency costs a little throughput (−8 % at 16 users) because of thread switching in the overloaded service.
4. CPU rises until it hits a ceiling; memory does not change.

**Q5 — Which microservice consumes more resources? Why?**

> "The **Borrow Service**: 120–127 % CPU from W3 onwards, against 44–51 % for Book and Member and 11–14 % for Notification. Two reasons:
> 1. **It does the most work per request.** For each `/borrow/check` it receives the client's request, makes **two outgoing HTTP calls**, parses two JSON replies, and builds its own reply. Book and Member each answer one simple request with one SQLite lookup.
> 2. **It runs one Uvicorn worker process, and Python has the GIL** (Global Interpreter Lock): one Python process runs Python code on only about one core at a time. The extra 20–30 % above 100 % is work done while the GIL is released — mainly waiting on the network. So Borrow cannot use the laptop's other idle cores; it becomes the bottleneck at about 160 req/s.
> For memory, Book uses the most (~108 MiB), but it was the same at idle and at every load level, so it is not caused by the workload."

**Q6 — Explain any performance degradation or failures.**

> "No failures — 0 of 41,220.
> Degradation:
> 1. Response time 11 → 108 ms — queueing in front of the CPU-saturated Borrow Service.
> 2. Throughput fell 8 % after its peak — with 8–16 users Borrow runs more threads (PIDS 3 → 17) that compete for the GIL.
> 3. Long tail — 95th percentile 160 ms vs median 100 ms at W5.
>
> **A hidden overhead we discovered:** every 5 seconds Docker runs `python -c "import urllib.request; …"` inside **each** container for the healthcheck. Starting a new Python interpreter is CPU-heavy: notification-service samples spiked to 66–69 % although it received no test traffic. Averaged, that is about **11–14 % CPU per container, all the time**. Fix: a longer interval such as 30 s, or a lighter check like `curl`."

### 6.13 How to remove the bottleneck (if asked)

| Option | Expected effect |
|:--|:--|
| Run Borrow with more Uvicorn workers (`--workers 4`) | Several processes → several GILs → uses more cores; throughput should rise well above 160 req/s |
| Run several Borrow containers behind a load balancer | Same idea, at container level (note: our compose file fixes `container_name` and port 8003, so `--scale` would need those removed and a load balancer in front) |
| `async def` endpoints with `httpx.AsyncClient`, calling Member and Book **in parallel** | Lower response time per request, fewer threads |
| Lighter or less frequent healthchecks | Frees about 11–14 % CPU per container |
| Cache member/book lookups for a few seconds | Fewer downstream calls per request |

We did not implement these; they are what we would try next.

### 6.14 Limitations (say them before he finds them)

- Locust ran on the same laptop as Docker (shares the CPU; effect small with 16 logical CPUs).
- One 60-second run per level (the repeat at 8 users — 148 vs 149.9 req/s — suggests the variation is small).
- `docker stats --no-stream` gives snapshots about every 2 s, about 30 per level; short spikes are sampled unevenly.
- No CPU or memory limits on containers, so results depend on this laptop.
- Docker Desktop runs containers inside a WSL2 VM — small virtualisation overhead.
- Container timestamps are UTC, about 5.5 hours behind IST.

---

## 7. Closing — 1 minute

**SHOW:** conclusion slide.

**SAY:**

> "To summarise:
> 1. We built four independent FastAPI microservices, each with its own database and REST API, and tested each one on its own.
> 2. We containerized each with its own Dockerfile and deployed all of them with one Docker Compose command, with healthchecks controlling the start order.
> 3. The services communicate over the `library-net` network by **service name**, and an end-to-end borrow request passes through all four.
> 4. We load-tested at 1, 2, 4, 8 and 16 concurrent requests while monitoring every container.
> 5. The system peaked at **about 160 requests per second**, after which response time grew in proportion to load, exactly as Little's Law predicts. The **Borrow Service's CPU** was the bottleneck because it does the most work and one Python process is limited to about one core. Memory stayed flat, and there were **zero failures in 41,220 requests**.
>
> Thank you."

---

## 8. Hard questions and honest answers

These are the questions that separate understanding from memorising. Answer short, then stop.

| # | Question | Answer |
|:-:|:--|:--|
| 1 | Why is W1 only 89 req/s if the system can do 160? | One user sends one request, waits ~11 ms for the reply, then sends the next. 1000 ms ÷ 11 ms ≈ 90 per second. The system is idle most of the time; it is limited by the user, not the server. |
| 2 | Why does throughput stop at ~160? | Borrow's CPU is full (about 1.2–1.3 cores). It cannot process requests faster, so extra users just wait. |
| 3 | How can CPU be 127 % — more than 100? | `docker stats` counts 100 % per core. 127 % = 1.27 cores. With 16 logical CPUs the maximum would be 1600 %. |
| 4 | If it is limited to one core by the GIL, how does it reach 127 %? | The GIL is released while a thread waits on the network or does certain low-level work, so a bit more than one core can be used — but not much more. |
| 5 | Why did throughput *drop* from 160.8 to 147.5? | More threads in the overloaded Borrow process (PIDS 3 → 17) compete for the GIL; switching between them costs time. |
| 6 | Why is response time almost exactly doubling? | Little's Law: R = N ÷ X. Throughput X is fixed at ~150–160, so R grows in proportion to N. |
| 7 | Why does Notification use 11–14 % CPU when it is never called in the test? | Docker's healthcheck starts a new Python interpreter in the container every 5 s. That costs CPU continuously. |
| 8 | Why didn't you load-test `POST /borrow`? | It changes data. All 10 books would be borrowed in the first second and every request after that would correctly fail with 409, so we would measure errors, not performance. |
| 9 | Users vs concurrency — are they really equal? | Yes, because `wait_time = constant(0)`: each user has exactly one request in flight at all times. Little's Law confirms it: calculated N = 0.99, 1.98, 3.97, 7.97, 15.96. |
| 10 | Why is memory flat? | Each request is small and short-lived; nothing is cached or accumulated. Memory is mostly Python, FastAPI and libraries loaded at start-up. |
| 11 | Why does Book use more memory than Borrow? | It was already ~105 MiB at idle, before any load, and stayed the same at every level. It is a start-up difference, not caused by the load test. We did not investigate it further because it does not change with load. |
| 12 | What does median 100 ms but average 108 ms tell you? | The distribution has a tail of slower requests that pulls the average up. |
| 13 | Why does the Locust console show more requests than your table? | The CSV is written ~0.3 s before the console summary; those extra requests are under 1 %. We report the CSV. |
| 14 | Which value is "response time" in your table? | Average response time from Locust's Aggregated row. Median and 95th percentile are reported too. |
| 15 | How do you know your graphs are not made up? | They are generated by `scripts/generate_graphs.py` from the CSVs that `run_workloads.py` wrote; the raw Locust files and every `docker stats` sample are in `results/raw/`. The numbers match the screenshots, and Little's Law holds within 1 %. |
| 16 | What would happen at 32 or 64 users? | Throughput would stay around 150 req/s (or drop slightly); response time would keep doubling — about 215 and 430 ms — following R = N ÷ X. Eventually requests could hit the 5 s timeout. We did not measure this. |
| 17 | How many cores does the laptop have and how many did the app use? | 16 logical CPUs. At the peak the four services together used about 2.3 cores (234.7 %). Most of the machine was idle — the limit was one process, not the hardware. |
| 18 | Why `python -m locust` instead of `locust`? | It runs Locust with the same Python that has it installed, so it works even if the `locust` command is not on the PATH. |
| 19 | What is the Streamlit app's role? | It is only the **client** (user interface). It has no database; it calls the four services' REST APIs. It is not one of the microservices. |
| 20 | What happens on `docker compose up -d` step by step? | Build images if missing → create network `library-net` → create the 4 volumes → start Book, Member, Notification → wait until healthy → start Borrow → wait until healthy → start the frontend. |

---

## 9. Numbers to remember

| What | Value |
|:--|:--|
| Services / containers / images | 4 services + 1 client = 5 containers, 5 images |
| Ports | Book 8001, Member 8002, Borrow 8003, Notification 8004, Streamlit 8501, Locust UI 8089 |
| Network | `library-net`, bridge, 172.18.0.0/16 |
| Workloads | W1–W5 = 1, 2, 4, 8, 16 users, 60 s each, 10 s cooldown |
| Total requests / failures | 41,220 / 0 |
| Throughput | 89.45 → 160.58 → **160.83 (peak, W3)** → 149.93 → 147.48 req/s |
| Average response time | 11.04 → 12.32 → 24.69 → 53.16 → 108.19 ms |
| 95th percentile | 14 → 17 → 35 → 74 → 160 ms |
| Borrow CPU | 51 → 84 → 120 → 127 → 127 % |
| Book / Member CPU | ~32 → ~50 → ~44 % |
| Notification CPU (healthcheck only) | 11–14 % |
| Total memory | 257–270 MiB, flat |
| Borrow PIDS | 3 (W1) → 17 (W5) |
| Little's Law N | 0.99, 1.98, 3.97, 7.97, 15.96 |
| Locust UI repeat (8 users) | 148 RPS, 53.97 ms, 11,984 requests, 0 fails |
| Healthcheck | every 5 s, timeout 3 s, 10 retries |
| Base image | `python:3.12-slim`; service images ~212 MB |
| Tools | FastAPI, Uvicorn, SQLite, httpx, Streamlit, Docker 29.8, Compose v5.5.1, Locust 2.46.6, pandas, matplotlib |

---

## 10. Command cheat sheet

All from the project folder unless shown otherwise:
`C:\Users\Asus\Desktop\Cloud_computing\PGC\PGC_lab\CC_github\CC_lab_evaluation`

| Purpose | Command |
|:--|:--|
| Run one service locally | `cd services\book_service` then `python -m uvicorn main:app --port 8001` |
| Test all endpoints | `python scripts\test_services.py` |
| Streamlit locally | `cd frontend` then `python -m streamlit run app.py` |
| Build images | `docker compose build` |
| List images | `docker images "library-app/*"` |
| Start everything | `docker compose up -d` |
| Running containers | `docker ps` |
| Logs | `docker compose logs borrow-service` / `docker compose logs --tail 5 <names>` |
| Network | `docker network inspect library-net` |
| Call by name from inside | `docker exec borrow-service python -c "import urllib.request;print(urllib.request.urlopen('http://book-service:8001/health').read())"` |
| Volumes | `docker volume ls` |
| Live monitoring | `docker stats book-service member-service borrow-service notification-service` |
| Locust web UI | `python -m locust -f loadtest\locustfile.py --host http://127.0.0.1:8003` → `http://localhost:8089` |
| One level, headless (example W3) | `python -m locust -f loadtest\locustfile.py --headless -u 4 -r 4 -t 60s --host http://127.0.0.1:8003` |
| Full measurement (overwrites `results/`) | `python loadtest\run_workloads.py` |
| Regenerate graphs | `python scripts\generate_graphs.py` |
| Stop one container / start again | `docker stop notification-service` / `docker start notification-service` |
| Stop everything (keep data) | `docker compose down` |
| Stop and delete data | `docker compose down -v` |

**If something goes wrong:**

| Problem | Fix |
|:--|:--|
| `dockerDesktopLinuxEngine` error | Docker Desktop not running — start it, wait for *Engine running* |
| `port is already allocated` | Local Uvicorn/Streamlit still running — Ctrl + C in those terminals |
| `address already in use` when starting Uvicorn | Containers are running — `docker compose down` |
| A container is `(unhealthy)` | `docker compose logs <name>` |
| Borrow shows `(health: starting)` | Wait 10–20 s; it waits for the other three |
| Swagger borrow says 409 | That book is already borrowed — choose another `book_id` |
