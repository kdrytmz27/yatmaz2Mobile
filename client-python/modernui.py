# Shared native-rendered mobile theme. No stretched bitmap panel skins.
import grp
import math

PANEL = 0xf21b1c20
SURFACE = 0xff29292c
BORDER = 0xff776c58
ACCENT = 0xffcfad70
TEXT = 0xffeee5d5
MUTED = 0xffb8a78e

def Bar(x, y, w, h, color):
	if w <= 0 or h <= 0: return
	grp.SetColor(color)
	grp.RenderBar(int(x), int(y), int(w), int(h))

def Line(x, y, w, h, color):
	grp.SetColor(color)
	grp.RenderLine(int(round(x)), int(round(y)), int(round(x+w))-int(round(x)), int(round(y+h))-int(round(y)))

def Circle(x,y,r,color,segments=20):
	for i in range(segments):
		a=i*2*math.pi/segments; b=(i+1)*2*math.pi/segments
		Line(x+math.cos(a)*r,y+math.sin(a)*r,(math.cos(b)-math.cos(a))*r,(math.sin(b)-math.sin(a))*r,color)

def Card(x, y, w, h, fill=PANEL, edge=BORDER, radius=5):
	r = min(radius, int(w / 2), int(h / 2))
	Bar(x+r, y, w-2*r, h, fill)
	Bar(x, y+r, r, h-2*r, fill)
	Bar(x+w-r, y+r, r, h-2*r, fill)
	for i in range(r):
		inset = r-int(math.sqrt(max(0, r*r-(r-i-0.5)**2)))
		Bar(x+inset, y+i, r-inset, 1, fill)
		Bar(x+w-r, y+i, r-inset, 1, fill)
		Bar(x+inset, y+h-i-1, r-inset, 1, fill)
		Bar(x+w-r, y+h-i-1, r-inset, 1, fill)
	Line(x+r,y,w-2*r,0,edge)
	Line(x+r,y+h,w-2*r,0,edge)
	Line(x,y+r,0,h-2*r,edge)
	Line(x+w,y+r,0,h-2*r,edge)
	Line(x,y+r,r,-r,edge)
	Line(x+w-r,y,r,r,edge)
	Line(x,y+h-r,r,r,edge)
	Line(x+w-r,y+h,r,-r,edge)

def Disc(x,y,size,pressed=False,active=False):
 r=size/2.0
 # Scan bands fill the circle without bitmap stretching.
 for yy in range(0,int(size)):
  half=math.sqrt(max(0,r*r-(yy+0.5-r)**2))
  Bar(x+r-half,y+yy,half*2,1,0xe82c2020 if pressed else 0xe81b1d22)
 Circle(x+r,y+r,r-1,ACCENT if active or pressed else 0xffa18c67,40)
 Circle(x+r,y+r,r-4,0xff49433b,40)
 Circle(x+r,y+r,r-6,0xff272a30,40)


