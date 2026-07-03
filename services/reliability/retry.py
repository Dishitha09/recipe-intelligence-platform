import functools
import time


try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    transient_retry = retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, exp_base=4, min=1, max=16),
    )
except ImportError:
    def transient_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay_seconds = 1
            last_error = None

            for attempt in range(3):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc

                    if attempt == 2:
                        break

                    time.sleep(delay_seconds)
                    delay_seconds = min(delay_seconds * 4, 16)

            raise last_error

        return wrapper
