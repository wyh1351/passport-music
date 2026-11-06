#!/usr/bin/env python3
"""Build nine static, flash-resident I8 backgrounds; Pillow13.0.0."""
from pathlib import Path
import hashlib,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
out=['// User-supplied images: see assets/README.md for provenance.',
     '#include "music_wallpapers.h"',
     '#if LV_BIN_DECODER_RAM_LOAD',
     '#error "Wallpapers require row decoding on this board without PSRAM"',
     '#endif']
inventory=[]
for index in range(1,10):
    path=ROOT/f'assets/images/wallpapers/{index:02d}.jpg'
    image=Image.open(path).convert('RGB');size=image.size
    h=round(image.height*240/image.width)
    image=image.resize((240,h),Image.Resampling.NEAREST).crop((0,h-320,240,h))
    image.putdata([tuple(round(c*(.84 if y<112 else .80 if y<250 else .68)) for c in image.getpixel((x,y))) for y in range(320) for x in range(240)])
    indexed=image.quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    colors=indexed.getpalette();data=bytearray()
    for j in range(256):
        r,g,b=colors[j*3:j*3+3];data.extend((b,g,r,255))
    data.extend(indexed.tobytes())
    name=f'music_wallpaper_{index}'
    out.append(f'static const uint8_t {name}_data[]={{')
    out.extend(','.join(str(v) for v in data[j:j+48])+',' for j in range(0,len(data),48));out.append('};')
    out.append(f'static const lv_image_dsc_t {name}={{.header={{.magic=LV_IMAGE_HEADER_MAGIC,.cf=LV_COLOR_FORMAT_I8,.w=240,.h=320,.stride=240}},.data_size=sizeof({name}_data),.data={name}_data}};')
    inventory.append({'index':index,'source':path.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_size':size,'image_bytes':len(data),'image_sha256':hashlib.sha256(data).hexdigest()})
out.append('const lv_image_dsc_t *music_wallpaper_image(int selected) {')
out.append('    static const lv_image_dsc_t *images[]={NULL,'+','.join(f'&music_wallpaper_{i}' for i in range(1,10))+'};')
out.append('    return selected>=1 && selected<=9?images[selected]:NULL;\n}')
dest=ROOT/'assets/images/music_wallpapers.c';dest.write_text('\n'.join(out)+'\n',encoding='utf-8',newline='\n')
record={'format':'LVGL I8 BGRA palette','width':240,'height':320,'pillow':Image.__version__,'images':inventory,'total_image_bytes':sum(i['image_bytes'] for i in inventory),'generated_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
(ROOT/'assets/images/wallpapers/inventory.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Nine static wallpapers:',record['total_image_bytes'],'Flash bytes; no full-frame RAM buffer.')
