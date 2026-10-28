"""Publish this allowlisted project using an already authenticated GitHub CLI."""
from pathlib import Path
import argparse,base64,hashlib,json,os,re,shutil,subprocess,sys
from package import ROOT,PUBLIC_FILES,VERSION,package


def locate(name):
    found=shutil.which(name)
    if found:return found
    if name=='gh':
        candidate=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'GitHub CLI/gh.exe'
        if candidate.is_file():return str(candidate)
    raise RuntimeError(f'Missing CLI: {name}')


META=ROOT/'.publish'

def run(args,capture=None,check=True):
    META.mkdir(exist_ok=True)
    if capture:
        path=META/capture
        with path.open('w',encoding='utf-8') as handle:
            result=subprocess.run(args,cwd=ROOT,stdout=handle,stderr=None)
        output=path.read_text(encoding='utf-8-sig')
    else:
        result=subprocess.run(args,cwd=ROOT)
        output=''
    if check and result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {args[0]} {args[1]}')
    return result.returncode,output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',default='sogou-graphite-rounded',help='New repository name under the authenticated user')
    args=parser.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',args.repo),'Use a repository name, not an owner/repo pair'
    gh=locate('gh');git=locate('git')
    code,_=run([gh,'auth','status','--active'],check=False)
    if code:raise RuntimeError('Complete gh auth login in your browser, then run this publishing script again.')
    _,text=run([gh,'api','user'],'user.json');profile=json.loads(text)
    owner=profile['login'];identifier=profile['id'];nwo=f'{owner}/{args.repo}'
    archive=package()
    marker=META/'target.json'
    code,text=run([gh,'repo','view',nwo,'--json','nameWithOwner,url,isPrivate'],'repository.json',False)
    if code:
        run([gh,'repo','create',nwo,'--public','--description','Graphite 搜狗输入法圆角与深色适配；原设计 xiaochunjimmy，Windows 移植 jrfeng'])
        marker.write_text(json.dumps({'repository':nwo},indent=2),encoding='utf-8')
    else:
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8'))['repository']!=nwo:
            raise RuntimeError(f'Remote repository already exists and was not created by this publishing run: {nwo}. Choose another --repo name.')
        assert not json.loads(text)['isPrivate'],'The requested skin publication uses a public repository'
    if not (ROOT/'.git').is_dir():run([git,'init','-b','main',str(ROOT)])
    run([git,'config','--local','user.name',owner])
    run([git,'config','--local','user.email',f'{identifier}+{owner}@users.noreply.github.com'])
    # Repository-local credential configuration: no token in URLs or files.
    helper='!"'+str(Path(gh)).replace('\\','/')+'" auth git-credential'
    run([git,'config','--local','--replace-all','credential.https://github.com.helper',''])
    run([git,'config','--local','--add','credential.https://github.com.helper',helper])
    code,text=run([git,'remote','get-url','origin'],'origin.txt',False)
    url=f'https://github.com/{nwo}.git'
    if code:run([git,'remote','add','origin',url])
    else:assert text.strip()==url,'Existing origin does not match this publication'
    run([git,'add','--',*PUBLIC_FILES])
    _,text=run([git,'ls-files'],'tracked.txt')
    assert set(text.splitlines())==set(PUBLIC_FILES),'Unexpected tracked files; publication stopped before committing'
    code,_=run([git,'diff','--cached','--quiet'],check=False)
    if code==1:run([git,'commit','-m','Publish Graphite Rounded; credit xiaochunjimmy and jrfeng'])
    elif code:raise RuntimeError('Git staged change check failed')
    code,_=run([git,'push','--set-upstream','origin','main'],check=False)
    if code:run([git,'-c','http.proxy=','push','--set-upstream','origin','main'])
    assets=[archive,ROOT/'skins/Graphite-Rounded-Light.ssf',ROOT/'skins/Graphite-Rounded-Dark.ssf',ROOT/'assets/preview.png']
    code,_=run([gh,'release','view',VERSION,'--repo',nwo,'--json','url'],'existing-release.json',False)
    if code:
        run([gh,'release','create',VERSION,'--repo',nwo,'--target','main','--title','Graphite Rounded 1.2.0','--notes-file',str(ROOT/'docs/RELEASE-v1.2.0.md'),*[str(p) for p in assets]])
    else:
        run([gh,'release','upload',VERSION,'--repo',nwo,'--clobber',*[str(p) for p in assets]])
    _,text=run([gh,'repo','view',nwo,'--json','nameWithOwner,url,isPrivate'],'verified-repository.json');repository=json.loads(text)
    assert repository['nameWithOwner']==nwo and not repository['isPrivate']
    _,text=run([gh,'api',f'repos/{nwo}/contents/README.md'],'verified-readme.json');remote_readme=base64.b64decode(json.loads(text)['content']).decode('utf-8')
    assert 'xiaochunjimmy' in remote_readme and 'Jimmy Cheung' in remote_readme and 'jrfeng' in remote_readme
    _,text=run([git,'rev-parse','HEAD'],'local-head.txt');local_sha=text.strip()
    _,text=run([gh,'api',f'repos/{nwo}/commits/main'],'remote-head.json');assert json.loads(text)['sha']==local_sha
    _,text=run([gh,'api',f'repos/{nwo}/releases/tags/{VERSION}'],'verified-release.json');release=json.loads(text)
    assert not release['draft'] and release['tag_name']==VERSION
    remote_assets={a['name']:a for a in release['assets']}
    downloads=[]
    for path in assets:
        asset=remote_assets[path.name]
        assert asset['state']=='uploaded' and asset['size']==path.stat().st_size
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if asset.get('digest'):assert asset['digest']=='sha256:'+sha
        downloads.append({'name':path.name,'url':asset['browser_download_url'],'sha256':sha})
    result={'repository':repository['url'],'release':release['html_url'],'commit':local_sha,'version':VERSION,'verified_author_attribution':True,'verified_public_file_count':len(PUBLIC_FILES),'assets':downloads}
    (META/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (RuntimeError,AssertionError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
