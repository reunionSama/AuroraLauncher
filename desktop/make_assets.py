"""Deterministic original technical textures / icon, not third-party launcher artwork."""
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).parent/'assets';r.mkdir(exist_ok=True)
im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
# Original Aurora explorer skin, Minecraft 64x64 UV layout.
for u,v,w,h,color in [(0,0,32,16,'#b98464'),(16,16,24,16,'#176979'),(40,16,16,16,'#197e8a'),(32,48,16,16,'#197e8a'),(0,16,16,16,'#1d2e45'),(16,48,16,16,'#1d2e45')]:d.rectangle((u,v,u+w-1,v+h-1),fill=color)
d.rectangle((0,0,31,7),fill='#233344');d.rectangle((8,8,15,9),fill='#233344');d.rectangle((8,10,8,14),fill='#233344');d.rectangle((15,10,15,14),fill='#233344')
d.point((10,11),fill='#edfbff');d.point((13,11),fill='#edfbff');d.point((10,12),fill='#164958');d.point((13,12),fill='#164958');d.rectangle((11,14,12,14),fill='#704135')
for u,v in [(44,20),(36,52)]:d.rectangle((u,v+9,u+3,v+11),fill='#b98464')
for u,v in [(4,20),(20,52)]:d.rectangle((u,v+9,u+3,v+11),fill='#0e192a')
d.rectangle((23,20,24,31),fill='#123746');d.polygon([(24,23),(25,25),(27,26),(25,27),(24,29),(23,27),(21,26),(23,25)],fill='#8ef5e3')
im.save(r/'aurora_skin.png')
icon=Image.new('RGBA',(256,256));p=ImageDraw.Draw(icon);p.rounded_rectangle((0,0,255,255),radius=58,fill='#0d2738');p.polygon([(128,35),(157,99),(221,128),(157,157),(128,221),(99,157),(35,128),(99,99)],fill='#16b8c5');p.polygon([(128,99),(157,128),(128,157),(99,128)],fill='#dcffff');icon.save(r/'icon.png');icon.save(r/'icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
