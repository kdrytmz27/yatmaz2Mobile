# Touch HUD for the Android build: an attack button ringed by big quick-slot buttons, pick-up,
# and a wheel menu for what desktop players reach through hotkeys. Loaded only when m2profile
# exists (Android). The "HUD" game option switches between it and the desktop taskbar.
import math
import modernui
import app, item, net, player, skill, wndMgr
import emotion, mouseModule, ui, uiQuest

ART = "mobile/"
CONFIG = "mobilehud.cfg"
SLOT = 50
ATTACK = 80
SMALL = 42
REFRESH_SEC = 0.25
LABEL_COLOR = modernui.TEXT
T = "d:/ymir work/ui/game/taskbar/"
# stock taskbar icons carry their own square frame; crop it inside the round buttons
FRAMED = 0.13

# taskbar children that the mobile HUD replaces; the HP/SP/EXP gauges stay
DESKTOP_ONLY = ("Base_Board_01", "LeftMouseButton", "RightMouseButton", "CharacterButton",
		"InventoryButton", "MessengerButton", "SystemButton", "quickslot_board")

_hud = None


def IsMobileMode():
	try:
		f = open(CONFIG, "r")
		try:
			return f.read().strip() != "desktop"
		finally:
			f.close()
	except IOError:
		return app.IsTouchPrimary() != 0


def SetMobileMode(mobile):
	try:
		f = open(CONFIG, "w")
		try:
			f.write("mobile" if mobile else "desktop")
		finally:
			f.close()
	except IOError:
		pass
	if _hud:
		_hud.ApplyMode()


class _Label(ui.Window):
	def __init__(self, parent, height):
		ui.Window.__init__(self)
		self.SetParent(parent)
		self.AddFlag("not_pick")
		self.height = height
		self.back = ui.ExpandedImageBox()
		self.back.SetParent(self)
		self.back.AddFlag("not_pick")
		self.back.LoadImage(ART + "label.tga")
		self.back.Hide()
		self.text = ui.TextLine()
		self.text.SetParent(self)
		self.text.AddFlag("not_pick")
		self.text.SetPackedFontColor(LABEL_COLOR)
		self.text.SetHorizontalAlignCenter()
		self.text.SetVerticalAlignCenter()
		self.text.Show()

	def SetText(self, text, centerX, top):
		self.text.SetText(text)
		(tw, th) = self.text.GetTextSize()
		w = max(self.height + 4, tw + 12)
		self.SetSize(w, self.height)
		self.back.SetScale(float(w) / self.back.GetWidth(), float(self.height) / self.back.GetHeight())
		self.text.SetPosition(w / 2, self.height / 2)
		self.SetPosition(centerX - w / 2, top)
		self.Show()


