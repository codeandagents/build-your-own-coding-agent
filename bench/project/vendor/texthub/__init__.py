"""TextHub SMS gateway, Python client 2.3.1 (vendored: see vendor/texthub/README.md before changing anything here)."""
from .client import Client, Message, Result
from .errors import RateLimited, TextHubError
from .segments import encoding_of, segments

__version__ = "2.3.1"
__all__ = ["Client", "Message", "RateLimited", "Result", "TextHubError", "encoding_of", "segments"]
