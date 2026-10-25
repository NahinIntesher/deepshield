"""Set isolation before any app module can load the developer's real .env."""
import os
from pathlib import Path
import tempfile

_session=tempfile.TemporaryDirectory(prefix='deepshield-tests-')
os.environ.update({
    'DATABASE_URL':'sqlite:///'+str(Path(_session.name)/'suite.db'),
    'DATA_ROOT':str(Path(_session.name)/'data'),
    'MEDIA_STORAGE_ENABLED':'false',
    'MODEL_SPACE_ID':'',
    'MODEL_SPACE_TOKEN':'',
    'COOKIE_SECURE':'false',
    'COOKIE_SAMESITE':'lax',
})