class _Disc(ui.Window):
	def __init__(self, size, onTap, onPress = None):
		ui.Window.__init__(self)
		self.SetSize(size, size)
		self.size = size
		self.pressed = False
		self.active = False
		self.coolFraction = 0.0
		self.glyph = None
		self.onTap = onTap
		self.onPress = onPress
		self.base = self.__Image(ART + "button.tga", 1.0)
		self.icon = ui.ExpandedImageBox()
		self.icon.SetParent(self)
		self.icon.AddFlag("not_pick")
		self.cool = self.__Image(ART + "cooldown.tga", 1.0)
		self.cool.Hide()
		self.glow = self.__Image(ART + "active.tga", 1.0)
		self.glow.Hide()
		self.label = None
		self.iconName = None
		self.base.Hide()
		self.Show()

	def OnRender(self):
		x,y=self.GetGlobalPosition()
		modernui.Disc(x,y,self.size,self.pressed,self.active or self.glyph == "attack")
		if self.coolFraction > 0: modernui.Bar(x+4,y+self.size-5,(self.size-8)*self.coolFraction,2,modernui.ACCENT)
		if self.glyph: modernui.Glyph(self.glyph,x,y,self.size,modernui.ACCENT if self.glyph == "attack" else modernui.TEXT)

	def __Image(self, name, frac):
		img = ui.ExpandedImageBox()
		img.SetParent(self)
		img.AddFlag("not_pick")
		img.LoadImage(name)
		side = int(self.size * frac)
		img.SetScale(float(side) / img.GetWidth(), float(side) / img.GetHeight())
		img.SetPosition((self.size - side) / 2, (self.size - side) / 2)
		img.Show()
		return img

	def SetIcon(self, name, frac = 0.56, crop = 0.0):
		if name == self.iconName:
			return
		self.iconName = name
		if not name:
			self.icon.Hide()
			return
		self.icon.LoadImage(name)
		w, h = self.icon.GetWidth(), self.icon.GetHeight()
		if w <= 0 or h <= 0:
			self.icon.Hide()
			return
		side = self.size * frac
		s = min(side / (w * (1.0 - 2 * crop)), side / (h * (1.0 - 2 * crop)))
		self.icon.SetScale(s, s)
		self.icon.SetRenderingRect(-crop, -crop, -crop, -crop)
		self.icon.SetPosition(int((self.size - w * s) / 2), int((self.size - h * s) / 2))
		self.icon.Show()

	# key hint sits on the lower rim; names hang below the button
	def SetLabel(self, text, below = False):
		if not self.label:
			self.label = _Label(self, 18 if below else 15)
		self.label.SetText(text, self.size / 2, self.size + 2 if below else self.size - 15)

	def SetCoolDown(self, fraction):
		self.coolFraction = max(0.0,min(1.0,fraction))
		self.cool.Hide()

	def SetActive(self, on):
		self.active = on
		self.glow.Hide()

	def __Pressed(self, down):
		self.pressed = down
		self.icon.SetAlpha(0.7 if down else 1.0)

	def OnMouseLeftButtonDown(self):
		self.__Pressed(True)
		if self.onPress:
			self.onPress(True)
		return True

	def OnMouseLeftButtonUp(self):
		self.__Pressed(False)
		if self.onPress:
			self.onPress(False)
		elif self.IsIn():
			self.onTap()
		return True


class _Wheel(ui.Window):
	RADIUS = 175
	ITEM = 64

	def __init__(self, entries):
		ui.Window.__init__(self, "TOP_MOST")
		w, h = wndMgr.GetScreenWidth(), wndMgr.GetScreenHeight()
		self.SetSize(w, h)
		self.dim = ui.Bar("TOP_MOST")
		self.dim.SetParent(self)
		self.dim.AddFlag("not_pick")
		self.dim.SetSize(w, h)
		self.dim.SetColor(0x70000000)
		self.dim.Show()
		self.discs = []
		self.panel = ui.Board()
		self.panel.SetParent(self)
		self.panel.SetSize(470,330)
		self.panel.SetPosition((w-470)/2,(h-330)/2)
		self.panel.Show()
		self.heading=ui.TextLine()
		self.heading.SetParent(self.panel)
		self.heading.SetPosition(22,16)
		self.heading.SetText("ADVENTURE MENU")
		self.heading.SetPackedFontColor(modernui.ACCENT)
		self.heading.Show()
		for i, (label, icon, crop, action) in enumerate(entries):
			d = _Disc(50,self.__Choose(action))
			d.SetParent(self.panel)
			d.glyph = ('bag','character','skills','quests','emotes','map','chat','friends','names','ride','settings')[i]
			d.SetLabel(label,True)
			d.SetPosition(30+(i%4)*112,52+(i/4)*88)
			self.discs.append(d)
		self.Hide()

	def __Choose(self, action):
		def run():
			self.Hide()
			action()
		return run

	def Toggle(self):
		if self.IsShow():
			self.Hide()
		else:
			self.Show()
			self.SetTop()

	def OnMouseLeftButtonUp(self):
		self.Hide()
		return True


class HudOption:
	"""The 'HUD: Desktop / Mobile' row appended to the game options dialog."""
	ROOT = "d:/ymir work/ui/public/"

	def __init__(self, board, y, labelX, dataX, buttonWidth):
		self.label = ui.TextLine()
		self.label.SetParent(board)
		self.label.SetPosition(labelX, y + 2)
		self.label.SetText("HUD")
		self.label.Show()
		self.buttons = []
		for n, (text, mobile) in enumerate((("Desktop", False), ("Mobile", True))):
			b = ui.RadioButton()
			b.SetParent(board)
			b.SetUpVisual(self.ROOT + "middle_button_01.sub")
			b.SetOverVisual(self.ROOT + "middle_button_02.sub")
			b.SetDownVisual(self.ROOT + "middle_button_03.sub")
			b.SetPosition(dataX + buttonWidth * n, y)
			b.SetText(text)
			b.SetEvent(self.__Select, mobile)
			b.Show()
			self.buttons.append(b)
		self.__Refresh()

	def __Select(self, mobile):
		SetMobileMode(mobile)
		self.__Refresh()

	def __Refresh(self):
		on = 1 if IsMobileMode() else 0
		for n, b in enumerate(self.buttons):
			if n == on:
				b.Down()
			else:
				b.SetUp()

	def Destroy(self):
		self.buttons = []
		self.label = None


