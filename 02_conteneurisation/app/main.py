from __future__ import annotations

import os
import socket
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

APP_ENV = os.getenv('APP_ENV', 'development')
DATABASE_URL = os.getenv('DATABASE_URL', '')

app = FastAPI(title='CareHub appointments', version='1.0.0')
REQUESTS = Counter('carehub_http_requests_total', 'HTTP requests', ['endpoint', 'status'])
APPOINTMENT_LATENCY = Histogram('carehub_appointment_seconds', 'Appointment operation latency')


class AppointmentIn(BaseModel):
    patient_reference: str = Field(min_length=3, max_length=64)
    requested_at: datetime
    specialty: str = Field(min_length=2, max_length=80)


def _connect():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL is not configured')
    import psycopg
    return psycopg.connect(DATABASE_URL, connect_timeout=3)


def init_db() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id BIGSERIAL PRIMARY KEY,
                    patient_reference VARCHAR(64) NOT NULL,
                    requested_at TIMESTAMPTZ NOT NULL,
                    specialty VARCHAR(80) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()


@app.on_event('startup')
def startup() -> None:
    # The database can be temporarily unavailable during startup; Compose health
    # dependencies reduce the risk. A failed initialization is surfaced by /ready.
    try:
        init_db()
    except Exception:
        pass


@app.get('/health')
def health() -> dict[str, str]:
    REQUESTS.labels('/health', '200').inc()
    return {'status': 'ok', 'environment': APP_ENV}


@app.get('/ready')
def ready() -> dict[str, str]:
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                cur.fetchone()
        REQUESTS.labels('/ready', '200').inc()
        return {'status': 'ready'}
    except Exception as exc:
        REQUESTS.labels('/ready', '503').inc()
        raise HTTPException(status_code=503, detail='database unavailable') from exc


@app.get('/instance')
def instance() -> dict[str, str]:
    """Expose the container instance for scaling/load-balancing evidence."""
    return {'instance': socket.gethostname(), 'environment': APP_ENV}


@app.get('/metrics')
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post('/api/appointments', status_code=201)
def create_appointment(payload: AppointmentIn) -> dict[str, Any]:
    with APPOINTMENT_LATENCY.time():
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO appointments (patient_reference, requested_at, specialty)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (payload.patient_reference, payload.requested_at, payload.specialty),
                    )
                    appointment_id = cur.fetchone()[0]
                conn.commit()
            REQUESTS.labels('/api/appointments', '201').inc()
            return {
                'id': appointment_id,
                'status': 'created',
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            REQUESTS.labels('/api/appointments', '503').inc()
            raise HTTPException(status_code=503, detail='database unavailable') from exc