def Glyph(kind, x, y, size, color=TEXT):
	cx, cy = x+size/2, y+size/2
	d = size*0.23
	if kind == 'close':
		Line(cx-d,cy-d,d*2,d*2,color); Line(cx-d,cy+d,d*2,-d*2,color)
	elif kind == 'menu':
		for a in (-1,0,1): Bar(cx-d,cy+a*d,d*2,2,color)
	elif kind == 'attack':
		Line(cx-d,cy+d,d*2,-d*2,color)
		Line(cx-d+3,cy+d+3,d*2,-d*2,color)
		Line(cx-d-3,cy+d-7,11,11,color)
		Line(cx+d-4,cy-d,7,-3,color)
	elif kind == 'pickup':
		Line(cx,cy-d,0,d*1.5,color)
		Line(cx-d/2,cy, d/2,d/2,color); Line(cx,cy+d/2,d/2,-d/2,color)
		Line(cx-d,cy+d,d*2,0,color)
	elif kind in ('character','friends','names','emotes'):
		Circle(cx,cy-d/2,d/2,color,16)
		Line(cx-d,cy+d,d*2,0,color); Line(cx-d,cy+d,d/2,-d,color); Line(cx+d/2,cy,d/2,d,color)
		if kind == 'friends': Line(cx+d,cy-d,d/2,0,color)
	elif kind in ('skills','dragon'):
		Line(cx+d/2,cy-d,-d,d,color); Line(cx-d/2,cy,d,0,color); Line(cx+d/2,cy,-d,d,color)
	elif kind in ('quests','chat'):
		for a in (-1,0,1): Line(cx-d,cy+a*d/2,d*2,0,color)
		Line(cx-d-3,cy-d,0,d*2,color)
	elif kind == 'map':
		Line(cx-d,cy-d/2,d,-d/2,color); Line(cx,cy-d,d,d/2,color)
		Line(cx-d,cy+d,d,-d/2,color); Line(cx,cy+d/2,d,d/2,color)
		for xx in (-d,0,d): Line(cx+xx,cy-d/2,0,d*1.5,color)
	elif kind == 'settings':
		Circle(cx,cy,d*0.7,color)
		for a in range(8):
			t=a*math.pi/4; Line(cx+math.cos(t)*d*0.8,cy+math.sin(t)*d*0.8,math.cos(t)*d*0.45,math.sin(t)*d*0.45,color)
	elif kind == 'costume':
		Line(cx-d,cy-d,d/2,0,color); Line(cx+d/2,cy-d,d/2,0,color)
		Line(cx-d,cy-d,-d/2,d,color); Line(cx+d,cy-d,d/2,d,color)
		Line(cx-d/2,cy,0,d,color); Line(cx+d/2,cy,0,d,color); Line(cx-d/2,cy+d,d,0,color)
	elif kind == 'plus':
		Bar(cx-d,cy-1,d*2,2,color); Bar(cx-1,cy-d,2,d*2,color)
	elif kind == 'ride':
		Line(cx-d,cy,d*2,0,color); Line(cx-d,cy,0,d,color); Line(cx+d/2,cy,0,d,color)
		Line(cx+d/2,cy,d/2,-d,color); Line(cx+d,cy-d,d/2,d/2,color)
	else:
		# Inventory / utility icon: compact geometric container.
		Line(cx-d,cy-d,d*2,0,color); Line(cx-d,cy+d,d*2,0,color)
		Line(cx-d,cy-d,0,d*2,color); Line(cx+d,cy-d,0,d*2,color)
		Line(cx-d/2,cy-d-3,d,0,color)

def InventoryPanel(x,y,w,h):
 Bar(x+3,y+4,w,h,0x80000000)
 Bar(x,y,w,h,0xf51c1b1b)
 # Recessed dark interior, layered aged metal border and corner brackets.
 Bar(x+5,y+29,w-10,h-34,0xff171718)
 for inset,color in ((0,0xff141213),(1,0xff9b8b72),(2,0xff51483d),(4,0xff342e29)):
  Line(x+inset,y+inset,w-2*inset,0,color); Line(x+inset,y+h-inset,w-2*inset,0,color)
  Line(x+inset,y+inset,0,h-2*inset,color); Line(x+w-inset,y+inset,0,h-2*inset,color)
 for xx,yy,dx,dy in ((x+3,y+3,1,1),(x+w-3,y+3,-1,1),(x+3,y+h-3,1,-1),(x+w-3,y+h-3,-1,-1)):
  Line(xx,yy,10*dx,0,0xffcfb58b); Line(xx,yy,0,10*dy,0xffcfb58b)
  Line(xx+4*dx,yy+4*dy,5*dx,0,0xff806a4e); Line(xx+4*dx,yy+4*dy,0,5*dy,0xff806a4e)

def InventoryCell(x,y,w,h):
 Bar(x+1,y+1,w-2,h-2,0xff111214)
 Line(x,y,w-1,0,0xff796b53); Line(x,y,0,h-1,0xff796b53)
 Line(x+w-1,y,0,h-1,0xff39352f); Line(x,y+h-1,w-1,0,0xff39352f)
 Line(x+2,y+2,w-5,0,0xff242324)


def _HideSkin(self):
	for child in getattr(self,'Corners',[]) + getattr(self,'Lines',[]): child.Hide()
	if getattr(self,'Base',None): self.Base.Hide()

