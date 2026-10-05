# Docker Explained From Zero — For This Project

> **How to read this.** This document assumes you know nothing about Docker. It starts with the
> **problem** Docker solves, then builds up one concept at a time, with each concept depending on
> the one before it. Every concept is then connected to a real file or command in this project.
> Read `implementation.md` for the application itself (FastAPI, microservices, results).
> If a section is unclear, give that section to another LLM and ask follow-up questions.

---

## Contents

1. [The problem: why Docker exists](#1-the-problem-why-docker-exists)
2. [First answer: virtual machines, and why they were not enough](#2-first-answer-virtual-machines-and-why-they-were-not-enough)
3. [Containerization: what a container really is](#3-containerization-what-a-container-really-is)
4. [Virtual machine vs container](#4-virtual-machine-vs-container)
5. [Docker: the tool](#5-docker-the-tool)
6. [Images](#6-images)
7. [The Dockerfile — how an image is built](#7-the-dockerfile--how-an-image-is-built)
8. [Layers and the build cache](#8-layers-and-the-build-cache)
9. [Containers — running an image](#9-containers--running-an-image)
10. [Ports and port mapping](#10-ports-and-port-mapping)
11. [Networking between containers](#11-networking-between-containers)
12. [Volumes — keeping data](#12-volumes--keeping-data)
13. [Environment variables — configuring a container](#13-environment-variables--configuring-a-container)
14. [Healthchecks](#14-healthchecks)
15. [Docker Compose — running many containers together](#15-docker-compose--running-many-containers-together)
16. [Our docker-compose.yml, line by line](#16-our-docker-composeyml-line-by-line)
17. [Monitoring: docker stats, logs, exec, inspect](#17-monitoring-docker-stats-logs-exec-inspect)
18. [Docker on Windows: Docker Desktop and WSL2](#18-docker-on-windows-docker-desktop-and-wsl2)
19. [What happens when you type `docker compose up -d`](#19-what-happens-when-you-type-docker-compose-up--d)
20. [How Docker fits into cloud computing](#20-how-docker-fits-into-cloud-computing)
21. [Command cheat sheet](#21-command-cheat-sheet)
22. [Viva questions on Docker](#22-viva-questions-on-docker)
23. [Glossary](#23-glossary)

---

## 1. The problem: why Docker exists

A program never runs on its own. Our Book Service, for example, needs:

- an **operating system** (Linux, Windows …);
- a **Python interpreter** of a suitable version;
- **libraries**: `fastapi`, `uvicorn`, `pydantic`, … each at a version that works with the others;
- **system libraries** that Python itself depends on;
- **configuration**: which port to use, where the database file is.

All of this together is called the program's **environment** or **dependencies**. Problems start when the program moves from one machine to another:

**1. "It works on my machine."** You wrote and tested the code on your laptop with Python 3.13 and FastAPI 0.141. The evaluator's machine has Python 3.9 and an older FastAPI. Your code uses a feature the old version doesn't have, and it crashes. The code is the same; the environment is different.

**2. Dependency conflicts.** Project A needs `library X` version 1. Project B on the same machine needs `library X` version 2. Only one version can be installed system-wide, so one project breaks. Python's virtual environments solve this partly, but only for Python packages, not for the Python version itself or for system libraries.

**3. Setup is slow and error-prone.** Setting up a new server means a long list of manual steps (install this, configure that). People forget steps, servers drift apart over time, and nobody knows exactly what is installed where.

**4. Many services make it worse.** A microservice application has many programs. Each may need different versions of things, and they must all be started in the right way, with the right settings, and connected to each other. Doing that by hand on every machine is not practical.

**What we want** is a way to:
- package a program **together with its entire environment** into one unit;
- run that unit **the same way on any machine** (laptop, lab PC, cloud server);
- keep units **isolated** from each other so they cannot conflict;
- do this **cheaply and quickly**, so that running 10 or 100 of them is normal.

That is exactly what **containerization** provides, and **Docker** is the most widely used tool for it.

---

## 2. First answer: virtual machines, and why they were not enough

Before containers, the standard answer was the **virtual machine (VM)**. You studied this in the hypervisor experiment (Proxmox vs VMware).

A **hypervisor** creates virtual hardware: virtual CPUs, virtual RAM and a virtual disk. On that virtual hardware you install a **complete guest operating system**, with **its own kernel**, and then your application.

```text
┌───────────┐ ┌───────────┐ ┌───────────┐
│  App A    │ │  App B    │ │  App C    │
│ Libraries │ │ Libraries │ │ Libraries │
│ Guest OS  │ │ Guest OS  │ │ Guest OS  │   ← a full OS + kernel in EVERY VM
│ (kernel)  │ │ (kernel)  │ │ (kernel)  │
└───────────┘ └───────────┘ └───────────┘
        Hypervisor (VMware, KVM, Hyper-V)
        Physical hardware
```

VMs do solve isolation and portability: you can copy a VM image to another machine. But they are **heavy**:

| Problem | Why |
|:--|:--|
| **Size** | Each VM contains a full OS, usually **several GB** |
| **Start-up time** | The guest OS must boot: **tens of seconds to minutes** |
| **Memory** | Each guest kernel and its background services use RAM even when idle; a VM might reserve 1–2 GB |
| **Density** | A laptop can run a few VMs, not dozens |
| **Duplication** | Ten VMs mean ten copies of the same OS, all patched and maintained separately |

For **one** big application, that is acceptable. For a **microservice** application with many small services, giving each service its own full OS is wasteful. Our Book Service is a few dozen lines of Python, and putting it in a 2 GB VM makes little sense.

The key observation: **the applications don't actually need their own kernel. They only need their own files, libraries and isolation.** Containers are built on that observation.

---

## 3. Containerization: what a container really is

### 3.1 The kernel, briefly
An operating system has two parts:
- the **kernel**: the core that controls the CPU, memory, disks and network, and runs processes;
- **user space**: everything else, such as programs, libraries, the shell and configuration files.

When you run a program, it becomes a **process**, which the kernel schedules on the CPU.

### 3.2 A container is an isolated process
A **container** is **one or more normal processes running on the host's kernel**. The kernel uses special features to make those processes believe they are alone on their own machine.

The two Linux kernel features that make this possible:

**1. Namespaces control what a process can see.** Each namespace gives the container its own private view of one part of the system:

| Namespace | What the container gets | Effect in our project |
|:--|:--|:--|
| **PID** | Its own process list; its main process is PID 1 | Inside book-service, Uvicorn is process 1 and cannot see the other containers' processes |
| **Network (net)** | Its own network interfaces, IP address, ports and routing | Every service can listen on its own port, each container has its own IP (172.18.0.x), and `localhost` inside a container means *only that container* |
| **Mount (mnt)** | Its own filesystem tree | Each container sees its own `/app`, `/data` and its own Python installation |
| **UTS** | Its own hostname | Each container has its own hostname |
| **IPC** | Its own inter-process communication space | Containers cannot use shared memory to interfere with each other |
| **User** | Its own user ID mapping | A user that is root inside a container can be mapped to a non-root user on the host (optional) |

**2. Control groups (cgroups) control how much a process can use.** cgroups limit and **measure** CPU, memory, disk I/O and process count per container. This is where `docker stats` gets its numbers. It is also how you could say "this container may use at most 1 CPU and 512 MB" (we did not set limits in this project).

Combine the two and you get a process that:
- has its **own filesystem** (with its own Python 3.12 and libraries),
- has its **own network identity**,
- **cannot see** other containers,
- has **measurable, limitable** resource use,
- but **shares the host's kernel**. There is no second OS to boot.

That is a container. **Containerization** is the practice of packaging applications to run this way.

### 3.3 Consequences of sharing the kernel
- **Start-up in under a second to a few seconds.** Starting a container is basically starting a process; nothing boots. In our project the four services became healthy within about 8 seconds of `docker compose up`, and most of that was the healthcheck interval.
- **Small size.** The image holds only user-space files, not a kernel. Our service images use about 212 MB on disk and about 51 MB of packaged content.
- **Little overhead.** Code in a container runs directly on the real CPU through the normal kernel, so performance is close to running it directly on the host.
- **Weaker isolation than a VM.** All containers share one kernel, so a serious kernel bug could, in theory, let a process escape its container. VMs, with separate kernels, isolate more strongly.
- **Linux containers need a Linux kernel.** Containers built from Linux images (like ours) need a Linux kernel underneath. On Windows, Docker Desktop provides one with a small hidden Linux VM (see Section 18).

---

## 4. Virtual machine vs container

```text
        VIRTUAL MACHINES                          CONTAINERS
┌──────┐ ┌──────┐ ┌──────┐            ┌──────┐ ┌──────┐ ┌──────┐
│ App  │ │ App  │ │ App  │            │ App  │ │ App  │ │ App  │
│ Libs │ │ Libs │ │ Libs │            │ Libs │ │ Libs │ │ Libs │
│Guest │ │Guest │ │Guest │            └──────┘ └──────┘ └──────┘
│ OS + │ │ OS + │ │ OS + │              Container engine (Docker)
│kernel│ │kernel│ │kernel│              Host OS — ONE shared kernel
└──────┘ └──────┘ └──────┘              Physical hardware
   Hypervisor
   Physical hardware
```

| | Virtual machine | Container |
|:--|:--|:--|
| What is virtualised | Hardware | The operating system's view (files, network, processes) |
| Kernel | Each VM has its own | All containers share the host's |
| Size | GBs | MBs to a few hundred MB |
| Start time | Tens of seconds to minutes | Under a second to a few seconds |
| Isolation | Very strong | Strong, but weaker than a VM |
| Can run a different OS | Yes (Windows VM on a Linux host) | Only the host's kernel type (Linux containers need Linux) |
| Typical density | A few per laptop | Dozens to hundreds per laptop |
| Typical use | Full servers, different OSes, strong isolation | Packaging and running applications, microservices |

They are **not competitors** in practice. In the cloud, containers almost always run **inside VMs**: the cloud provider gives you a VM, and you run many containers in it. On your laptop, Docker Desktop does the same thing, running containers inside a small Linux VM.

---

## 5. Docker: the tool

Containers existed in Linux before Docker (as LXC). **Docker** (released in 2013) made them **easy** by providing:

1. **A standard package format,** the **image**, which can be built from a simple text file and shared.
2. **A simple command-line tool** (`docker build`, `docker run`, …).
3. **A registry,** **Docker Hub**, where images are stored and downloaded, like an app store for images.
4. **Docker Compose,** for describing and running multi-container applications.

### 5.1 How Docker is organised

```text
   You type:  docker ps
        │
        ▼
 ┌─────────────────┐   REST API    ┌──────────────────────────────┐
 │ Docker CLI      │ ────────────▶ │ Docker daemon (dockerd)      │
 │ (docker.exe)    │               │ builds images, runs          │
 └─────────────────┘               │ containers, manages networks │
                                   │ and volumes                  │
                                   └──────────────┬───────────────┘
                                                  │ uses
                                   containerd + runc → Linux kernel
                                   (namespaces + cgroups)
                                                  │ pulls images from
                                                  ▼
                                   Registry (Docker Hub: python:3.12-slim)
```

- The **Docker CLI** (`docker` command) is only a client. It sends your command to the daemon.
- The **Docker daemon** (`dockerd`) is a background service that does the real work.
- **containerd** and **runc** are lower-level components that ask the kernel to create the namespaces and cgroups.
- A **registry** stores images. **Docker Hub** is the default public one.

This is why every `docker` command failed until **Docker Desktop was started**: the CLI had no daemon to talk to.

### 5.2 The three core objects

| Object | What it is | Relationship |
|:--|:--|:--|
| **Image** | A read-only package: filesystem + settings | The template |
| **Container** | A running (or stopped) instance of an image | Created from an image; you can create many containers from one image |
| **Dockerfile** | A text file with instructions for building an image | Input to `docker build` |

```text
Dockerfile  ──docker build──▶  Image  ──docker run──▶  Container (running process)
 (recipe)                    (package)                 (instance)
```

In programming terms, an image is like a **class** and a container is like an **object** created from it. One image can have many running containers, each with its own state.

---

## 6. Images

### 6.1 What is inside an image
An image contains:
1. **A filesystem:** all the files the program needs. For our services that means a minimal Debian Linux user space, Python 3.12, the pip-installed libraries (`fastapi`, `uvicorn` …) and our `main.py`.
2. **Metadata:** settings such as which command to run at start (`CMD`), the working directory, environment variables and documented ports.

It does **not** contain a kernel.

### 6.2 Names and tags
An image name has the form `repository:tag`:

| Image | Repository | Tag |
|:--|:--|:--|
| `python:3.12-slim` | `python` (official image on Docker Hub) | `3.12-slim` = Python 3.12 on a slimmed-down Debian |
| `library-app/book-service:1.0` | `library-app/book-service` (our own) | `1.0` |

A **tag** is a label for a version. If you leave it out, Docker assumes `:latest`. Official images on Docker Hub live under a hidden namespace called `library/`. That's why, when we first named our images `library/book-service`, Docker displayed them as just `book-service`, and we renamed them to `library-app/...`.

### 6.3 Base images
Nobody builds an image from nothing. You start **from** an existing image, the **base image**, and add your own files on top. Our services start from `python:3.12-slim`, which already contains Debian and Python 3.12. The `slim` variant leaves out compilers and documentation to stay small. The very first `docker compose build` downloaded (**pulled**) this base image from Docker Hub, which is why it took several minutes. After that it was cached locally.

### 6.4 Our images (from `docker images library-app/*`, screenshot 24)

| Image | Disk usage | Content size |
|:--|--:|--:|
| `library-app/book-service:1.0` | 212 MB | 51.5 MB |
| `library-app/member-service:1.0` | 212 MB | 51.5 MB |
| `library-app/borrow-service:1.0` | 214 MB | 52.0 MB |
| `library-app/notification-service:1.0` | 212 MB | 51.5 MB |
| `library-app/frontend:1.0` | 778 MB | 179 MB |

Docker reports both the space the image takes when unpacked on disk and the size of its packaged content. The four service images are almost identical because they share the same base image and nearly the same libraries. Borrow is slightly bigger because of `httpx`. The frontend is much larger because Streamlit pulls in pandas, numpy and pyarrow.

Images that share layers (see Section 8) **store those layers only once** on disk, so the four service images together take far less than 4 × 212 MB.

---

## 7. The Dockerfile — how an image is built

A **Dockerfile** is a text file with step-by-step instructions for building an image. Here is ours for the Borrow Service (`services/borrow_service/Dockerfile`). The other three are the same apart from the port:

```dockerfile
# Borrow Service image
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

Line by line:

| Instruction | What it does | Why we need it |
|:--|:--|:--|
| `FROM python:3.12-slim` | Starts from the official Python 3.12 slim image | We get Linux and Python already installed and tested |
| `WORKDIR /app` | Creates `/app` inside the image and makes it the current folder for the following instructions and at run time | A tidy place for our code; `COPY ... .` copies into `/app` |
| `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1` | Sets environment variables inside the image | The first stops Python writing `.pyc` cache files. The second makes `print`/log output appear immediately in `docker logs` instead of being held in a buffer |
| `COPY requirements.txt .` | Copies the file from your computer into `/app` in the image | pip needs to know which libraries to install |
| `RUN pip install --no-cache-dir -r requirements.txt` | **Runs a command during the build** and saves the result into the image | Installs FastAPI, Uvicorn (and httpx). `--no-cache-dir` keeps pip's download cache out of the image, so the image is smaller |
| `COPY main.py .` | Copies our application code | The service itself |
| `EXPOSE 8003` | **Documents** that the program listens on port 8003 | Information only. It does **not** open the port to your laptop; port mapping does that (Section 10) |
| `CMD [...]` | The **default command** to run when a container starts from this image | Starts Uvicorn serving `main:app` on port 8003, on all interfaces (`0.0.0.0`) |

### 7.1 `RUN` vs `CMD`, a common confusion
- **`RUN`** runs at **build time**, **once**, and its result (installed files) becomes part of the image.
- **`CMD`** runs at **container start**, **every time** a container is created from the image.

### 7.2 Why `--host 0.0.0.0` matters inside a container
Inside the container's own network namespace, `127.0.0.1` means *that container only*. If Uvicorn listened on `127.0.0.1`, only processes inside the same container could connect. Port-forwarded traffic from your laptop and requests from other containers arrive on the container's network interface (e.g. `172.18.0.2`), not on its loopback address, so they would be refused. `0.0.0.0` means "accept connections on every interface", which makes the service reachable from outside the container.

### 7.3 The build context and `.dockerignore`
When you run `docker build ./services/book_service`, everything in that folder (the **build context**) is sent to the Docker daemon, and `COPY` can only copy files from it. Our `.dockerignore` lists files to **leave out**:

```text
__pycache__/
data/
*.db
```

So the local SQLite databases from Checkpoint 1 never end up inside the image. Each container starts with a clean database instead.

### 7.4 `requirements.txt`
A plain list of Python packages:

```text
fastapi>=0.110
uvicorn>=0.29
httpx>=0.27      # Borrow Service only
```

`>=` means "this version or newer". Pinning exact versions (`==`) would make builds even more repeatable.

---

## 8. Layers and the build cache

### 8.1 Images are made of layers
Each instruction in a Dockerfile that changes the filesystem (`FROM`, `COPY`, `RUN`) creates a new **layer**. A layer is a set of file changes stacked on top of the previous one. Instructions like `ENV`, `WORKDIR`, `EXPOSE` and `CMD` only change the metadata.

```text
┌──────────────────────────────────────┐
│ COPY main.py            (a few KB)   │  ← changes often
├──────────────────────────────────────┤
│ RUN pip install ...     (~15–20 MB)  │
├──────────────────────────────────────┤
│ COPY requirements.txt   (tiny)       │
├──────────────────────────────────────┤
│ python:3.12-slim layers (~150+ MB)   │  ← shared by ALL our service images
└──────────────────────────────────────┘
```

Layers are **read-only** and identified by a hash of their content. Two images that use the same base image **share** those base layers on disk.

### 8.2 The build cache
When you rebuild, Docker checks each instruction in order: "have I already built this exact step, with the same inputs?" If yes, it **reuses the cached layer** instantly. As soon as one step changes, **that step and every step after it** are rebuilt.

That is why our Dockerfile copies `requirements.txt` and runs `pip install` **before** copying `main.py`:
- When you edit `main.py` (common), only the last `COPY` layer is rebuilt. The slow `pip install` layer comes from the cache.
- If we had copied `main.py` first, every code change would re-run `pip install`.

You saw this: the first build took several minutes (downloading the base image and packages), and the next `docker compose build` finished in about **31 seconds** (screenshot 23).

### 8.3 The container's writable layer
When a container starts, Docker adds a thin **writable layer** on top of the image's read-only layers. Any file the running program creates or changes goes there. **When the container is deleted, that writable layer is deleted too.** That is why data that must survive goes into a **volume** (Section 12). It is also why "containers are disposable" is a core idea: you should be able to delete a container and start a fresh one from the same image at any time.

---

## 9. Containers — running an image

### 9.1 Lifecycle

```text
 docker create / run        docker start         docker stop          docker rm
 ───────────────▶ Created ──────────────▶ Running ──────────▶ Exited ─────────▶ (deleted)
                                ▲                      │
                                └──── docker restart ──┘
```

- `docker run` = create + start in one step.
- A container **runs as long as its main process (PID 1) runs.** For us, PID 1 is Uvicorn. If Uvicorn crashed, the container would move to *Exited*.
- `docker stop` sends a polite shutdown signal (SIGTERM), waits, and then forces it.

### 9.2 Running one container by hand (for understanding)
Docker Compose does this for us, but the basic command is:

```bash
docker run -d --name book-service -p 8001:8001 -e DB_PATH=/data/books.db \
           -v book-data:/data library-app/book-service:1.0
```

| Flag | Meaning |
|:--|:--|
| `-d` | Detached: run in the background |
| `--name book-service` | Give the container a fixed name |
| `-p 8001:8001` | Port mapping, laptop:container (Section 10) |
| `-e DB_PATH=...` | Environment variable (Section 13) |
| `-v book-data:/data` | Attach a volume (Section 12) |
| last argument | The image to run |

Writing this for five containers, plus a network, plus start order, is tedious and error-prone. **Docker Compose** replaces all of it with one file (Section 15).

### 9.3 Containers are isolated from each other
Each of our five containers has:
- its own filesystem (its own copy of `/app`, Python and libraries);
- its own processes (in each container, Uvicorn or Streamlit is PID 1);
- its own network interface and IP on `library-net`;
- its own CPU and memory accounting.

They share only the kernel, plus whatever we deliberately connect: the **network**, and **volumes** if we chose to share them (we didn't).

---

## 10. Ports and port mapping

### 10.1 The problem
Each container has its **own network namespace**. When Uvicorn inside book-service listens on port 8001, that is port 8001 **of the container**, not of your laptop. Your browser on Windows cannot reach it directly.

### 10.2 Publishing a port
**Port mapping** (also called **publishing**) tells Docker to forward a port on the host to a port in the container:

```yaml
ports:
  - "8001:8001"     # "HOST_PORT:CONTAINER_PORT"
```

Now a request to `http://localhost:8001` on your laptop is forwarded to port 8001 inside the book-service container. The two numbers don't have to match: `"9000:8001"` would make the service available at `localhost:9000`.

`docker ps` shows this as `0.0.0.0:8001->8001/tcp` (screenshot 26).

### 10.3 Who needs port mapping?
- **You** (browser, Swagger UI, Locust on Windows) need it, because you are **outside** the Docker network.
- **Containers talking to each other do not need it.** They talk over the internal network directly (Section 11).

We published all ports so you can open each service's `/docs` page and so Locust can reach Borrow. In a production setup, you would often publish **only** the entry point (Borrow and the frontend) and keep Book, Member and Notification private, reachable only by other containers. That is more secure.

### 10.4 "Port is already allocated"
Only one program can listen on a given host port. While your four local Uvicorn terminals were running on ports 8001–8004, Docker could not publish those ports. That's why you stopped them before `docker compose up`.

---

## 11. Networking between containers

### 11.1 Docker networks
Docker can create **virtual networks** inside the host. The common type is a **bridge network**: a virtual switch that containers plug into. Each container on it gets a private IP address, and containers on the same network can reach each other. Containers on different networks cannot.

Our `docker-compose.yml` creates one network:

```yaml
networks:
  library-net:
    name: library-net
    driver: bridge
```

and attaches every service to it (`networks: [library-net]`). `docker network inspect library-net` (screenshots 27–28) showed:

| Setting | Value |
|:--|:--|
| Driver | bridge |
| Subnet | 172.18.0.0/16 |
| Gateway | 172.18.0.1 |
| book-service | 172.18.0.2 |
| member-service | 172.18.0.3 |
| notification-service | 172.18.0.4 |
| borrow-service | 172.18.0.5 |
| library-frontend | 172.18.0.6 |

### 11.2 Service discovery with built-in DNS
IP addresses are **not stable**. If a container is recreated, it may get a different IP. Hard-coding `172.18.0.2` would break.

On a **user-defined network** (like `library-net`, and like the default network that Compose creates), Docker runs an **embedded DNS server**. Every container can look up other containers **by their service name** (and container name), and Docker answers with the current IP.

So the Borrow Service uses:
```text
http://book-service:8001
http://member-service:8002
http://notification-service:8004
```

When the Borrow code calls `http://book-service:8001/books/3`:
1. It asks DNS: "what is the IP of `book-service`?"
2. Docker's DNS answers `172.18.0.2`.
3. The request goes over the bridge to the book-service container's port 8001.

This is **service discovery**: finding other services by name instead of by address. You proved it with:

```bash
docker exec borrow-service python -c "import urllib.request;print(urllib.request.urlopen('http://book-service:8001/health').read())"
# b'{"service":"book-service","status":"healthy"}'      (screenshot 29)
```

Note: the original default network called `bridge` (used when you `docker run` without a network) does **not** provide this name-based DNS. That is one reason to always use a user-defined network, which Compose does automatically.

### 11.3 The meaning of `localhost` inside a container
This is the most common beginner mistake. **Inside a container, `localhost` (127.0.0.1) means that container itself.** If the Borrow container called `http://localhost:8001`, it would look for port 8001 **inside the borrow container**, find nothing, and fail. To reach another container, use **its service name**.

That's why our code reads service addresses from environment variables:
- locally (no Docker), they default to `http://127.0.0.1:8001`, because all four programs run on your laptop;
- in Docker, Compose sets them to `http://book-service:8001`.

### 11.4 The full path of a request, network-wise

```text
Windows (Locust / browser)
   │  http://localhost:8003   ← published port
   ▼
[port mapping 8003 → borrow-service:8003]
   │
   ▼
borrow-service (172.18.0.5)  ── http://member-service:8002 ──▶ member-service (172.18.0.3)
                             ── http://book-service:8001   ──▶ book-service   (172.18.0.2)
                             ── http://notification-service:8004 ─▶ notification-service (172.18.0.4)
          (all inside library-net, resolved by Docker DNS, no published ports needed)
```

---

## 12. Volumes — keeping data

### 12.1 The problem
Section 8.3 said that a container's writable layer is **deleted with the container**. Our services store data in SQLite files. If those files lived in the container's writable layer, every `docker compose down` or rebuild would **wipe all books, members and borrows**.

### 12.2 Volumes
A **volume** is storage managed by Docker that lives **outside** any container's layers. You **mount** it at a path inside the container. Whatever the program writes to that path actually goes into the volume, which survives when containers are deleted and recreated.

In `docker-compose.yml`:

```yaml
services:
  book-service:
    environment:
      DB_PATH: /data/books.db       # the app writes its database to /data
    volumes:
      - book-data:/data             # /data inside the container IS the volume "book-data"

volumes:
  book-data:                        # declare the named volume
  member-data:
  borrow-data:
  notification-data:
```

Each service has its **own** volume, which matches the "database per service" rule. When you ran `docker compose up -d`, Docker created them (screenshot 25). Their full names carry the project name as a prefix: `cc_lab_evaluation_book-data`, and so on.

### 12.3 Volume behaviour you should know
| Command | Effect on data |
|:--|:--|
| `docker compose down` | Removes containers and the network. **Volumes are kept**, so the data survives |
| `docker compose up -d` again | New containers reattach to the same volumes, so the old data is back |
| `docker compose down -v` | Also **deletes the volumes**, so all data is lost and the next start re-seeds 10 books and 5 members |
| Rebuilding an image | Does not touch volumes |

### 12.4 Bind mounts (for comparison)
Another way to persist data is a **bind mount**, which maps a folder on your own computer into the container, e.g. `./data:/data`. It's handy during development (you can see the files directly), but it depends on the host's folder layout. **Named volumes** are managed fully by Docker and are the usual choice for database data.

---

## 13. Environment variables — configuring a container

The same image should run in different situations (laptop, test server, cloud) without being rebuilt. So **settings are passed in from outside** as **environment variables**, not written into the code.

Our services read:

| Variable | Used by | Value in Docker | Default when run locally |
|:--|:--|:--|:--|
| `DB_PATH` | all 4 services | `/data/books.db` etc. (inside the volume) | `data/books.db` |
| `BOOK_SERVICE_URL` | Borrow, frontend | `http://book-service:8001` | `http://127.0.0.1:8001` |
| `MEMBER_SERVICE_URL` | Borrow, frontend | `http://member-service:8002` | `http://127.0.0.1:8002` |
| `NOTIFICATION_SERVICE_URL` | Borrow, frontend | `http://notification-service:8004` | `http://127.0.0.1:8004` |
| `BORROW_SERVICE_URL` | frontend | `http://borrow-service:8003` | `http://127.0.0.1:8003` |

In Python: `os.getenv("BOOK_SERVICE_URL", "http://127.0.0.1:8001")`.
In Compose: the `environment:` section of each service.

This is why **one codebase** works both in Checkpoint 1 (four terminals) and in Docker. It also follows a widely used cloud principle: *store configuration in the environment, not in the code*.

---

## 14. Healthchecks

### 14.1 "Running" is not the same as "ready"
`docker ps` showing a container as *Up* only means its main process exists. The program might still be starting, or might be stuck. A **healthcheck** is a command Docker runs **inside the container, repeatedly**, to find out whether the application is actually working.

Ours (for book-service):

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
  interval: 5s       # run the check every 5 seconds
  timeout: 3s        # if it takes longer than 3 s, count it as failed
  retries: 10        # after 10 failures in a row, mark the container "unhealthy"
```

- The check runs **inside** the container, so here `localhost` is correct: it means this container.
- If `/health` answers, Python exits with code 0, which means **healthy**. If the connection fails, Python raises an error and exits non-zero, which counts as a failure.
- `docker ps` then shows `Up 35 seconds (healthy)` (screenshot 26).

The frontend has no healthcheck, which is why it shows only `Up`.

### 14.2 Using health to control start order
Borrow depends on the other three. If Borrow started first and immediately received a request, its calls to Book would fail. Compose's `depends_on` with a condition fixes this:

```yaml
borrow-service:
  depends_on:
    book-service:         {condition: service_healthy}
    member-service:       {condition: service_healthy}
    notification-service: {condition: service_healthy}
```

Compose waits until those three are **healthy** before starting Borrow. The frontend similarly waits for Borrow. You can see this in the `docker ps` timings: Borrow was "Up" a few seconds later than the others.

### 14.3 The cost we measured
Each check starts a **new Python interpreter** in the container, which costs a burst of CPU. With 4 containers checked every 5 seconds, this showed up in our measurements: the Notification Service received **no** load-test traffic, yet averaged about **11–14 % CPU** with spikes near 70 %. A longer interval (e.g. 30 s) or a lighter command (`curl`/`wget`, if installed in the image) would reduce this. It's a good example of monitoring revealing something you didn't expect.

---

## 15. Docker Compose — running many containers together

### 15.1 Why Compose
Our application needs five containers, one network and four volumes, each with the right ports, environment variables, healthchecks and start order. Doing that with individual `docker run` commands would mean a long list of commands that must be typed correctly every time.

**Docker Compose** lets you describe the **whole application in one YAML file**, `docker-compose.yml`, and manage it with single commands:

```bash
docker compose build      # build all images
docker compose up -d      # create network + volumes, start all containers in the right order
docker compose ps         # status of this application's containers
docker compose logs -f    # follow logs of all services
docker compose down       # stop and remove containers + network (keeps volumes)
```

This is called a **declarative** approach: you describe **what** you want (these services, this network, these volumes), and Compose works out **how** to create it. If you run `up` again after changing the file, it changes only what is needed.

### 15.2 Compose vocabulary
| Term | Meaning |
|:--|:--|
| **Project** | The whole application. By default, named after the folder (`cc_lab_evaluation`) |
| **Service** | One entry under `services:`, describing how to run a container (e.g. `book-service`) |
| **Container** | The actual running instance created for a service |
| **Network / volume** | Declared at the bottom and attached to services |

The **service name** (`book-service`) is the name other containers use in DNS. We also set `container_name: book-service` so the container has the same simple name in `docker ps` and `docker stats`.

### 15.3 YAML in 30 seconds
YAML is a text format that uses **indentation** (spaces, never tabs) for structure:
- `key: value` is a setting.
- An indented block belongs to the key above it.
- `- item` is a list item.

Wrong indentation is the most common Compose error.

---

## 16. Our docker-compose.yml, line by line

```yaml
x-healthcheck: &healthcheck        # (1) a reusable block, defined once
  interval: 5s
  timeout: 3s
  retries: 10

services:                          # (2) the containers that make up the app
  book-service:                    # (3) service name = DNS name on the network
    build: ./services/book_service #     build the image from this folder's Dockerfile
    image: library-app/book-service:1.0   # name/tag for the built image
    container_name: book-service   #     fixed container name
    ports:
      - "8001:8001"                #     publish: laptop 8001 → container 8001
    environment:
      DB_PATH: /data/books.db      #     configuration via environment variable
    volumes:
      - book-data:/data            #     persistent storage for the SQLite file
    networks:
      - library-net                #     join the shared network
    healthcheck:
      <<: *healthcheck             # (4) paste in the reusable block from (1)
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]

  member-service:      # ... same pattern, port 8002, members.db, member-data
  notification-service:# ... same pattern, port 8004, notifications.db, notification-data

  borrow-service:
    build: ./services/borrow_service
    image: library-app/borrow-service:1.0
    container_name: borrow-service
    ports:
      - "8003:8003"
    environment:
      DB_PATH: /data/borrows.db
      BOOK_SERVICE_URL: http://book-service:8001                 # (5) other services BY NAME
      MEMBER_SERVICE_URL: http://member-service:8002
      NOTIFICATION_SERVICE_URL: http://notification-service:8004
    volumes:
      - borrow-data:/data
    networks:
      - library-net
    depends_on:                                                  # (6) start order
      book-service:         {condition: service_healthy}
      member-service:       {condition: service_healthy}
      notification-service: {condition: service_healthy}
    healthcheck: ...

  frontend:                         # (7) the Streamlit client
    build: ./frontend
    image: library-app/frontend:1.0
    container_name: library-frontend
    ports:
      - "8501:8501"
    environment:                    #     the client also uses service names
      BOOK_SERVICE_URL: http://book-service:8001
      MEMBER_SERVICE_URL: http://member-service:8002
      BORROW_SERVICE_URL: http://borrow-service:8003
      NOTIFICATION_SERVICE_URL: http://notification-service:8004
    networks:
      - library-net
    depends_on:
      borrow-service: {condition: service_healthy}

networks:                           # (8) the network
  library-net:
    name: library-net
    driver: bridge

volumes:                            # (9) named volumes, one per service
  book-data:
  member-data:
  borrow-data:
  notification-data:
```

Notes:
1. **`x-healthcheck: &healthcheck`**: keys starting with `x-` are ignored by Compose, so they can hold reusable snippets. `&healthcheck` gives the block a name (a YAML **anchor**).
2. **`services:`**: five entries, so five containers.
3. **The service name** is how other containers find this one (Docker DNS).
4. **`<<: *healthcheck`** merges the anchored block in here, which saves repeating `interval/timeout/retries` four times.
5. **The core of microservice communication in Docker**: addresses are **service names**, passed in as environment variables.
6. **`depends_on` + `service_healthy`**: Borrow starts only after its dependencies pass their healthchecks.
7. **The frontend is in the same network,** because its Python code runs inside a container and must call the services by name. Your browser only receives the finished web page through port 8501.
8. **One user-defined bridge network,** which provides the name-based DNS.
9. **Four named volumes,** so each service's database survives container restarts.

> **About scaling:** `docker compose up --scale borrow-service=3` would start three Borrow containers. With our file as written, this would fail for two reasons: `container_name` must be unique, and only one container can publish host port 8003. To scale a service you remove `container_name`, stop publishing its port, and put a load balancer (e.g. Nginx) in front. This is a natural "next step" to mention if asked.

---

## 17. Monitoring: docker stats, logs, exec, inspect

| Command | What it shows | How we used it |
|:--|:--|:--|
| `docker ps` | Running containers, image, status (healthy), ports | Proof of deployment (screenshot 26) |
| `docker images library-app/*` | Our images and their sizes | Proof of build (screenshot 24) |
| `docker stats` | Live CPU %, memory, network and disk I/O, PIDS per container | Monitoring during the load test (screenshots 37, 38, 43) |
| `docker stats --no-stream` | One snapshot, then exit | Used by `run_workloads.py` in a loop to record numbers into CSV |
| `docker compose logs <service>` | The program's output (Uvicorn request logs, errors) | Debugging |
| `docker exec <container> <command>` | Runs a command **inside** a running container | Proved name-based communication (screenshot 29) |
| `docker network inspect library-net` | Network settings and the containers attached, with IPs | Proof of shared network (screenshots 27–28) |
| `docker inspect <container>` | Every detail of a container (env vars, mounts, IP, health log) | Deeper debugging |

**Reading `docker stats`:**

```text
NAME             CPU %     MEM USAGE / LIMIT     MEM %   NET I/O          BLOCK I/O        PIDS
borrow-service   126.66%   43.98MiB / 7.664GiB   0.56%   45.2MB / 45MB    9.79MB / 135kB   17
```

- **CPU %:** 100 % = one full CPU core, so 126.66 % ≈ 1.27 cores. These numbers come from **cgroups** (Section 3.2).
- **MEM USAGE / LIMIT:** memory used, and the most the container may use. We set no limit, so the limit is the memory of Docker Desktop's Linux VM (7.664 GiB).
- **NET I/O:** total bytes received / sent since start.
- **BLOCK I/O:** disk reads / writes.
- **PIDS:** processes plus threads. Borrow went from 2 at idle to 17 under load, because its thread pool grew.

---

## 18. Docker on Windows: Docker Desktop and WSL2

Our images are **Linux** images (based on Debian), and Linux containers need a **Linux kernel** (Section 3.3). Windows doesn't have one, so **Docker Desktop**:

1. runs a small, lightweight **Linux virtual machine** using **WSL2** (Windows Subsystem for Linux 2, which uses Hyper-V technology underneath);
2. runs the **Docker daemon inside that Linux VM**;
3. installs the `docker` CLI on Windows, which sends commands to that daemon;
4. forwards published ports, so `localhost:8001` on Windows reaches the container.

```text
Windows 11
 ├── docker.exe (CLI), browser, Locust, VS Code
 └── WSL2 Linux VM  (started by Docker Desktop)
       └── Docker daemon
             ├── book-service container
             ├── member-service container
             ├── borrow-service container
             ├── notification-service container
             └── library-frontend container
```

Consequences you saw:
- **Docker Desktop must be running** before any `docker` command works (Session 4: "Docker Desktop was stopped").
- The memory limit in `docker stats`, **7.664 GiB**, is the memory given to that Linux VM, not your laptop's full 16 GB.
- `wsl -l -v` lists a distribution called `docker-desktop`, which is that VM.
- There is a small virtualisation overhead compared with running Docker on native Linux, as noted in the README's limitations.

This connects nicely to your hypervisor experiment: **containers on Windows run inside a VM**, just as containers in the cloud usually run inside VMs.

---

## 19. What happens when you type `docker compose up -d`

Putting every concept together:

1. **Read the file.** Compose reads `docker-compose.yml` and names the project `cc_lab_evaluation` (after the folder).
2. **Images.** For each service, check whether the image (e.g. `library-app/book-service:1.0`) exists. If not, **build** it from the Dockerfile in its `build:` folder (layers, cache). With `--build` it always rebuilds.
3. **Network.** Create the bridge network `library-net` (subnet 172.18.0.0/16) with its embedded DNS.
4. **Volumes.** Create `cc_lab_evaluation_book-data` and the others, if they don't exist yet.
5. **Containers, in dependency order:**
   - Create and start **book-service**, **member-service** and **notification-service**. Each gets:
     - its own namespaces (filesystem from the image plus a writable layer, its own PID 1, its own network interface with an IP on `library-net`);
     - cgroups for resource accounting;
     - its volume mounted at `/data`;
     - its environment variables;
     - its published port.
   - Inside each, `CMD` starts **Uvicorn**. The `lifespan` function creates and seeds the SQLite database in `/data`.
   - Docker starts running the **healthchecks** every 5 s.
   - Once all three are **healthy**, start **borrow-service**, with service-name URLs in its environment.
   - Once Borrow is healthy, start **library-frontend** (Streamlit).
6. **Detach.** `-d` returns you to the prompt while the containers keep running in the background.

Then `docker ps` shows four services `Up (healthy)` and the frontend `Up`. The application is reachable at `localhost:8501` (UI) and `localhost:8001–8004` (APIs).

And `docker compose down` reverses it: it stops and removes the containers and the network, and **keeps the volumes**, so the data survives.

---

## 20. How Docker fits into cloud computing

- **Portability.** The same image runs on your laptop, a lab server, AWS, Azure or Google Cloud. "Build once, run anywhere."
- **Microservices.** Containers make it cheap to run each service separately, which is the practical foundation of microservice architectures.
- **Scaling.** Starting another copy of a container takes seconds, so you can add copies of a busy service (horizontal scaling) and remove them when load drops. Our results showed exactly which service should be scaled: **Borrow**.
- **Orchestration.** On many machines, tools such as **Kubernetes** (and cloud services like Amazon ECS/EKS, Azure AKS and Google GKE) do what Docker Compose does on one machine: decide where containers run, restart failed ones, scale them and connect them. Compose is the single-machine version of the same idea, and the concepts in this document (images, containers, networks, service discovery, volumes, health checks, environment configuration) carry over directly.
- **CI/CD.** Automated pipelines build an image for every code change, test it, push it to a registry, and deploy that exact image. What was tested is exactly what runs.

---

## 21. Command cheat sheet

| Goal | Command |
|:--|:--|
| Check that Docker works | `docker info`, `docker run --rm hello-world` |
| Build all images | `docker compose build` |
| Start everything (background) | `docker compose up -d` |
| Rebuild and restart one service | `docker compose up -d --build frontend` |
| See running containers | `docker ps` (or `docker compose ps`) |
| See images | `docker images library-app/*` |
| Live resource use | `docker stats book-service member-service borrow-service notification-service` |
| Logs of a service | `docker compose logs borrow-service` (add `-f` to follow) |
| Run a command inside a container | `docker exec -it borrow-service sh` (opens a shell; type `exit` to leave) |
| Inspect the network | `docker network inspect library-net` |
| List volumes | `docker volume ls` |
| Stop everything (keep data) | `docker compose down` |
| Stop everything and delete data | `docker compose down -v` |
| Remove unused images and cache | `docker system prune` (careful: deletes unused objects) |

---

## 22. Viva questions on Docker

**Q1. Why do we need Docker?**
To package an application with its complete environment (OS libraries, Python version, packages, config) so it runs the same on any machine. This removes "works on my machine" problems, avoids dependency conflicts, and makes it practical to run many isolated services such as our four microservices.

**Q2. What is containerization? How is a container different from a VM?**
Containerization means running an application as an isolated process that has its own filesystem, network and process view (Linux **namespaces**) and controlled resources (**cgroups**), while **sharing the host's kernel**. A VM virtualises hardware and runs its own full OS and kernel. That makes containers much smaller and faster to start, but their isolation is weaker.

**Q3. What is the difference between an image and a container?**
An image is a read-only package (filesystem layers + start-up settings) built from a Dockerfile. A container is a running instance of that image, with its own writable layer. One image can run as many containers.

**Q4. Explain your Dockerfile.**
`FROM python:3.12-slim` is the base with Python. `WORKDIR /app` sets the code folder. `COPY requirements.txt` + `RUN pip install` installs the libraries, done first so the step is cached. `COPY main.py` adds the code. `EXPOSE` documents the port. `CMD` starts Uvicorn on `0.0.0.0` and the service's port.

**Q5. Why copy `requirements.txt` before `main.py`?**
Because of **layer caching**. Docker rebuilds a step and everything after it only if its input changed. Code changes often and requirements rarely, so this order lets rebuilds reuse the slow `pip install` layer.

**Q6. What is the difference between `RUN` and `CMD`?**
`RUN` executes at build time and saves the result in the image. `CMD` is the command executed each time a container starts.

**Q7. What does `EXPOSE` do? What does `ports: "8001:8001"` do?**
`EXPOSE` only documents the port. `ports` publishes it: traffic to port 8001 on the host is forwarded to port 8001 in the container.

**Q8. How do your containers find each other?**
They are all on the user-defined bridge network `library-net`. Docker's embedded DNS resolves service names (e.g. `book-service`) to the container's current IP, so Borrow calls `http://book-service:8001`.

**Q9. Why can't Borrow use `localhost:8001` to reach Book in Docker?**
Each container has its own network namespace, so `localhost` inside the Borrow container refers to the Borrow container itself, where nothing listens on 8001.

**Q10. What is a volume and why do you use it?**
A volume is Docker-managed storage that exists outside a container's lifecycle. Our SQLite files are stored in volumes (`/data`), so data survives when containers are removed or rebuilt. `docker compose down -v` deletes them.

**Q11. What is Docker Compose?**
A tool for defining a multi-container application in one YAML file (services, images, ports, environment, volumes, networks, start order, health checks) and managing it with commands like `docker compose up -d` and `down`.

**Q12. What do `depends_on` and the healthcheck do?**
The healthcheck repeatedly calls `/health` inside each container to decide whether it is healthy. `depends_on` with `condition: service_healthy` makes Borrow start only after Book, Member and Notification are healthy.

**Q13. What does `docker stats` measure, and where do the numbers come from?**
Per-container CPU % (100 % = one core), memory, network I/O, disk I/O and process count. The kernel's cgroups track these for each container.

**Q14. How does Docker run Linux containers on your Windows laptop?**
Docker Desktop starts a lightweight Linux VM with WSL2. The Docker daemon and all containers run inside it, and published ports are forwarded to Windows.

**Q15. How would you scale the bottleneck service?**
Run several Borrow containers (remove the fixed `container_name` and published port, add a load balancer in front), or run several Uvicorn workers inside it. In the cloud, an orchestrator such as Kubernetes would do this automatically.

---

## 23. Glossary

| Term | Meaning |
|:--|:--|
| **Containerization** | Running applications as isolated processes with their own environment, sharing the host kernel |
| **Container** | A running instance of an image: isolated process(es) + writable layer |
| **Image** | Read-only, layered package of a filesystem + start-up settings |
| **Dockerfile** | Text instructions for building an image |
| **Layer** | One set of filesystem changes in an image; cached and shared |
| **Build cache** | Reuse of unchanged layers to make rebuilds fast |
| **Build context** | The folder sent to Docker when building; `COPY` can only use files from it |
| **.dockerignore** | Files left out of the build context |
| **Base image** | The image you start `FROM` (e.g. `python:3.12-slim`) |
| **Tag** | Version label of an image (`:1.0`, `:latest`) |
| **Registry / Docker Hub** | Server that stores and distributes images |
| **Pull / push** | Download an image from / upload it to a registry |
| **Docker daemon (dockerd)** | Background service that builds and runs containers |
| **Docker CLI** | The `docker` command; a client for the daemon |
| **Kernel** | Core of the OS that manages hardware and processes |
| **Namespace** | Kernel feature giving a process a private view (PID, network, mount …) |
| **cgroup** | Kernel feature that limits and measures resource use |
| **Writable layer** | A container's private changes; deleted with the container |
| **Port mapping / publishing** | Forwarding a host port to a container port (`"8001:8001"`) |
| **Bridge network** | Virtual network connecting containers on one host |
| **Embedded DNS / service discovery** | Resolving a service name to a container IP |
| **Volume** | Persistent Docker-managed storage mounted into containers |
| **Bind mount** | A host folder mounted into a container |
| **Environment variable** | Configuration passed to a container from outside |
| **Healthcheck** | Repeated command that decides if a container is healthy |
| **depends_on** | Compose setting for start order (optionally waiting for health) |
| **Docker Compose** | Tool to define and run multi-container apps from YAML |
| **Project (Compose)** | The whole application defined by one compose file |
| **Docker Desktop** | Windows/macOS app that runs Docker inside a Linux VM |
| **WSL2** | Windows Subsystem for Linux 2; the lightweight Linux VM used by Docker Desktop |
| **Orchestration (Kubernetes)** | Managing containers across many machines: placement, scaling, healing |
| **Horizontal scaling** | Running more copies of a service to handle more load |
