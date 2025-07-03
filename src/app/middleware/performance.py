import time
from contextvars import ContextVar
from types import TracebackType
from typing import Dict, List, Optional, Type

from src.app.utils.logging_config import get_performance_logger

# Context variable to store query timing information
query_stats: ContextVar[Dict[str, List[float]]] = ContextVar("query_stats", default={})


class QueryPerformanceTracker:
    """
    A context manager to track query execution time.
    """

    def __init__(self, query_name: str) -> None:
        self.query_name = query_name
        self.start_time: Optional[float] = None  # ✅ Type hint for mypy

    def __enter__(self) -> "QueryPerformanceTracker":
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        if self.start_time is not None:
            execution_time = time.time() - self.start_time
            stats = query_stats.get()

            if self.query_name not in stats:
                stats[self.query_name] = []

            stats[self.query_name].append(execution_time)
            query_stats.set(stats)

            # Log slow queries (> 100ms)
            if execution_time > 0.1:
                perf_logger = get_performance_logger()
                perf_logger.warning(
                    f"Slow query detected: {self.query_name} took {execution_time:.4f}s"
                )

        return None  # ✅ Required return to avoid mypy error


def get_query_stats() -> Dict[str, Dict[str, float]]:
    """
    Get statistics about query performance.
    Returns a dictionary with query names as keys and statistics as values.
    """
    stats = query_stats.get()
    result = {}

    for query_name, times in stats.items():
        if not times:
            continue

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        count = len(times)

        result[query_name] = {
            "avg_time": avg_time,
            "max_time": max_time,
            "min_time": min_time,
            "count": count,
            "total_time": sum(times),
        }

    return result


def reset_query_stats() -> None:
    """
    Reset the query statistics.
    """
    query_stats.set({})
