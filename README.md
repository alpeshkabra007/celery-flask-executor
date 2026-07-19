# Celery + Flask Task Executor

A minimal reference implementation of **asynchronous background task
processing** with [Celery](https://docs.celeryq.dev/), a [Flask](https://flask.palletsprojects.com/)
API, and [Redis](https://redis.io/) as the broker and result backend — all wired
together with Docker Compose.

Submit work over HTTP, run it off the request thread on a Celery worker, and
poll for the result. A tiny `add` task stands in for any real workload.

## Architecture

```
        HTTP                         enqueue
Client  ───▶  Flask API  ──────────────────────────▶  Redis (broker)
              (web)                                       │
              ▲                                           ▼
              │           poll result           Celery Worker (worker)
              └──────────────  Redis (result backend)  ◀──┘
```

| Service | Role |
| --- | --- |
| `web` | Flask app exposing the HTTP API (port `5000`) |
| `worker` | Celery worker that executes queued tasks |
| `redis` | Message broker + result backend (port `6379`) |

## Quick start

```bash
docker-compose build
docker-compose up
```

The API is then available at `http://localhost:5000`.

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Health check — returns `Hello World`. |
| `GET` | `/add/<a>/<b>` | Enqueue an addition task. Returns `{ "task_id": "..." }` (HTTP 202). |
| `GET` | `/result/<task_id>` | Poll a task's state and result. |

### Example

```bash
# Enqueue 2 + 3
curl http://localhost:5000/add/2/3
# -> {"task_id": "a1b2c3..."}

# Poll for the result
curl http://localhost:5000/result/a1b2c3...
# -> {"state": "SUCCESS", "result": 5, ...}
```

## Configuration

Both services read the broker/backend URLs from the environment (defaults shown):

| Variable | Default |
| --- | --- |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` |

## Project layout

```
.
├── flask_app/
│   ├── __init__.py     # app factory, Celery setup, routes, the add task
│   └── app.py          # entrypoint
├── celery_worker.py    # Celery worker entrypoint
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## License

MIT
