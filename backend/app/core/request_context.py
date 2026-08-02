import contextvars

# Context variables bound to task/thread execution flow
request_id_var = contextvars.ContextVar("request_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")


def get_request_id() -> str:
    """Retrieves current request ID from context flow."""
    return request_id_var.get()


def get_user_id() -> str:
    """Retrieves current user identifier (email or ID) from context flow."""
    return user_id_var.get()
