from rest_framework.response import Response


def envelope_ok(data=None, meta=None, status=200):
    return Response({"success": True, "data": data, "error": None, "meta": meta}, status=status)


def envelope_error(code: str, message: str, status=400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}, "meta": None},
        status=status,
    )
