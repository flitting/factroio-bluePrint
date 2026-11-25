#!/usr/bin/env python3
"""Retrieve pinned external research inputs from their public source URLs.

No external blueprint contents are embedded in this script. Source byte hashes
are checked before use. Forum-hosted strings require the public author page to
be readable; when denied by the host, provide an author-downloaded source file
and validate it against source-catalog.json. No credentials are used.
"""
import argparse,base64,hashlib,json,re,urllib.request,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def retrieve(row):
 target=ROOT/row['local_source']
 if target.exists():
  actual=hashlib.sha256(target.read_bytes()).hexdigest()
  if actual==row['sha256']:return {'id':row['id'],'status':'already_verified'}
  raise RuntimeError(f'Existing source does not match pinned digest: {target}')
 if row['retrieval']=='raw_json':
  data=urllib.request.urlopen(row['source_url'],timeout=60).read()
 elif row['retrieval']=='forum_blueprint_string':
  page=urllib.request.urlopen(row['source_url'],timeout=60).read().decode()
  data=None
  for string in re.findall(r'\b0eN[A-Za-z0-9+/=]{500,}',page):
   try:
    decoded=json.loads(zlib.decompress(base64.b64decode(string[1:])))
   except Exception:continue
   if decoded.get('blueprint',{}).get('label')==row['upstream_label']:
    candidate=(string+'\n').encode()
    if hashlib.sha256(candidate).hexdigest()==row['sha256']:data=candidate;break
  if data is None:raise RuntimeError('Pinned blueprint not found on public author page: '+row['id'])
 else:raise RuntimeError('Unknown retrieval mode')
 assert hashlib.sha256(data).hexdigest()==row['sha256'],('source digest changed',row['id'])
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 if target.suffix=='.txt':
  decoded=json.loads(zlib.decompress(base64.b64decode(data.decode().strip()[1:])));target.with_suffix('.json').write_text(json.dumps(decoded,indent=2))
 return {'id':row['id'],'status':'downloaded_verified'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');args=p.parse_args()
 rows=json.loads((HERE/'source-catalog.json').read_text())['sources']
 for row in rows:
  if args.ids and row['id'] not in args.ids:continue
  try:print(json.dumps(retrieve(row)))
  except Exception as e:print(json.dumps({'id':row['id'],'status':'failed','error':str(e)}))
