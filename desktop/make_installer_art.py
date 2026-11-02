"""Original deterministic aurora artwork for the native Windows setup wizard."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pathlib import Path
import math
out=Path(__file__).parent/'assets'
w,h=328,628
im=Image.new('RGB',(w,h));pix=im.load()
for y in range(h):
    for x in range(w):
        u=x/w;v=y/h
        glow=0.0
        for layer in range(3):
            top=.29+.045*math.sin(u*8+layer)+layer*.075
            glow+=math.exp(-((v-top)/.15)**2)*(.5+.5*math.sin(u*13+layer))*.34
        pix[x,y]=(int(7+glow*12),int(20+glow*115),int(32+glow*100))
d=ImageDraw.Draw(im)
for i in range(52):
    x=(i*7919)%w;y=(i*3571)%(h//2);d.ellipse((x,y,x+1,y+1),fill='#537984')
icon=Image.open(out/'icon.png').convert('RGBA').resize((70,70));im.paste(icon,(30,46),icon)
font_path=next((p for p in ['C:/Windows/Fonts/segoeuib.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if Path(p).exists()),None)
small_path=next((p for p in ['C:/Windows/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'] if Path(p).exists()),None)
font=ImageFont.truetype(font_path,28) if font_path else ImageFont.load_default()
small=ImageFont.truetype(small_path,14) if small_path else ImageFont.load_default()
d.text((30,145),'AURORA',font=font,fill='#e8ffff')
d.text((31,185),'L A U N C H E R',font=small,fill='#8fe5d7')
d.line((31,228,280,228),fill='#2b6570',width=1)
for y,title,subtitle in [(284,'YOUR WORLDS','Independent game instances'),(363,'YOUR STYLE','Skins, capes and aurora'),(442,'YOUR ADVENTURE','Ready when you are')]:
    d.ellipse((31,y+6,37,y+12),fill='#41d7c0');d.text((51,y),title,font=small,fill='#daf3f3');d.text((51,y+25),subtitle,font=small,fill='#90b3c2')
d.text((31,581),'reunionSama  /  Windows',font=small,fill='#6f9faa')
im.save(out/'setup-sidebar.bmp')
im=Image.new('RGB',(64,64),'#ffffff');icon=icon.resize((54,54));im.paste(icon,(5,5),icon);im.save(out/'setup-small.bmp')
