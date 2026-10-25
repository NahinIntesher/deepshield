"""Upload curated inference files using a token scoped to this private Space."""
import json
from pathlib import Path
from huggingface_hub import HfApi,CommitOperationAdd

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
REPO='nahin-intesher/deepshield-inference'

def main():
    api=HfApi()
    if not api.space_info(REPO).private:
        raise ValueError('Inference Space must remain private.')
    files={name:ROOT/name for name in ['app.py','runtime.zip','requirements.txt','packages.txt','README.md','source-hashes.json']}
    files['best_model.pth']=PROJECT/'Model/best_model.pth'
    files['det_10g.onnx']=Path.home()/'.insightface/models/buffalo_l/det_10g.onnx'
    if not all(path.is_file() for path in files.values()):
        raise ValueError('Missing source, checkpoint or original face detector.')
    commit=api.create_commit(repo_id=REPO,repo_type='space',commit_message='Deploy original DeepShield inference on free ZeroGPU',
        operations=[CommitOperationAdd(path_in_repo=name,path_or_fileobj=str(path)) for name,path in files.items()])
    info=api.space_info(REPO,revision=commit.oid,files_metadata=True)
    weight=next(row for row in info.siblings if row.rfilename=='best_model.pth')
    manifest=json.loads((PROJECT/'Model/hosting/checkpoint-manifest.json').read_text(encoding='utf-8'))
    if not info.private or not weight.lfs or weight.lfs.sha256!=manifest['sha256'] or weight.size!=manifest['bytes']:
        raise ValueError('Hosted checkpoint verification failed.')
    result={'space':REPO,'private':info.private,'revision':commit.oid,'sha256':weight.lfs.sha256,'bytes':weight.size,
            'code_uploaded':True,'prediction_verified':False}
    (ROOT/'deployment.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Private inference code and original checkpoint uploaded and verified. Build/inference still require verification.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Space upload did not complete:',type(exc).__name__)
        raise SystemExit(1) from None
