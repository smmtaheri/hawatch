from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    payload = {
        "error": {
            "code": response.status_code,
            "message": _message(response.data),
            "retryable": response.status_code >= 500,
        }
    }
    response.data = payload
    return response


def _message(data) -> str:
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        return "درخواست نامعتبر است."
    if isinstance(data, list) and data:
        return str(data[0])
    return "خطای ناشناخته."
