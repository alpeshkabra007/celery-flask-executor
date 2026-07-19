"""Celery task definitions.

All tasks are registered against the module-level ``celery`` instance created in
:mod:`flask_app`. Importing this module (which happens at the bottom of
``flask_app/__init__.py``) is what makes the tasks discoverable by both the
Flask routes and the Celery worker.
"""

import random
import time

from flask_app import celery


@celery.task()
def add_together(a, b):
    """Return the sum of two numbers.

    Kept intentionally trivial as the canonical "hello world" async task.
    """
    return a + b


@celery.task(bind=True)
def process_batch(self, n):
    """Simulate a long-running job that reports incremental progress.

    Iterates ``n`` times, sleeping briefly on each step and pushing a
    ``PROGRESS`` state so clients polling ``/result/<task_id>`` can render a
    progress bar.
    """
    n = int(n)
    for i in range(n):
        time.sleep(0.05)
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': n,
                'status': 'Processing item {0} of {1}'.format(i + 1, n),
            },
        )
    return {
        'current': n,
        'total': n,
        'status': 'Batch complete',
        'result': n,
    }


@celery.task()
def compute_fibonacci(n):
    """Compute the n-th Fibonacci number.

    A small stand-in for a CPU-bound workload that should run off the request
    thread. Implemented iteratively so large ``n`` stays memory-friendly.
    """
    n = int(n)
    if n < 0:
        raise ValueError('n must be non-negative')
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


@celery.task(bind=True, max_retries=3, default_retry_delay=1)
def unreliable_task(self, value, failure_rate=0.5):
    """A task that fails intermittently and retries itself.

    Demonstrates Celery's retry mechanism: it raises a transient error with
    probability ``failure_rate`` and asks Celery to retry, up to
    ``max_retries`` times before giving up.
    """
    if random.random() < failure_rate:
        try:
            raise RuntimeError('Transient failure, will retry')
        except RuntimeError as exc:
            raise self.retry(exc=exc)
    return {'value': value, 'status': 'ok', 'retries': self.request.retries}
