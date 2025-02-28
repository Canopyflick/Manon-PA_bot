# utils/db_helpers.py
from datetime import datetime
from typing import List, Any, Optional, Tuple, Dict, Union


def build_query_with_datetime_params(
        base_query: str,
        params: List[Any],
        datetime_filters: List[Tuple[str, str, datetime]],
        order_by: Optional[str] = None
) -> Tuple[str, List[Any]]:
    """
    Build a PostgreSQL query with proper handling of datetime parameters.

    Args:
        base_query: The base SQL query string
        params: Initial list of parameters
        datetime_filters: List of (column_name, operator, datetime_value) tuples
                         e.g., [('deadline', '>=', start_time), ('deadline', '<=', end_time)]
        order_by: Optional ORDER BY clause

    Returns:
        Tuple of (complete query string, parameters list)
    """
    query = base_query
    current_params = list(params)  # Create a copy to avoid modifying the original

    for column, operator, dt_value in datetime_filters:
        if dt_value is not None:
            # Add the condition with proper parameter index and type casting
            param_index = len(current_params) + 1
            query += f" AND {column} {operator} ${param_index}::timestamptz"
            current_params.append(dt_value.isoformat())

    if order_by:
        query += f" ORDER BY {order_by}"

    return query, current_params