DISPLAY_CONFIG = "display.cfg"
UI_SCALE_MIN = 0.5
UI_SCALE_MAX = 1.5
FONT_SCALE_MIN = 1.0
FONT_SCALE_MAX = 1.6
CAMERA_MIN = 0.25
CAMERA_MAX = 2.0
VALUE_TEXT_WIDTH = 34


def _Clamp(value, low, high):
	return max(low, min(high, value))


def LoadDisplayConfig():
	"""display.cfg holds 'key value' lines; the engine reads ui_scale and camera_sensitivity."""
	conf = {"ui_scale": "1.0", "font_scale": "1.0", "orientation": "landscape", "camera_sensitivity": "1.0", "font": "default"}
	try:
		f = open(DISPLAY_CONFIG, "r")
		try:
			for line in f.readlines():
				parts = line.split()
				if len(parts) == 2:
					conf[parts[0]] = parts[1]
		finally:
			f.close()
	except IOError:
		pass
	for key, low, high in (("ui_scale", UI_SCALE_MIN, UI_SCALE_MAX), ("font_scale", FONT_SCALE_MIN, FONT_SCALE_MAX), ("camera_sensitivity", CAMERA_MIN, CAMERA_MAX)):
		try:
			conf[key] = _Clamp(float(conf[key]), low, high)
		except ValueError:
			conf[key] = 1.0
	conf["portrait"] = conf["orientation"] == "portrait"
	return conf


def SaveDisplayConfig(conf):
	try:
		f = open(DISPLAY_CONFIG, "w")
		try:
			f.write("ui_scale %.2f\nfont_scale %.2f\norientation %s\ncamera_sensitivity %.2f\nfont %s\n" % (
				_Clamp(conf["ui_scale"], UI_SCALE_MIN, UI_SCALE_MAX),
				_Clamp(conf.get("font_scale", 1.0), FONT_SCALE_MIN, FONT_SCALE_MAX),
				"portrait" if conf["portrait"] else "landscape",
				_Clamp(conf["camera_sensitivity"], CAMERA_MIN, CAMERA_MAX),
				conf.get("font", "default")))
		finally:
			f.close()
	except IOError:
		pass


class _NextFrame(ui.Window):
	"""Runs a callback on the next UI update, outside the event handler that requested it."""

	def __init__(self, func):
		ui.Window.__init__(self)
		self.func = func
		self.Show()

	def OnUpdate(self):
		func, self.func = self.func, None
		self.Hide()
		global _pending
		_pending = None
		if func:
			func()


_pending = None


def _RunNextFrame(func):
	global _pending
	_pending = _NextFrame(func)


def _RebuildGameUI(game, reopenOptions):
	"""Resizes the logical canvas and recreates the game UI in place; the connection,
	world and player state stay as they are and the windows refill from them."""
	import gc
	import interfaceModule, uiTarget
	old = game.interface
	quests = [(btn.index, btn.name) for btn in old.questButtonList]
	if game.mobileHud:
		game.mobileHud.Destroy()
		game.mobileHud = None
	mouseModule.mouseController.DeattachObject()
	oldWindows = [v for v in old.__dict__.values() if isinstance(v, ui.Window)]
	old.HideAllWindows()
	old.Close()
	for wnd in oldWindows:
		wnd.Hide()
	game.interface = None
	old = None
	gc.collect()

	curtain = uiQuest.QuestDialog.__dict__.get("QuestCurtain")
	if curtain:
		curtain.TopBar.Hide()
		curtain.BottomBar.Hide()
		curtain.Hide()
		del uiQuest.QuestDialog.QuestCurtain

	app.ApplyUIScale()
	w, h = wndMgr.GetScreenWidth(), wndMgr.GetScreenHeight()
	game.SetSize(w, h)

	interface = interfaceModule.Interface()
	interface.MakeInterface()
	interface.ShowDefaultWindows()
	game.interface = interface
	for index, name in reversed(quests):
		interface.RecvQuest(index, name)

	if game.targetBoard:
		game.targetBoard.Hide()
		game.targetBoard.Destroy()
	game.targetBoard = uiTarget.TargetBoard()
	game.targetBoard.SetWhisperEvent(ui.__mem_func__(interface.OpenWhisperDialog))
	game.targetBoard.Hide()
	game.console.SetConsoleSize(w, 200)
	game.mobileHud = MobileHud(game)

	game.StartGame()
	game.RefreshStatus()
	game.RefreshQuest()
	if reopenOptions:
		interface.ToggleSystemDialog()
		interface.dlgSystem._SystemDialog__ClickGameOptionButton()
	game.SetFocus()


