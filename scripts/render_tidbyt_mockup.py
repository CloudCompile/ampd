from PIL import Image, ImageDraw, ImageFont
W,H,S=64,32,12
font8=ImageFont.truetype("/tmp/roboto.ttf",8); font6=ImageFont.truetype("/tmp/roboto.ttf",6); font5=ImageFont.truetype("/tmp/roboto.ttf",5)
accent=(250,45,72); white=(245,245,245); dim=(105,105,105); bg=(20,15,28)
def frame(title,album,artist,elapsed,duration,mode,playing=True):
 im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im)
 # blurred/pixelated background wash
 for y in range(H):
  d.line((0,y,W-1,y),fill=(24+(y%5)*5,12+(y%4)*4,32+(y%7)*7))
 # static clipped metadata
 def clip(x): return x[:7]+"." if len(x)>8 else x
 d.text((0,0),clip(title),font=font8,fill=white); d.text((0,8),clip(album),font=font8,fill=(220,220,220)); d.text((0,16),clip(artist),font=font8,fill=(210,210,210))
 frac=elapsed/duration if duration else 0; d.rectangle((0,27,25,30),outline=dim,width=1); d.rectangle((0,27,max(0,int(frac*25)),30),fill=accent) if frac else None
 sec=int(elapsed/1000); d.text((28,25),f"{sec//60}:{sec%60:02d}",font=font5,fill=white)
 if mode=="art":
  art=Image.new("RGB",(24,24),(80,20,110)); ad=ImageDraw.Draw(art); ad.ellipse((4,4,19,19),outline=accent,width=2); ad.ellipse((10,10,13,13),fill=white); im.paste(art,(40,4))
 elif mode=="lyrics":
  d.text((41,6),"before",font=font5,fill=dim); d.text((41,13),"CURRENT",font=font6,fill=white); d.text((41,23),"after",font=font5,fill=dim)
 else: d.text((42,14),"no lyrics",font=font5,fill=white)
 if playing: d.rectangle((40,4,42,6),fill=accent)
 out=Image.new("RGB",(W*S,H*S),(10,9,10)); od=ImageDraw.Draw(out)
 for y in range(H):
  for x in range(W):
   c=im.getpixel((x,y)); x0,y0=x*S+1,y*S+1; od.rounded_rectangle((x0,y0,x0+S-2,y0+S-2),radius=2,fill=c)
 return out
states=[("auto — lyrics available",frame("Just Between Us — natori","Just Between Us","natori",96000,260000,"lyrics")),("artwork fallback",frame("Overdose","Overdose - Single","natori",41000,197094,"art")),("paused",frame("Overdose","Overdose - Single","natori",41000,197094,"art",False)),("idle",frame("(idle)","tonearm","",0,0,"none",False))]
for name,im in states: im.save("/home/inferenceport/tidbyt-"+name.replace(" ","-").replace("—","-").replace("/","-")+'.png')
# contact sheet
sheet=Image.new("RGB",(W*S+40,(H*S+55)*len(states)),(24,24,28)); d=ImageDraw.Draw(sheet); y=15
for name,im in states: d.text((20,y),name,font=ImageFont.truetype("/tmp/roboto.ttf",20),fill=(220,220,220)); sheet.paste(im,(20,y+28)); y+=H*S+55
sheet.save("/home/inferenceport/tidbyt-carplay-mockup.png")
