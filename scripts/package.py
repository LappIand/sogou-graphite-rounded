"""Audit the explicit public file list and create a clean attributed release ZIP."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import configparser, hashlib, json, re, struct

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_FILES=[
    'README.md','ATTRIBUTION.md','.gitignore','.gitattributes','requirements.txt',
    'assets/preview.png','assets/layouts.png',
    'native/Graphite-Light.dat','native/Graphite-Dark.dat','native/Manage-GraphiteNativeTheme.ps1',
    'skins/Graphite-Rounded-Light.ssf','skins/Graphite-Rounded-Dark.ssf',
    'source/Graphite-with_shadow.original.ssf','source/Graphite-Dark-with_shadow.ssf',
    'source/panel-geometry.json','source/manifest.json','source/Manage-GraphiteNativeTheme.template.ps1',
    'scripts/build.py','scripts/package.py','scripts/publish.py',
    'docs/INSTALL.md','docs/BUILD.md','docs/VALIDATION.md','docs/RELEASE-v1.3.0.md',
    'docs/resource-validation.json','docs/installer-validation.json','docs/build-validation.json',
]
VERSION='v1.3.0'
PACKAGE_NAME='Graphite-Rounded-Native-LightDark.zip'


def native_members(data):
    assert data[:4]==b'Skin' and struct.unpack_from('<I',data,8)[0]==len(data)-8
    result={}
    for i in range(struct.unpack_from('<I',data,12)[0]//4):
        at=8+struct.unpack_from('<I',data,16+4*i)[0]
        n=struct.unpack_from('<I',data,at)[0];name=data[at+4:at+4+n].decode('utf-16-le');at+=4+n
        n=struct.unpack_from('<I',data,at)[0];result[name]=data[at+4:at+4+n]
    return result


def audit():
    token_pattern=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{40,})')
    private_patterns=[r'[A-Za-z]:[/\\]Users[/\\][^\s"\']+',r'[A-Za-z]:[/\\]dsh[/\\]',r'AppData[/\\]LocalLow']
    files=[]
    for name in PUBLIC_FILES:
        path=ROOT/name
        assert path.is_file() and not path.is_symlink(),f'Missing or linked public file: {name}'
        data=path.read_bytes()
        if path.suffix.lower() in ('.md','.py','.ps1','.json','.txt'):
            text=data.decode('utf-8-sig')
            assert not token_pattern.search(text),f'Credential-like text found in {name}'
            assert not any(re.search(pattern,text,re.I) for pattern in private_patterns),f'Host-specific path found in {name}'
        files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for name in ('README.md','ATTRIBUTION.md','docs/RELEASE-v1.3.0.md'):
        text=(ROOT/name).read_text(encoding='utf-8')
        assert 'xiaochunjimmy' in text and 'Jimmy Cheung' in text and 'jrfeng' in text,name
    manager=(ROOT/'native/Manage-GraphiteNativeTheme.ps1').read_text(encoding='utf-8')
    assert "[string]$Action = 'Check'" in manager
    for label in ('Light','Dark'):
        raw=(ROOT/f'native/Graphite-{label}.dat').read_bytes()
        assert hashlib.sha256(raw).hexdigest() in manager
        members=native_members(raw)
        assert len(members)==49
        ini=configparser.ConfigParser(interpolation=None);ini.read_string(members['skin.ini'].decode('utf-16'))
        assert ini['General']['skin_author']=='jrfeng'
        with ZipFile(ROOT/f'skins/Graphite-Rounded-{label}.ssf') as z:
            assert z.testzip() is None and set(z.namelist())==set(members)
            for name in members:assert z.read(name)==members[name]
    checks=json.loads((ROOT/'docs/build-validation.json').read_text(encoding='utf-8'))
    assert sum(v['fixed_corner_stretch_tests'] for v in checks['variants'].values())==120
    tests=json.loads((ROOT/'docs/installer-validation.json').read_text(encoding='utf-8'))
    assert len(tests['Tests'])==10 and all(t['Status']=='passed' for t in tests['Tests'])
    return files


def package():
    files=audit()
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    archive=dist/PACKAGE_NAME
    entries={
        'README.md':ROOT/'README.md','ATTRIBUTION.md':ROOT/'ATTRIBUTION.md',
        'assets/preview.png':ROOT/'assets/preview.png','assets/layouts.png':ROOT/'assets/layouts.png',
        'Graphite-Light.dat':ROOT/'native/Graphite-Light.dat',
        'Graphite-Dark.dat':ROOT/'native/Graphite-Dark.dat',
        'Manage-GraphiteNativeTheme.ps1':ROOT/'native/Manage-GraphiteNativeTheme.ps1',
        'extras/Graphite-Rounded-Light.ssf':ROOT/'skins/Graphite-Rounded-Light.ssf',
        'extras/Graphite-Rounded-Dark.ssf':ROOT/'skins/Graphite-Rounded-Dark.ssf',
    }
    install=(ROOT/'docs/INSTALL.md').read_text(encoding='utf-8').replace('(../ATTRIBUTION.md)','(ATTRIBUTION.md)')
    validation={'version':VERSION,'target_sogou':'16.6.0.4777','design_author':'xiaochunjimmy (Jimmy Cheung / Remix Design)','windows_port_author':'jrfeng','radius_px':8,'stretch_checks':120,'installer_fixture_checks':10,'runtime_compatibility_not_claimed':True}
    with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for name,path in entries.items():z.writestr(name,path.read_bytes())
        z.writestr('使用说明.md',install.encode('utf-8'))
        z.writestr('validation.json',json.dumps(validation,ensure_ascii=False,indent=2).encode('utf-8'))
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(entries)|{'使用说明.md','validation.json'}
        for name,path in entries.items():assert z.read(name)==path.read_bytes()
        assert 'xiaochunjimmy' in z.read('ATTRIBUTION.md').decode('utf-8') and 'jrfeng' in z.read('ATTRIBUTION.md').decode('utf-8')
    source_archive=dist/('Graphite-Rounded-Source-'+VERSION+'.zip')
    with ZipFile(source_archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for name in PUBLIC_FILES:z.writestr('sogou-graphite-rounded/'+name,(ROOT/name).read_bytes())
    with ZipFile(source_archive) as z:
        assert z.testzip() is None and len(z.namelist())==len(PUBLIC_FILES)
        for name in PUBLIC_FILES:assert z.read('sogou-graphite-rounded/'+name)==(ROOT/name).read_bytes()
    (dist/'public-file-manifest.json').write_text(json.dumps({'public_files':files,'release_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_archive_sha256':hashlib.sha256(source_archive.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Public allowlist audit passed:',len(files),'files')
    print('Attributed release package:',archive.name)
    print('SHA256:',hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive


if __name__=='__main__':package()
