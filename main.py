import logging
import time
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from db_security import QueryRejected, query

logger = logging.getLogger('sql_demo')


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=4096)


def create_app(database=None):
    app = FastAPI(title='SQL Security Demo')
    database = database or Path(__file__).with_name('demo.db')

    @app.post('/query')
    def execute(request: QueryRequest):
        request_id = uuid4().hex
        started = time.monotonic()
        status = 'ok'
        try:
            return {'request_id': request_id, **query(database, request.sql)}
        except QueryRejected as exc:
            status = 'rejected'
            raise HTTPException(400, detail=str(exc)) from exc
        finally:
            # Log metadata, never raw SQL or result values.
            logger.info('request_id=%s status=%s duration_ms=%.2f', request_id, status,
                        (time.monotonic() - started) * 1000)

    return app


app = create_app()
