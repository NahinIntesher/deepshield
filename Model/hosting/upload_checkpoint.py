"""Upload the original checkpoint to its private Hugging Face model repository.

Run using hosting/.venv with HF_HOME set to hosting/.hf-cache. The token stays local.
"""
import hashlib
import json
import re
import traceback
from pathlib import Path

from huggingface_hub import HfApi, CommitOperationAdd

ROOT = Path(__file__).resolve().parent
REPO = 'nahin-intesher/deepshield-checkpoint'


def main():
    manifest = json.loads((ROOT/'checkpoint-manifest.json').read_text(encoding='utf-8'))
    weights = ROOT.parent/manifest['file']
    checksum = hashlib.sha256()
    with weights.open('rb') as stream:
        for part in iter(lambda: stream.read(8*1024*1024), b''):
            checksum.update(part)
    if weights.stat().st_size != manifest['bytes'] or checksum.hexdigest() != manifest['sha256']:
        raise ValueError('Local checkpoint does not match the verified original.')
    api = HfApi()
    before = api.model_info(REPO)
    if not before.private:
        raise ValueError('Repository must be private before uploading.')
    print('Uploading original checkpoint to private repository...', flush=True)
    commit = api.create_commit(
        repo_id=REPO,
        repo_type='model',
        commit_message='Store original DeepShield checkpoint and checksum',
        operations=[
            CommitOperationAdd(path_in_repo='best_model.pth', path_or_fileobj=str(weights)),
            CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=str(ROOT/'README.md')),
            CommitOperationAdd(path_in_repo='checkpoint-manifest.json', path_or_fileobj=str(ROOT/'checkpoint-manifest.json')),
        ],
    )
    info = api.model_info(REPO, revision=commit.oid, files_metadata=True)
    remote = next(row for row in info.siblings if row.rfilename == 'best_model.pth')
    if not info.private or remote.size != manifest['bytes'] or not remote.lfs or remote.lfs.sha256 != manifest['sha256']:
        raise ValueError('Remote size, hash or privacy verification failed.')
    result = {
        'repository': REPO, 'url': 'https://huggingface.co/'+REPO,
        'private': info.private, 'revision': commit.oid,
        'file': remote.rfilename, 'bytes': remote.size,
        'local_sha256': checksum.hexdigest(), 'remote_sha256': remote.lfs.sha256,
        'verified': True, 'hosting': 'file storage only; no inference API',
    }
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified private checkpoint: size and server SHA-256 match the original.', flush=True)
    print(result['url'], flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid logging credentials, signed storage URLs, request headers or tokens.
        print('Upload/verification did not complete:',type(exc).__name__,flush=True)
        reason = re.sub(r'https?://\S+', '[storage URL]', str(exc))
        reason = re.sub(r'hf_[A-Za-z0-9]+', '[token]', reason)
        reason = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [redacted]', reason)
        print('Diagnostic:', reason[:500], flush=True)
        print('Failed operation:', ' > '.join(frame.name for frame in traceback.extract_tb(exc.__traceback__)[-6:]), flush=True)
        raise SystemExit(1) from None