def OnSurfaceResized():
	"""Called by the engine after the window/surface size settles."""
	if ApplyUIScaleLive():
		return
	import uiscale
	if not uiscale.Relayout():
		app.ApplyUIScale()


def ApplyUIScaleLive():
	"""True when the current phase can be rescaled in place (it is rebuilt next frame)."""
	if not _hud or not _hud.game or not _hud.game.interface:
		return False
	game = _hud.game

	def rebuild():
		try:
			_RebuildGameUI(game, True)
		except Exception:
			import dbg, sys
			dbg.TraceError("live UI rescale failed: %s; restarting" % str(sys.exc_info()[1]))
			app.RestartApplication()
	_RunNextFrame(rebuild)
	return True


class DisplayOption:
	"""Game option rows: UI size (applied in place), camera sensitivity (applied on the next
	drag) and orientation (needs a restart, the activity orientation is fixed at launch)."""
	ROOT = "d:/ymir work/ui/public/"
	ROWS = 4

	def __init__(self, board, y, labelX, dataX, buttonWidth):
		self.conf = LoadDisplayConfig()
		self.appliedScale = self.conf["ui_scale"]
		self.runningPortrait = self.conf["portrait"]
		self.children = []

		self.__Text(board, labelX, y + 2, "UI size")
		self.sizeSlider = self.__Slider(board, dataX, y + 2,
			(self.conf["ui_scale"] - UI_SCALE_MIN) / (UI_SCALE_MAX - UI_SCALE_MIN), self.__OnSlideSize)
		self.sizeLabel = self.__Text(board, self.__ValueX(board, dataX, self.sizeSlider), y + 2, "")

		self.__Text(board, labelX, y + 27, "Camera")
		self.cameraSlider = self.__Slider(board, dataX, y + 27,
			(self.conf["camera_sensitivity"] - CAMERA_MIN) / (CAMERA_MAX - CAMERA_MIN), self.__OnSlideCamera)
		self.cameraLabel = self.__Text(board, self.__ValueX(board, dataX, self.cameraSlider), y + 27, "")

		self.__Text(board, labelX, y + 52, "Screen")
		self.orientButtons = []
		for n, (text, portrait) in enumerate((("Landscape", False), ("Portrait", True))):
			b = self.__Button(board, dataX + buttonWidth * n, y + 50, text, ui.RadioButton())
			b.SetEvent(self.__SelectOrientation, portrait)
			self.orientButtons.append(b)

		self.apply = self.__Button(board, dataX, y + 75, "Apply", ui.Button())
		self.apply.SetEvent(ui.__mem_func__(self.__Apply))
		self.__Refresh()

	def __ValueX(self, board, dataX, slider):
		return min(dataX + slider.GetWidth() + 6, board.GetWidth() - VALUE_TEXT_WIDTH)

	def __Text(self, board, x, y, text):
		t = ui.TextLine()
		t.SetParent(board)
		t.SetPosition(x, y)
		t.SetText(text)
		t.Show()
		self.children.append(t)
		return t

	def __Button(self, board, x, y, text, b):
		b.SetParent(board)
		b.SetUpVisual(self.ROOT + "middle_button_01.sub")
		b.SetOverVisual(self.ROOT + "middle_button_02.sub")
		b.SetDownVisual(self.ROOT + "middle_button_03.sub")
		b.SetPosition(x, y)
		b.SetText(text)
		b.Show()
		self.children.append(b)
		return b

	def __Slider(self, board, x, y, pos, event):
		slider = ui.SliderBar()
		slider.SetParent(board)
		slider.SetPosition(x, y)
		slider.SetSliderPos(_Clamp(pos, 0.0, 1.0))
		slider.SetEvent(ui.__mem_func__(event))
		slider.Show()
		self.children.append(slider)
		return slider

	def __OnSlideSize(self):
		pos = _Clamp(self.sizeSlider.GetSliderPos(), 0.0, 1.0)
		self.conf["ui_scale"] = round(UI_SCALE_MIN + pos * (UI_SCALE_MAX - UI_SCALE_MIN), 2)
		self.__Refresh()

	def __OnSlideCamera(self):
		pos = _Clamp(self.cameraSlider.GetSliderPos(), 0.0, 1.0)
		self.conf["camera_sensitivity"] = round(CAMERA_MIN + pos * (CAMERA_MAX - CAMERA_MIN), 2)
		SaveDisplayConfig(self.conf)
		self.__Refresh()

	def __SelectOrientation(self, portrait):
		self.conf["portrait"] = portrait
		self.__Refresh()

	def __Apply(self):
		SaveDisplayConfig(self.conf)
		if self.conf["portrait"] != self.runningPortrait:
			app.RestartApplication()
			return
		if ApplyUIScaleLive():
			self.appliedScale = self.conf["ui_scale"]
			self.apply.Hide()
		else:
			app.RestartApplication()

	def __Refresh(self):
		self.sizeLabel.SetText("%d%%" % int(self.conf["ui_scale"] * 100 + 0.5))
		self.cameraLabel.SetText("%d%%" % int(self.conf["camera_sensitivity"] * 100 + 0.5))
		on = 1 if self.conf["portrait"] else 0
		for n, b in enumerate(self.orientButtons):
			if n == on:
				b.Down()
			else:
				b.SetUp()
		if self.conf["portrait"] != self.runningPortrait:
			self.apply.SetText("Restart to apply")
			self.apply.Show()
		elif abs(self.conf["ui_scale"] - self.appliedScale) > 0.001:
			self.apply.SetText("Apply")
			self.apply.Show()
		else:
			self.apply.Hide()

	def Destroy(self):
		self.children = []
		self.orientButtons = []
		self.sizeSlider = None
		self.cameraSlider = None
		self.apply = None
		self.sizeLabel = None
		self.cameraLabel = None


