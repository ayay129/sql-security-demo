"""SQLite engine-level permissions; never rely on SQL keyword matching."""
import sqlite3
import time
from pathlib import Path


class QueryRejected(ValueError):
    pass


POLICY = {'products': frozenset({'id', 'name', 'price'})}
FUNCTIONS = frozenset({'count', 'sum', 'avg', 'min', 'max', 'lower', 'upper', 'length', 'coalesce'})


def authorize(action, table, column, database, source):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        if (database == 'main' or (database is None and column == '')) and table in POLICY and (column == '' or column in POLICY[table]):
            return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and column.lower() in FUNCTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def query(path: Path, sql: str, max_rows=100, timeout_seconds=0.1):
    if not sql.strip() or len(sql) > 4096:
        raise QueryRejected('SQL must contain 1–4096 characters')
    deadline = time.monotonic() + timeout_seconds
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.enable_load_extension(False)
        connection.set_authorizer(authorize)
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 100)
        # Preparation uses exactly the same permissions as execution.
        plan = connection.execute('EXPLAIN QUERY PLAN ' + sql).fetchall()
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise QueryRejected('Only result-producing queries are allowed')
        rows = cursor.fetchmany(max_rows + 1)
        return {'columns': [item[0] for item in cursor.description],
                'rows': [list(row) for row in rows[:max_rows]],
                'truncated': len(rows) > max_rows,
                'plan': [list(row) for row in plan]}
    except sqlite3.Error as exc:
        raise QueryRejected('Query rejected by read-only access policy or execution budget') from exc
    finally:
        connection.close()
