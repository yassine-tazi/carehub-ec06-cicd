from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


class FakeCursor:
    def __init__(self, fetch_value=(1,)):
        self.fetch_value = fetch_value
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.fetch_value


class FakeConnection:
    def __init__(self, fetch_value=(1,)):
        self.cursor_obj = FakeCursor(fetch_value)
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'




def test_instance_endpoint():
    response = client.get('/instance')
    assert response.status_code == 200
    assert response.json()['instance']
    assert 'environment' in response.json()


def test_metrics_exposed():
    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'carehub_http_requests_total' in response.text


def test_invalid_appointment_rejected_before_database():
    response = client.post(
        '/api/appointments',
        json={'patient_reference': 'x', 'requested_at': '2026-09-17T10:00:00Z', 'specialty': 'A'},
    )
    assert response.status_code == 422


def test_ready_success(monkeypatch):
    monkeypatch.setattr(main, '_connect', lambda: FakeConnection())
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.json() == {'status': 'ready'}


def test_ready_failure(monkeypatch):
    def boom():
        raise RuntimeError('db down')
    monkeypatch.setattr(main, '_connect', boom)
    response = client.get('/ready')
    assert response.status_code == 503


def test_create_appointment_success(monkeypatch):
    monkeypatch.setattr(main, '_connect', lambda: FakeConnection((42,)))
    response = client.post(
        '/api/appointments',
        json={
            'patient_reference': 'PAT-001',
            'requested_at': '2026-09-17T10:00:00Z',
            'specialty': 'Cardiologie',
        },
    )
    assert response.status_code == 201
    assert response.json()['id'] == 42


def test_create_appointment_failure(monkeypatch):
    def boom():
        raise RuntimeError('db down')
    monkeypatch.setattr(main, '_connect', boom)
    response = client.post(
        '/api/appointments',
        json={
            'patient_reference': 'PAT-002',
            'requested_at': '2026-09-17T10:00:00Z',
            'specialty': 'Neurologie',
        },
    )
    assert response.status_code == 503