def _PanelRender(self):
	if getattr(self,'modernHidden',False): return
	x,y=self.GetGlobalPosition()
	w,h=self.GetWidth(),self.GetHeight()
	if getattr(self,'modernInventory',False):
		InventoryPanel(x,y,170,236)
		InventoryPanel(x+178,y,188,380)
		for row in range(9):
			for col in range(5): InventoryCell(x+190+col*32,y+62+row*32,32,32)
		for sx,sy,sw,sh in self.modernEquipSlots:
			InventoryCell(x+13+sx,y+41+sy,sw,sh)
		return
	Card(x+3,y+5,w,h,0x50000000,0x00000000)
	Card(x,y,w,h)
	Line(x+8,y+3,w-16,0,0xffb3a184)
	Line(x+8,y+h-3,w-16,0,0xff090a0d)
	for xx,yy,dx,dy in ((x+5,y+5,1,1),(x+w-5,y+5,-1,1),(x+5,y+h-5,1,-1),(x+w-5,y+h-5,-1,-1)):
	 Line(xx,yy,12*dx,0,ACCENT); Line(xx,yy,0,12*dy,ACCENT)

def _ButtonRender(self):
	name=getattr(self,'modernVisual','').lower()
	text=getattr(self,'ButtonText',None)
	close='close' in name and 'letter' not in name
	utility=any(s in name for s in ('tab_button','parameter_slot','middle_button','large_button','small_button','minimap_','atlas_open','dss_inventory_button','mall_button','costume_button','plus','minus','status_button','skill_button'))
	if not text and not close and not utility and not getattr(self,'modernForce',False): return
	x,y=self.GetGlobalPosition(); w,h=self.GetWidth(),self.GetHeight()
	down=self.IsDown(); hover=self.IsIn()
	Card(x,y,w,h,0xff654328 if down else (0xff4c3829 if hover else SURFACE),ACCENT if down else BORDER,3)
	if getattr(self,'modernForce',False): Glyph('quests',x,y,min(w,h),ACCENT)
	elif close: Glyph('close',x,y,min(w,h),MUTED)
	elif not text and 'scaleup' in name:
		Line(x+3,y+h/2,w-6,0,TEXT); Line(x+w/2,y+3,0,h-6,TEXT)
	elif not text and 'scaledown' in name: Line(x+3,y+h/2,w-6,0,TEXT)
	elif not text and 'minus' in name: Line(x+3,y+h/2,w-6,0,ACCENT)
	elif not text and 'tab_button' not in name and 'parameter_slot' not in name:
		kind='costume' if 'costume' in name else ('dragon' if 'dss_' in name else ('plus' if 'plus' in name or 'status_button' in name else ('map' if 'atlas_' in name else 'bag')))
		Glyph(kind,x,y,min(w,h),ACCENT)
	if text: text.SetPackedFontColor(TEXT if not down else ACCENT)

def Install(ui):
	for cls in (ui.Board,ui.ThinBoard):
		original=cls.SetSize
		def size(self,w,h,_original=original):
			_original(self,w,h); _HideSkin(self)
		cls.SetSize=size
		cls.OnRender=_PanelRender
	ui.ThinBoard.ShowInternal=lambda self: setattr(self,'modernHidden',False)
	ui.ThinBoard.HideInternal=lambda self: setattr(self,'modernHidden',True)
	old=ui.TitleBar.SetWidth
	def title(self,width):
		old(self,width)
		for obj in (self.imgLeft,self.imgCenter,self.imgRight): obj.Hide()
		self.btnClose.SetSize(22,22)
		self.btnClose.SetPosition(width-23,0)
	ui.TitleBar.SetWidth=title
	def titleRender(self):
		x,y=self.GetGlobalPosition(); Card(x,y,self.GetWidth(),self.GetHeight(),0xff4a1818,BORDER,3)
	ui.TitleBar.OnRender=titleRender
	oldVisual=ui.Button.SetUpVisual
	def visual(self,name):
		self.modernVisual=name; oldVisual(self,name)
	ui.Button.SetUpVisual=visual
	ui.Button.OnRender=_ButtonRender
	oldImage=ui.ImageBox.LoadImage
	def image(self,name):
		oldImage(self,name)
		if any(s in name.lower() for s in ('parameter_slot','slot_base','box_face','skill_board')):
			if not hasattr(self,'modernSurface'):
				layer=ui.Window(); layer.SetParent(self); layer.AddFlag('not_pick')
				def render():
					x,y=self.GetGlobalPosition(); Card(x,y,self.GetWidth(),self.GetHeight(),0xff23252b,0xff59564f,2)
				layer.OnRender=render; layer.Show(); self.modernSurface=layer
	ui.ImageBox.LoadImage=image
