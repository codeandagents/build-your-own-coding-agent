class TextHubError(Exception):
    """The gateway refused a request. `code` is TextHub's error code (see the API reference)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class RateLimited(TextHubError):
    """HTTP 429. `retry_after` is in seconds."""

    def __init__(self, retry_after: float):
        super().__init__("rate_limited", f"retry after {retry_after} s")
        self.retry_after = retry_after
