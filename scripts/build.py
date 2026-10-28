"""Build the derived Graphite skins. Original design: xiaochunjimmy; Windows port: jrfeng.
Requires Python 3.10+ and Pillow. All output remains in the workspace.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import configparser, hashlib, io, json, re, struct

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/rounded'
OUT.mkdir(parents=True,exist_ok=True)
for folder in ('native','skins','assets','docs'):(ROOT/folder).mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
RADIUS=8
BORDER=1
SCALE=6
GUARD=2
BACKGROUNDS={'skin1.png','skin1_2.png','skin2.png','skin2_1.png','skin2_2.png','bar.png'}
GEOMETRY=json.loads((ROOT/'source/panel-geometry.json').read_text(encoding='utf-8'))
source_manifest=json.loads((ROOT/'source/manifest.json').read_text(encoding='utf-8'))
for sample in source_manifest['samples']:
    assert hashlib.sha256((ROOT/sample['path']).read_bytes()).hexdigest()==sample['sha256'],'Source sample checksum mismatch'
# This build does not inspect or modify an installed input method.

def rounded_panel(name,dark):
    geometry=GEOMETRY[name]
    w,h=geometry['size']; x1,y1,x2,y2=geometry['body_box']
    assert 2*RADIUS<=min(x2-x1,y2-y1)
    fill=(36,38,43) if dark else (255,255,255)
    border=(60,64,72) if dark else (225,229,235)
    high=Image.new('RGBA',(w*SCALE,h*SCALE))
    draw=ImageDraw.Draw(high)
    outer=(x1*SCALE,y1*SCALE,x2*SCALE-1,y2*SCALE-1)
    inner=((x1+BORDER)*SCALE,(y1+BORDER)*SCALE,(x2-BORDER)*SCALE-1,(y2-BORDER)*SCALE-1)
    draw.rounded_rectangle(outer,RADIUS*SCALE,fill=(*border,255))
    draw.rounded_rectangle(inner,(RADIUS-BORDER)*SCALE,fill=(*fill,255))
    panel=high.resize((w,h),Image.Resampling.LANCZOS)
    # Shadow follows the NEW rounded silhouette, not the old rectangle.
    silhouette=Image.new('L',(w,h))
    silhouette.paste(panel.getchannel('A'),(0,2))
    shadow=silhouette.filter(ImageFilter.GaussianBlur(2.3))
    strength=.28 if dark else .20
    shadow=shadow.point(lambda v:round(v*strength))
    layer=Image.new('RGBA',(w,h),(0,0,0,0));layer.putalpha(shadow)
    layer.alpha_composite(panel)
    assert layer.getpixel((w//2,h//2))==(*fill,255)
    assert layer.getpixel((x1,y1))[3]<45,'corner must be transparent apart from soft shadow'
    assert layer.getpixel((x2-1,y1))[3]<45
    assert layer.getpixel((x1,y2-1))[3]<45
    assert layer.getpixel((x2-1,y2-1))[3]<45
    data=io.BytesIO();layer.save(data,format='PNG',optimize=True)
    return data.getvalue()


def safe_cuts(name):
    left,top,right,bottom=GEOMETRY[name]['insets']
    return [left+RADIUS+GUARD,top+RADIUS+GUARD,right+RADIUS+GUARD,bottom+RADIUS+GUARD]


def update_ini(raw,dark):
    text=raw.decode('utf-16')
    parser=configparser.ConfigParser(interpolation=None);parser.read_string(text)
    changes=[]
    for section in ('Scheme_H1','Scheme_H2','Scheme_V1','Scheme_V2'):
        for prefix in ('','pinyin_','zhongwen_'):
            key=prefix+'pic'
            if key not in parser[section]:continue
            name=parser[section][key]
            cuts=safe_cuts(name); w,h=GEOMETRY[name]['size']
            for axis,a,b,total in (('horizontal',cuts[0],cuts[2],w),('vertical',cuts[1],cuts[3],h)):
                layout=prefix+'layout_'+axis
                old=parser[section][layout]
                mode,left,right=map(int,old.split(','))
                new=f'{mode},{max(left,a)},{max(right,b)}'
                assert max(left,a)+max(right,b)<total,(section,layout,new,total)
                if new!=old:
                    parser[section][layout]=new
                    changes.append({'section':section,'key':layout,'old':old,'new':new})
    # Target only known section/key lines; preserve original order and CRLF.
    current=''; lines=[]
    for line in text.splitlines(keepends=True):
        stripped=line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):current=stripped[1:-1]
        if '=' in line and not stripped.startswith((';','#')):
            key=line.split('=',1)[0]
            replacement=next((c['new'] for c in changes if c['section']==current and c['key']==key),None)
            if replacement is not None:
                ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
                line=f'{key}={replacement}{ending}'
        lines.append(line)
    text=''.join(lines)
    text,count=re.subn(r'(?m)^skin_name=[^\r\n]*','skin_name='+('Graphite Rounded Dark' if dark else 'Graphite Rounded'),text)
    assert count==1
    text,count=re.subn(r'(?m)^skin_version=[^\r\n]*','skin_version=1.2',text);assert count==1
    return text.encode('utf-16'),changes


def pack_native(items):
    n=len(items)*4;body=bytearray();offsets=[]
    for name,data in items:
        offsets.append(8+n+len(body));encoded=name.encode('utf-16-le')
        body+=struct.pack('<I',len(encoded))+encoded+struct.pack('<I',len(data))+data
    return b'Skin'+struct.pack('<III',1,8+n+len(body),n)+struct.pack('<'+'I'*len(offsets),*offsets)+body


def unpack_native(raw):
    assert raw[:4]==b'Skin' and struct.unpack_from('<I',raw,8)[0]==len(raw)-8
    count=struct.unpack_from('<I',raw,12)[0]//4;items=[]
    for i in range(count):
        at=8+struct.unpack_from('<I',raw,16+4*i)[0]
        n=struct.unpack_from('<I',raw,at)[0];name=raw[at+4:at+4+n].decode('utf-16-le');at+=4+n
        n=struct.unpack_from('<I',raw,at)[0];items.append((name,raw[at+4:at+4+n]))
    return items


def nine_patch(image,size,cuts):
    l,t,r,b=cuts;w,h=image.size
    assert size[0]>=l+r and size[1]>=t+b
    out=Image.new('RGBA',size)
    sx=(0,l,w-r,w);sy=(0,t,h-b,h)
    dx=(0,l,size[0]-r,size[0]);dy=(0,t,size[1]-b,size[1])
    for row in range(3):
        for col in range(3):
            p=image.crop((sx[col],sy[row],sx[col+1],sy[row+1]))
            p=p.resize((dx[col+1]-dx[col],dy[row+1]-dy[row]),Image.Resampling.BICUBIC)
            out.paste(p,(dx[col],dy[row]))
    # Fixed corner tiles must remain byte-identical under stretch.
    for sb,db in (((0,0,l,t),(0,0,l,t)),((w-r,0,w,t),(size[0]-r,0,size[0],t)),((0,h-b,l,h),(0,size[1]-b,l,size[1])),((w-r,h-b,w,h),(size[0]-r,size[1]-b,size[0],size[1]))):
        assert image.crop(sb).tobytes()==out.crop(db).tobytes()
    return out


variants={};report={'radius_px':RADIUS,'border_px':BORDER,'supersampling':SCALE,'shadow_blur_px':2.3,'shadow_offset_px':[0,2],'font_and_candidate_margins':'unchanged','variants':{},'originals_preserved':True,'installation_performed':False}
for dark,source,label in ((False,'Graphite-with_shadow.original.ssf','Light'),(True,'Graphite-Dark-with_shadow.ssf','Dark')):
    with ZipFile(ROOT/'source'/source) as z:
        assert z.testzip() is None
        original={name:z.read(name) for name in z.namelist()}
    members=dict(original)
    members['skin.ini'],changes=update_ini(original['skin.ini'],dark)
    for name in BACKGROUNDS:members[name]=rounded_panel(name,dark)
    # All non-background assets unchanged, including every icon/arrow state.
    for name in original.keys()-BACKGROUNDS-{'skin.ini'}:assert original[name]==members[name]
    before=configparser.ConfigParser(interpolation=None);before.read_string(original['skin.ini'].decode('utf-16'))
    after=configparser.ConfigParser(interpolation=None);after.read_string(members['skin.ini'].decode('utf-16'))
    allowed={(c['section'],c['key']) for c in changes}|{('General','skin_name'),('General','skin_version')}
    for section in before.sections():
        for key,value in before[section].items():
            if (section,key) not in allowed:assert after[section][key]==value,(section,key)
    assert members['skin.ini'].startswith(b'\xff\xfe')
    references=set(re.findall(r'[\w-]+\.(?:png|bmp)',members['skin.ini'].decode('utf-16')))
    assert references<=members.keys()
    for name in references:
        old=Image.open(io.BytesIO(original[name]));new=Image.open(io.BytesIO(members[name]));assert old.size==new.size
        new.verify()
    ssf=OUT/f'Graphite-Rounded-{label}.ssf'
    with ZipFile(ssf,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in members.items():z.writestr(name,data)
    with ZipFile(ssf) as z:assert z.testzip() is None and set(z.namelist())==set(original)
    dat=pack_native(list(members.items()));assert unpack_native(dat)==list(members.items())
    (OUT/f'Graphite-{label}.dat').write_bytes(dat)
    (OUT/f'Graphite-Rounded-{label}.ini').write_text(members['skin.ini'].decode('utf-16'),encoding='utf-8')
    variants[label]=(members,after)
    tests=0
    for name in BACKGROUNDS-{'bar.png'}:
        im=Image.open(io.BytesIO(members[name])).convert('RGBA');cuts=safe_cuts(name)
        for width in (im.width,160,460,820):
            for height in (im.height,100,320):
                nine_patch(im,(width,height),cuts);tests+=1
    report['variants'][label]={'member_count':len(members),'image_references':len(references),'layout_slice_updates':changes,'fixed_corner_stretch_tests':tests,'native_sha256':hashlib.sha256(dat).hexdigest(),'ssf_sha256':hashlib.sha256(ssf.read_bytes()).hexdigest()}

# Reuse the audited installer without changing backup location or restore logic.
manager=(ROOT/'source/Manage-GraphiteNativeTheme.template.ps1').read_text(encoding='utf-8')
for label,old in (('Light','4c3b6d9aea7e566542458c424211ba0e50e82183aa23f4c191279c00fb56abfd'),('Dark','b7f0aca32ac96f99b6675fa602d8489c4b309126a7abc11d29ebd15125ef414a')):
    assert manager.count(old)==1;manager=manager.replace(old,report['variants'][label]['native_sha256'])
(OUT/'Manage-GraphiteNativeTheme.ps1').write_text(manager,encoding='utf-8')

import os
FONT_PATH=os.environ.get('GRAPHITE_FONT','C:/Windows/Fonts/msyh.ttc')
if Path(FONT_PATH).is_file():
    # Render preview using the packaged assets at 2x for visibly inspectable radii.
    canvas=Image.new('RGB',(1200,790),'#15171C');draw=ImageDraw.Draw(canvas)
    fontpath=FONT_PATH;font=lambda size:ImageFont.truetype(fontpath,size)
    primary=(232,234,237);secondary=(182,187,198)
    draw.text((48,34),'Graphite · Rounded',font=font(34),fill=primary)
    draw.text((50,93),'8px 圆角  /  1px 细边框  /  柔和阴影',font=font(20),fill=secondary)
    for index,label in enumerate(('Light','Dark')):
        members,parser=variants[label];y=147+index*235
        draw.text((49,y), '浅色 / LIGHT' if label=='Light' else '深色 / DARK',font=font(18),fill=secondary)
        im=Image.open(io.BytesIO(members['skin1.png'])).convert('RGBA')
        section=parser['Scheme_H1']
        _,left,right=map(int,section['layout_horizontal'].split(','));_,top,bottom=map(int,section['layout_vertical'].split(','))
        pane=nine_patch(im,(400,84),(left,top,right,bottom));pd=ImageDraw.Draw(pane)
        p=(10,15,40) if label=='Light' else primary;s=(89,99,119) if label=='Light' else secondary
        pd.text((22,13),'ni hao shi jie',font=font(16),fill=p)
        x=22
        for i,word in enumerate(('你好','世界','输入法','圆角','深色'),1):
            text=f'{i}.{word}';pd.text((x,39),text,font=font(16),fill=p if i==1 else s)
            x+=int(pd.textlength(text,font=font(16)))+13
        arrow=Image.open(io.BytesIO(members['ov_pagedown_on3.png'])).convert('RGBA');pane.alpha_composite(arrow,(368,45))
        pane=pane.resize((800,168),Image.Resampling.LANCZOS);canvas.paste(pane,(42,y+30),pane)
        bar=Image.open(io.BytesIO(members['bar.png'])).convert('RGBA')
        for name,xy in (('cn3.png',(34,16)),('cn_biaodian3.png',(90,13))):
            bar.alpha_composite(Image.open(io.BytesIO(members[name])).convert('RGBA'),xy)
        bar=bar.resize((248,128),Image.Resampling.LANCZOS);canvas.paste(bar,(894,y+48),bar)
        draw.text((976,y+176),'状态栏',font=font(17),fill=secondary)
    draw.text((50,633),'横排、竖排和分窗口均适配；字号与候选间距保持原样。',font=font(20),fill=secondary)
    draw.text((50,684),'预览放大 2 倍展示圆角细节；实际资源圆角为 8px。',font=font(17),fill='#858D9C')
    draw.text((50,721),'使用包内真实图像资源绘制的示意图，非搜狗安装后的运行截图。',font=font(16),fill='#858D9C')
    canvas.save(ROOT/'assets/preview.png')

    # Four-layout montage, drawing only backgrounds to inspect stretch geometry.
    sheet=Image.new('RGB',(1300,960),'#17191E');sd=ImageDraw.Draw(sheet)
    for vi,label in enumerate(('Light','Dark')):
        members,parser=variants[label]
        for si,section in enumerate(('Scheme_H1','Scheme_H2','Scheme_V1','Scheme_V2')):
            x=28+vi*644;y=25+si*230
            sd.text((x,y),label+' / '+section,font=font(18),fill=secondary)
            prefices=('',) if 'pic' in parser[section] else ('pinyin_','zhongwen_')
            px=x
            for prefix in prefices:
                name=parser[section][prefix+'pic'];im=Image.open(io.BytesIO(members[name])).convert('RGBA')
                _,l,r=map(int,parser[section][prefix+'layout_horizontal'].split(','));_,t,b=map(int,parser[section][prefix+'layout_vertical'].split(','))
                size=(570,94) if section=='Scheme_H1' else (260,105) if section=='Scheme_H2' else (205,166)
                tile=nine_patch(im,size,(l,t,r,b));sheet.paste(tile,(px,y+30),tile);px+=size[0]+12
    sheet.save(ROOT/'assets/layouts.png')

else:
    print('Preview rendering skipped: set GRAPHITE_FONT to a CJK font file to regenerate previews.')

for label in ('Light','Dark'):
    for filename,directory in ((f'Graphite-{label}.dat','native'),(f'Graphite-Rounded-{label}.ssf','skins')):
        (ROOT/directory/filename).write_bytes((OUT/filename).read_bytes())
(ROOT/'native/Manage-GraphiteNativeTheme.ps1').write_bytes((OUT/'Manage-GraphiteNativeTheme.ps1').read_bytes())
report['build_scope']='Repository files only; no input-method installation files read or changed.'
(ROOT/'docs/build-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
