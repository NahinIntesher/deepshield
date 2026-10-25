"""Index local videos only. No demo users, scores, labels or AI predictions."""
import hashlib
from ..config import VIDEOS_DIR,DATA_ROOT
from ..models.db_models import ResearchChallengeItem

EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

def video_index():
    from ..services import media_store
    result = {}
    for root,prefix in ((VIDEOS_DIR,''),(DATA_ROOT/'library','library/')):
        for label in ('real','fake'):
            folder = root / label
            folder.mkdir(parents=True, exist_ok=True)
            for path in sorted(folder.rglob('*')):
                if path.is_file() and path.suffix.lower() in EXTENSIONS and path.resolve().is_relative_to(root.resolve()):
                    token = hashlib.sha256((prefix+path.relative_to(root).as_posix()).encode()).hexdigest()[:24]
                    result[token] = (path, label.title())
    for path,label in media_store.library_paths():
        prefix='library/' if path.is_relative_to((DATA_ROOT/'library').resolve()) else ''
        root=(DATA_ROOT/'library').resolve() if prefix else VIDEOS_DIR.resolve()
        token=hashlib.sha256((prefix+path.relative_to(root).as_posix()).encode()).hexdigest()[:24]
        result[token]=(path,label)
    return result

def seed_database(db):
    existing = {i.media_path: i for i in db.query(ResearchChallengeItem).all()}
    for token, (path, label) in video_index().items():
        url = f'/api/media/{token}'
        if url not in existing:
            db.add(ResearchChallengeItem(title=f'Video {token[:6].upper()}', media_type='video', media_path=url,
                ground_truth=label, manipulation_type='Not annotated', difficulty='Not rated',
                description='Watch the video and make your own judgment.', visual_cues='[]'))
    db.commit()

def available_items(db):
    seed_database(db)
    urls = {f'/api/media/{t}' for t in video_index()}
    return [i for i in db.query(ResearchChallengeItem).filter_by(archived=False).all() if i.media_path in urls]

def item_path(item):
    token = item.media_path.rsplit('/',1)[-1]
    entry = video_index().get(token)
    if entry is None:
        raise FileNotFoundError('Video no longer exists. Refresh the video list.')
    from ..services.media_store import local_path
    return local_path(entry[0])
