import numpy as np
from PIL import Image, ImageFilter, ImageDraw
rng=np.random.default_rng(1937)
page=Image.open('raw.png').convert('L'); W,H=page.size
ink=1-np.asarray(page).astype(np.float32)/255.0            # 1 = full ink

def noise(scale, sigma):
    n=rng.random((H//scale+2, W//scale+2)).astype(np.float32)
    img=Image.fromarray((n*255).astype(np.uint8)).resize((W,H),Image.BICUBIC).filter(ImageFilter.GaussianBlur(sigma))
    return np.asarray(img).astype(np.float32)/255.0

# ink: slight spread, uneven density, specks of missing ink
inkimg=Image.fromarray((ink*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
ink=np.asarray(inkimg).astype(np.float32)/255.0
dens=0.80+0.20*noise(6,3)                                # mottled pressure
fine=rng.random((H,W)).astype(np.float32)
ink=ink*dens*np.where(fine<0.012,0.55,1.0)
ink=np.clip(ink*1.08,0,1)

# show-through of the back page (mirrored), very faint
back=1-np.asarray(Image.open('raw.png').convert('L').transpose(Image.FLIP_LEFT_RIGHT).filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32)/255.0
back=np.roll(back,(14,-9),axis=(0,1))

# paper colour: yellowed newsprint, darker toward edges, blotches, foxing
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
ex=np.minimum(xx,W-1-xx)/W; ey=np.minimum(yy,H-1-yy)/H
edge=np.clip(1-np.minimum(ex/0.06,1)*np.minimum(ey/0.04,1),0,1)**1.6   # 0 interior, 1 at edge
blot=noise(90,40); blot2=noise(25,12)
tone=0.10*edge+0.05*(blot-0.5)+0.025*(blot2-0.5)
base=np.array([233,219,186],np.float32)/255.0            # newsprint
paper=np.stack([base[i]-tone*(1.0 if i==0 else 1.25 if i==1 else 1.7) for i in range(3)],-1)
# foxing spots
fox=np.zeros((H,W),np.float32); fd=ImageDraw.Draw(foxi:=Image.new('L',(W,H),0))
for _ in range(70):
    x,y=rng.integers(0,W),rng.integers(0,H); r=rng.integers(2,9)
    fd.ellipse((x-r,y-r,x+r,y+r),fill=int(rng.integers(40,120)))
fox=np.asarray(foxi.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)/255.0
paper=paper-fox[...,None]*np.array([0.10,0.16,0.24])

# horizontal fold at the middle: crease line, shading either side, ink cracked along it
fy=H*0.5+6
dist=(yy-fy)
crease=np.exp(-(dist/5)**2)
shade=0.06*np.exp(-np.abs(dist)/140)*np.sign(dist).clip(0,1) + 0.035*np.exp(-np.abs(dist)/60)
paper=paper - shade[...,None]*np.array([1,1.1,1.25]) + crease[...,None]*0.07
ink=ink*(1-0.55*np.exp(-(dist/3)**2)*(rng.random((H,W))>0.3))
# vertical quarter-fold, fainter
fx=W*0.5; dx=xx-fx
paper=paper-0.025*np.exp(-np.abs(dx)/80)[...,None]+0.03*np.exp(-(dx/4)**2)[...,None]

inkc=np.array([0.10,0.09,0.08],np.float32)
out=paper*(1-ink[...,None])+inkc*ink[...,None]
out=out*(1-0.055*back[...,None])
out=np.clip(out,0,1)
img=Image.fromarray((out*255).astype(np.uint8),'RGB')

# rough edges: alpha mask with nibbled border and a small tear at the fold
mask=Image.new('L',(W,H),255); md=ImageDraw.Draw(mask)
def wob(n,amp):
    a=rng.normal(0,1,n//20+3); x=np.interp(np.linspace(0,len(a)-1,n),np.arange(len(a)),a)
    return np.abs(x)*amp+np.abs(rng.normal(0,0.6,n))
t=wob(W,2.5); b=wob(W,2.5); l=wob(H,2.5); r=wob(H,2.5)
pts=[(i,t[i]) for i in range(0,W,3)]+[(W-1-r[j],j) for j in range(0,H,3)]+[(i,H-1-b[i]) for i in range(W-1,0,-3)]+[(l[j],j) for j in range(H-1,0,-3)]
mask=Image.new('L',(W,H),0); md=ImageDraw.Draw(mask); md.polygon(pts,fill=255)
md.polygon([(W-1,fy-26),(W-30,fy-4),(W-22,fy+3),(W-1,fy+9)],fill=0)
mask=mask.filter(ImageFilter.GaussianBlur(0.8))
# scanner bed: dark grey, page slightly skewed, soft shadow
bg=Image.new('RGB',(W+160,H+160),(52,52,50))
shadow=Image.new('L',(W+160,H+160),0); shadow.paste(mask,(86,90)); shadow=shadow.filter(ImageFilter.GaussianBlur(14))
bg=Image.composite(Image.new('RGB',bg.size,(30,30,29)),bg,shadow.point(lambda v:int(v*0.7)))
bg.paste(img,(80,80),mask)
bg=bg.rotate(-0.45,resample=Image.BICUBIC,fillcolor=(52,52,50))
bg=bg.resize((bg.width*1500//bg.width, bg.height*1500//bg.width),Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2,60,2))
bg.save('bill-of-sale-1.jpg',quality=88)
print(bg.size)
