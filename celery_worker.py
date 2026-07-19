from flask_app import celery

# Import the tasks module so every task registers with the worker.
import flask_app.tasks  # noqa: F401


if __name__ == '__main__':
    celery.start()