class _PlayerCard(ui.Window):
 def __init__(self,parent):
  ui.Window.__init__(self)
  self.SetParent(parent); self.AddFlag("not_pick")
  self.SetPosition(16,16); self.SetSize(238,82)
  self.face=ui.ExpandedImageBox(); self.face.SetParent(self); self.face.AddFlag("not_pick")
  import uicharacter
  self.face.LoadImage(uicharacter.FACE_IMAGE_DICT.get(net.GetMainActorRace(),"icon/face/warrior_m.tga"))
  self.face.SetScale(48.0/self.face.GetWidth(),48.0/self.face.GetHeight()); self.face.SetPosition(7,15); self.face.Show()
  self.faceRace = net.GetMainActorRace()
  self.lines=[]
  for y in (8,28,47,66):
   label=ui.TextLine(); label.SetParent(self); label.AddFlag("not_pick"); label.SetPosition(65,y); label.SetPackedFontColor(modernui.TEXT); label.Show(); self.lines.append(label)
  self.Show()
 def OnUpdate(self):
  race = net.GetMainActorRace()
  if race != self.faceRace:
   import uicharacter
   self.face.LoadImage(uicharacter.FACE_IMAGE_DICT.get(race,"icon/face/warrior_m.tga"))
   self.face.SetScale(48.0/self.face.GetWidth(),48.0/self.face.GetHeight()); self.faceRace = race
  self.lines[0].SetText("%s  |  Lv.%d" % (player.GetName(),player.GetStatus(player.LEVEL)))
  self.lines[1].SetText("HP  %d / %d" % (player.GetStatus(player.HP),player.GetStatus(player.MAX_HP)))
  self.lines[2].SetText("MP  %d / %d" % (player.GetStatus(player.SP),player.GetStatus(player.MAX_SP)))
  self.lines[3].SetText("Energy  %d" % player.GetStatus(player.ENERGY))
 def OnRender(self):
  x,y=self.GetGlobalPosition(); modernui.Card(x,y,238,82,0xe81b1c20,modernui.BORDER,3)
  modernui.Card(x+4,y+12,54,54,0xff111318,modernui.ACCENT,3)
  for yy,current,maximum,color in ((43,player.HP,player.MAX_HP,0xffaf3441),(62,player.SP,player.MAX_SP,0xff3d77ad)):
   modernui.Bar(x+65,y+yy,161,3,0xff111318)
   modernui.Bar(x+65,y+yy,161*max(0,min(1,float(player.GetStatus(current))/max(1,player.GetStatus(maximum)))),3,color)


