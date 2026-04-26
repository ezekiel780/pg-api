from rest_framework.response import Response


def custom_response(success: bool, message: str, status_code: int = 200, data=None):
    """
    Standard API response wrapper for consistent backend responses.
    """

    response_payload = {
        "success": success,
        "message": message,
    }

    if data is not None:
        response_payload["data"] = data

    return Response(response_payload, status=status_code)
