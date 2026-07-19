"""Test suite for the Flask + Celery task executor.

Celery runs in EAGER mode here, so tasks execute synchronously in-process and
NO Redis broker/result backend is required to run these tests.
"""

import os

# Force eager mode and in-memory broker/backend BEFORE flask_app is imported so
# the module-level Celery instance (and every task bound to it) runs
# synchronously with NO Redis required. ``self.update_state`` in eager mode
# still writes to the result backend, hence the in-memory cache backend.
os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ['CELERY_RESULT_BACKEND'] = 'cache+memory://'

import pytest

from flask_app import create_app, celery
from flask_app.tasks import add_together, compute_fibonacci, process_batch

# Belt-and-braces: guarantee eager mode regardless of import ordering.
celery.conf.task_always_eager = True
celery.conf.task_eager_propagates = True


@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.test_client() as test_client:
        yield test_client


def test_home_returns_hello_world(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hello World' in response.data


def test_add_together_task_runs_directly():
    # Calling the task function directly should behave like a plain function.
    assert add_together(2, 3) == 5


def test_add_route_returns_202_with_task_id(client):
    response = client.get('/add/2/3')
    assert response.status_code == 202
    body = response.get_json()
    assert 'task_id' in body
    assert body['task_id']


def test_add_route_result_available_in_eager_mode(client):
    # In eager mode apply_async runs synchronously; the result is immediate.
    result = add_together.apply_async(args=[2, 3])
    assert result.get() == 5


def test_compute_fibonacci_task():
    assert compute_fibonacci(0) == 0
    assert compute_fibonacci(1) == 1
    assert compute_fibonacci(10) == 55
    # Via the eager task machinery.
    assert compute_fibonacci.apply_async(args=[10]).get() == 55


def test_fibonacci_route_returns_202(client):
    response = client.post('/tasks/fibonacci/10')
    assert response.status_code == 202
    body = response.get_json()
    assert 'task_id' in body and body['task_id']


def test_process_batch_task():
    result = process_batch.apply_async(args=[3]).get()
    assert result['total'] == 3
    assert result['current'] == 3
    assert result['result'] == 3


def test_batch_route_returns_202(client):
    response = client.post('/tasks/batch', json={'n': 3})
    assert response.status_code == 202
    body = response.get_json()
    assert 'task_id' in body and body['task_id']
