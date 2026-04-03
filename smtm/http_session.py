import time
import requests


def request_with_retry(request_func, *args, retries=2, backoff=0.5,
                       retry_on_status=(500, 502, 503, 504), **kwargs):
    """재시도 로직을 포함한 HTTP 요청 래퍼

    Wrapper that adds retry logic to HTTP requests for transient failures.
    Compatible with requests.get, requests.post, requests.delete etc.

    Args:
        request_func: 호출할 requests 함수 (requests.get, requests.post 등)
        retries: 재시도 횟수 (default: 2)
        backoff: 재시도 간 대기 시간 배수 (default: 0.5초, 1.0초)
        retry_on_status: 재시도할 HTTP 상태 코드
    """
    for attempt in range(retries + 1):
        try:
            response = request_func(*args, **kwargs)
            status = getattr(response, "status_code", None)
            if status in retry_on_status and attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue
            return response
        except requests.exceptions.ConnectionError:
            if attempt >= retries:
                raise
            time.sleep(backoff * (2 ** attempt))
