from flask import Flask, request
from celery import Celery
from celery.result import AsyncResult
import os


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    # Only push Celery-relevant settings using the modern (lowercase) keys.
    # Dumping the whole Flask config would mix the legacy ``CELERY_*`` keys with
    # the new-style ``broker_url`` / ``result_backend`` and raise
    # ImproperlyConfigured on recent Celery versions.
    if app.config.get('CELERY_TASK_ALWAYS_EAGER'):
        # Run tasks synchronously in-process (used by the test suite so no
        # Redis broker/backend is required).
        celery.conf.task_always_eager = True
        celery.conf.task_eager_propagates = True

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def _bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
        CELERY_TASK_ALWAYS_EAGER=_bool_env("CELERY_TASK_ALWAYS_EAGER", False),
    )
    if config:
        app.config.update(config)

    @app.route('/')
    def home():
        return 'Hello World'

    @app.route('/add/<int:a>/<int:b>')
    def add(a, b):
        task = add_together.apply_async(args=[a, b])
        return {'task_id': task.id}, 202

    @app.route('/tasks/fibonacci/<int:n>', methods=['POST'])
    def fibonacci(n):
        task = compute_fibonacci.apply_async(args=[n])
        return {'task_id': task.id}, 202

    @app.route('/tasks/batch', methods=['POST'])
    def batch():
        payload = request.get_json(silent=True) or {}
        n = int(payload.get('n', request.args.get('n', 10)))
        task = process_batch.apply_async(args=[n])
        return {'task_id': task.id}, 202

    @app.route('/tasks/unreliable', methods=['POST'])
    def unreliable():
        payload = request.get_json(silent=True) or {}
        value = payload.get('value', 'ping')
        task = unreliable_task.apply_async(args=[value])
        return {'task_id': task.id}, 202

    @app.route('/result/<task_id>')
    def result(task_id):
        task_result = AsyncResult(task_id)
        response = {'state': task_result.state}

        if task_result.state == 'PENDING':
            response.update({
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            })
        elif task_result.state != 'FAILURE':
            result_info = task_result.info
            if isinstance(result_info, dict):
                response.update({
                    'current': result_info.get('current', 0),
                    'total': result_info.get('total', 1),
                    'status': result_info.get('status', ''),
                    'result': task_result.result
                })
            else:
                response.update({
                    'current': 1,
                    'total': 1,
                    'status': '',
                    'result': task_result.result
                })
        else:
            response.update({
                'current': 1,
                'total': 1,
                'status': str(task_result.info),
            })
        return response

    return app


# The module-level app + Celery instance the worker (celery_worker.py) binds to.
app = create_app()
celery = make_celery(app)


# Import tasks last so they register against the module-level ``celery`` above
# and become available as module globals used by the routes and the worker.
from flask_app.tasks import (  # noqa: E402,F401
    add_together,
    compute_fibonacci,
    process_batch,
    unreliable_task,
)
