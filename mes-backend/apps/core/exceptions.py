from rest_framework.views import exception_handler

from apps.core.responses import envelope_error


def mes_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return envelope_error("server_error", "Internal server error", status=500)
    code = getattr(exc, "default_code", "error")
    message = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
    return envelope_error(str(code), str(message), status=response.status_code)
