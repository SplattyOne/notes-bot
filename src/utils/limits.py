import functools


def limit_concurrency(method):
    """Decorator for limiting the number of simultaneous calls to an asynchronous method."""
    @functools.wraps(method)
    async def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_semaphore') or not self._semaphore:
            raise ValueError('Need to have self._semaphore = asyncio.Semaphore class initiated')
        async with self._semaphore:
            return await method(self, *args, **kwargs)
    return wrapper
