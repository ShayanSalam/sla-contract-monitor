"""
Shared rate limiter instance.

Kept in its own module (rather than defined in main.py) so that both main.py
and any router that needs per-endpoint limits can import it without a
circular import - main.py imports the routers, so the routers can't import
the limiter back from main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