class MobileHud(ui.Window):
	# quick slot index -> keyboard key it mirrors
	SLOTS = ((0, "1"), (1, "2"), (2, "3"), (3, "4"), (4, "F1"), (5, "F2"), (6, "F3"), (7, "F4"))

	def __init__(self, game):
		ui.Window.__init__(self)
		global _hud
		self.game = game
		w, h = wndMgr.GetScreenWidth(), wndMgr.GetScreenHeight()
		self.SetSize(w, h)
		self.AddFlag("not_pick")

		cx, cy = w - 90, h - 98
		self.attack = self.__Disc(ATTACK, self.__Attack, cx - ATTACK / 2, cy - ATTACK / 2)
		self.attack.glyph = "attack"

		self.slots = []
		for n, (index, key) in enumerate(self.SLOTS):
			offsets = ((-105,12),(-91,-47),(-47,-91),(12,-105),(-230,25),(-174,25),(-230,-31),(-174,-31))
			x = cx + offsets[n][0] - SLOT / 2
			y = cy + offsets[n][1] - SLOT / 2
			d = self.__Disc(SLOT, self.__UseSlot(index), x, y)
			# Touch controls keep only item artwork; no desktop F-key captions.
			self.slots.append(d)

		top = h - 270
		self.pickup = self.__Disc(SMALL, player.PickCloseItem, w - SMALL - 27, top - SMALL)
		self.pickup.glyph = "pickup"
		self.menuButton = self.__Disc(SMALL, self.__ToggleWheel, w - SMALL - 27, top - 2 * SMALL - 12)
		self.menuButton.glyph = "menu"

		self.wheel = _Wheel(self.__WheelEntries())
		self.status = _PlayerCard(self)
		self.nextRefresh = 0.0
		self.taskBarWidth = None
		self.noticeBlocked = None
		_hud = self
		self.ApplyMode()

	def __Disc(self, size, onTap, x, y, onPress = None):
		d = _Disc(size, onTap, onPress)
		d.SetParent(self)
		d.SetPosition(x, y)
		return d

	# one swing per tap; tapping a monster is what keeps attacking it
	def __Attack(self):
		player.AttackOnce()

	def __UseSlot(self, index):
		if app.IsRTL():
			index = 3 - index if index < 4 else 11 - index
		def use():
			if mouseModule.mouseController.isAttached():
				self.game.interface.wndTaskBar.AddQuickSlot(index)
			else:
				player.RequestUseLocalQuickSlot(index)
		return use

	def __ToggleWheel(self):
		self.wheel.Toggle()

	def __ToggleNames(self):
		if self.game.ShowNameFlag:
			self.game.HideName()
		else:
			self.game.ShowName()

	def __WheelEntries(self):
		i = self.game.interface
		return (
			("Bag", T + "inventory_button_01.sub", FRAMED, i.ToggleInventoryWindow),
			("Character", T + "character_button_01.sub", FRAMED, i.ToggleCharacterWindowStatusPage),
			("Skills", T + "mouse_button_skill_01.sub", FRAMED, lambda: i.ToggleCharacterWindow("SKILL")),
			("Quests", "d:/ymir work/ui/game/quest/questicon/level_05.sub", 0.0, lambda: i.ToggleCharacterWindow("QUEST")),
			("Emotes", "d:/ymir work/ui/game/windows/emotion_clap.sub", 0.0, lambda: i.ToggleCharacterWindow("EMOTICON")),
			("Map", T + "m.sub", FRAMED, i.PressMKey),
			("Chat log", T + "open_chat_log_button_01.sub", FRAMED, i.ToggleChatLogWindow),
			("Friends", T + "community_button_01.sub", FRAMED, i.ToggleMessenger),
			("Names", T + "g.sub", FRAMED, self.__ToggleNames),
			("Ride", T + "mouse_button_move_and_attack_01.sub", FRAMED, lambda: net.SendChatPacket("/ride")),
			("Settings", T + "system_button_01.sub", FRAMED, i.ToggleSystemDialog),
		)

	def ApplyMode(self):
		mobile = IsMobileMode()
		taskBar = self.game.interface.wndTaskBar
		if taskBar:
			if self.taskBarWidth is None:
				self.taskBarWidth = taskBar.GetWidth()
			for name in DESKTOP_ONLY:
				child = taskBar.GetChild(name)
				if mobile:
					child.Hide()
				else:
					child.Show()
			# the taskbar root would otherwise swallow touches along the whole bottom edge
			exp = taskBar.GetChild("EXP_Gauge_Board")
			(ex, ey) = exp.GetLocalPosition()
			width = ex + exp.GetWidth() if mobile else self.taskBarWidth
			taskBar.SetSize(width, taskBar.GetHeight())
			if mobile and self.game.interface.wndExpandedTaskBar:
				self.game.interface.wndExpandedTaskBar.Hide()
		if mobile: taskBar.Hide()
		else: taskBar.Show()
		# Keep native action callbacks, but place controls outside Android joystick bounds.
		buttons = self.game.interface.wndGameButton.gameButtonDict
		for n, name in enumerate(("STATUS", "SKILL", "HELP", "QUEST", "BUILD", "EXIT_OBSERVER")):
			button = buttons[name]
			button.SetPosition(220, wndMgr.GetScreenHeight() - 100) if name == "STATUS" else button.SetPosition(252 + n * 76, 22)
			button.SetSize(42, 42)
		self.game.interface.ShowAllQuestButton()
		player.SetAttackKeyState(False)
		if mobile:
			self.Show()
		else:
			self.wheel.Hide()
			self.Hide()

	def __SlotIcon(self, index):
		(kind, pos) = player.GetLocalQuickSlot(index)
		if kind == player.SLOT_TYPE_INVENTORY:
			vnum = player.GetItemIndex(pos)
			if not vnum:
				return None, 0.0, False
			item.SelectItem(vnum)
			return item.GetIconImageFileName(), 0.0, False
		if kind == player.SLOT_TYPE_SKILL:
			skillIndex = player.GetSkillIndex(pos)
			if not skillIndex:
				return None, 0.0, False
			cool = 0.0
			if player.IsSkillCoolTime(pos):
				(total, elapsed) = player.GetSkillCoolTime(pos)
				if total > 0:
					cool = max(0.0, 1.0 - elapsed / total)
			return skill.GetIconName(skillIndex, player.GetSkillGrade(pos)), cool, player.IsSkillActive(pos)
		if kind == player.SLOT_TYPE_EMOTION:
			return emotion.ICON_DICT.get(pos), 0.0, False
		return None, 0.0, False

	def OnUpdate(self):
		now = app.GetTime()
		if now < self.nextRefresh:
			return
		self.nextRefresh = now + REFRESH_SEC
		i = self.game.interface
		i.wndTaskBar.Hide()
		if i.wndEnergyBar:
			i.wndEnergyBar.Hide()
			i.wndEnergyBar.tooltipEnergy.Hide()
		for tip in (i.wndTaskBar.tooltipHP,i.wndTaskBar.tooltipSP,i.wndTaskBar.tooltipST,i.wndTaskBar.tooltipEXP): tip.Hide()
		blocked = i.wndCharacter.IsShow() or i.wndInventory.IsShow() or bool(i.wndQuestWindow)
		if blocked != self.noticeBlocked:
			self.noticeBlocked = blocked
			if blocked:
				i.HideAllQuestButton()
			else:
				i.ShowAllQuestButton()
		for d, (index, key) in zip(self.slots, self.SLOTS):
			icon, cool, active = self.__SlotIcon(index)
			d.SetIcon(icon, 0.65)
			d.base.SetAlpha(1.0 if icon else 0.52)
			if d.label:
				d.label.text.SetPackedFontColor(LABEL_COLOR if icon else 0xff9a8b70)
			d.SetCoolDown(cool)
			d.SetActive(active)

	def Destroy(self):
		global _hud
		if _hud is self:
			_hud = None
		player.SetAttackKeyState(False)
		self.wheel.Hide()
		self.wheel = None
		self.slots = []
		self.Hide()
