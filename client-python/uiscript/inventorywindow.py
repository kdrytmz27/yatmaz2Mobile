import uiScriptLocale
import item

EQUIPMENT_START_INDEX = 90

# Paired right-side panels; preserve native 5-column item footprint.
WINDOW_WIDTH = 366
WINDOW_HEIGHT = 380
GRID_X, GRID_Y = 190, 62
GRID_COLUMNS, GRID_ROWS = 5, 9
TAB_X, TAB_Y = 190, 32

window = {
	"name" : "InventoryWindow",

	## 600 - (width + żŔ¸ĄÂĘŔ¸·Î şÎĹÍ ¶çżě±â 24 px)
	"x" : max(8, SCREEN_WIDTH - WINDOW_WIDTH - 26),
	"y" : max(8, (SCREEN_HEIGHT - WINDOW_HEIGHT) / 2),

	"style" : ("movable", "float",),

	"width" : WINDOW_WIDTH,
	"height" : WINDOW_HEIGHT,

	"children" :
	(
		## Inventory, Equipment Slots
		{
			"name" : "board",
			"type" : "board",
			"style" : ("attach",),

			"x" : 0,
			"y" : 0,

			"width" : WINDOW_WIDTH,
			"height" : WINDOW_HEIGHT,

			"children" :
			(
				## Title
				{
					"name" : "TitleBar",
					"type" : "titlebar",
					"style" : ("attach",),

					"x" : 8,
					"y" : 7,

					"width" : WINDOW_WIDTH - 15,
					"color" : "yellow",

					"children" :
					(
						{ "name":"TitleName", "type":"text", "x":(WINDOW_WIDTH - 15) / 2 - 3, "y":3, "text":uiScriptLocale.INVENTORY_TITLE, "text_horizontal_align":"center" },
					),
				},

				## Equipment Slot
				{
					"name" : "Equipment_Base",
					"type" : "image",

					"x" : 10,
					"y" : 33,

					# "image" : "d:/ymir work/ui/equipment_bg_with_ring.tga",
					"image" : "d:/ymir work/ui/equipment_bg_without_ring.tga",

					"children" :
					(

						{
							"name" : "EquipmentSlot",
							"type" : "slot",

							"x" : 3,
							"y" : 3,

							"width" : 150,
							"height" : 182,

							"slot" : (
										{"index":EQUIPMENT_START_INDEX+0, "x":39, "y":37, "width":32, "height":64},
										{"index":EQUIPMENT_START_INDEX+1, "x":39, "y":2, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+2, "x":39, "y":145, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+3, "x":75, "y":67, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+4, "x":3, "y":3, "width":32, "height":96},
										{"index":EQUIPMENT_START_INDEX+5, "x":114, "y":67, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+6, "x":114, "y":35, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+7, "x":2, "y":145, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+8, "x":75, "y":145, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+9, "x":114, "y":2, "width":32, "height":32},
										{"index":EQUIPMENT_START_INDEX+10, "x":75, "y":35, "width":32, "height":32},
										## »ő ąÝÁö1
										# {"index":item.EQUIPMENT_RING1, "x":2, "y":106, "width":32, "height":32},
										## »ő ąÝÁö2
										# {"index":item.EQUIPMENT_RING2, "x":75, "y":106, "width":32, "height":32},
										## »ő ş§Ć®
										{"index":item.EQUIPMENT_BELT, "x":39, "y":106, "width":32, "height":32},
									),
						},
						## Dragon Soul Button
						{
							"name" : "DSSButton",
							"type" : "button",

							"x" : 114,
							"y" : 107,

							"tooltip_text" : uiScriptLocale.TASKBAR_DRAGON_SOUL,

							"default_image" : "d:/ymir work/ui/dragonsoul/dss_inventory_button_01.tga",
							"over_image" : "d:/ymir work/ui/dragonsoul/dss_inventory_button_02.tga",
							"down_image" : "d:/ymir work/ui/dragonsoul/dss_inventory_button_03.tga",
						},
						## MallButton
						{
							"name" : "MallButton",
							"type" : "button",

							"x" : 118,
							"y" : 148,

							"tooltip_text" : uiScriptLocale.MALL_TITLE,

							"default_image" : "d:/ymir work/ui/game/TaskBar/Mall_Button_01.tga",
							"over_image" : "d:/ymir work/ui/game/TaskBar/Mall_Button_02.tga",
							"down_image" : "d:/ymir work/ui/game/TaskBar/Mall_Button_03.tga",
						},
						## CostumeButton
						{
							"name" : "CostumeButton",
							"type" : "button",

							"x" : 78,
							"y" : 5,

							"tooltip_text" : uiScriptLocale.COSTUME_TITLE,

							"default_image" : "d:/ymir work/ui/game/costume_button_01.tga",
							"over_image" : "d:/ymir work/ui/game/costume_button_02.tga",
							"down_image" : "d:/ymir work/ui/game/costume_button_03.tga",
						},						
						{
							"name" : "Equipment_Tab_01",
							"type" : "radio_button",

							"x" : 86,
							"y" : 161,

							"default_image" : "d:/ymir work/ui/game/windows/tab_button_small_01.sub",
							"over_image" : "d:/ymir work/ui/game/windows/tab_button_small_02.sub",
							"down_image" : "d:/ymir work/ui/game/windows/tab_button_small_03.sub",

							"children" :
							(
								{
									"name" : "Equipment_Tab_01_Print",
									"type" : "text",

									"x" : 0,
									"y" : 0,

									"all_align" : "center",

									"text" : "I",
								},
							),
						},
						{
							"name" : "Equipment_Tab_02",
							"type" : "radio_button",

							"x" : 86 + 32,
							"y" : 161,

							"default_image" : "d:/ymir work/ui/game/windows/tab_button_small_01.sub",
							"over_image" : "d:/ymir work/ui/game/windows/tab_button_small_02.sub",
							"down_image" : "d:/ymir work/ui/game/windows/tab_button_small_03.sub",

							"children" :
							(
								{
									"name" : "Equipment_Tab_02_Print",
									"type" : "text",

									"x" : 0,
									"y" : 0,

									"all_align" : "center",

									"text" : "II",
								},
							),
						},

					),
				},

				{
					"name" : "Inventory_Tab_01",
					"type" : "radio_button",

					"x" : TAB_X,
					"y" : TAB_Y,

					"default_image" : "d:/ymir work/ui/game/windows/tab_button_large_01.sub",
					"over_image" : "d:/ymir work/ui/game/windows/tab_button_large_02.sub",
					"down_image" : "d:/ymir work/ui/game/windows/tab_button_large_03.sub",
					"tooltip_text" : uiScriptLocale.INVENTORY_PAGE_BUTTON_TOOLTIP_1,

					"children" :
					(
						{
							"name" : "Inventory_Tab_01_Print",
							"type" : "text",

							"x" : 0,
							"y" : 0,

							"all_align" : "center",

							"text" : "I",
						},
					),
				},
				{
					"name" : "Inventory_Tab_02",
					"type" : "radio_button",

					"x" : TAB_X + 78,
					"y" : TAB_Y,

					"default_image" : "d:/ymir work/ui/game/windows/tab_button_large_01.sub",
					"over_image" : "d:/ymir work/ui/game/windows/tab_button_large_02.sub",
					"down_image" : "d:/ymir work/ui/game/windows/tab_button_large_03.sub",
					"tooltip_text" : uiScriptLocale.INVENTORY_PAGE_BUTTON_TOOLTIP_2,

					"children" :
					(
						{
							"name" : "Inventory_Tab_02_Print",
							"type" : "text",

							"x" : 0,
							"y" : 0,

							"all_align" : "center",

							"text" : "II",
						},
					),
				},

				## Item Slot
				{
					"name" : "ItemSlot",
					"type" : "grid_table",

					"x" : GRID_X,
					"y" : GRID_Y,

					"start_index" : 0,
					"x_count" : GRID_COLUMNS,
					"y_count" : GRID_ROWS,
					"x_step" : 32,
					"y_step" : 32,

					"image" : "d:/ymir work/ui/public/Slot_Base.sub"
				},

				## Print
				{
					"name":"Money_Slot",
					"type":"button",

					"x":8,
					"y":28,

					"horizontal_align":"center",
					"vertical_align":"bottom",

					"default_image" : "d:/ymir work/ui/public/parameter_slot_05.sub",
					"over_image" : "d:/ymir work/ui/public/parameter_slot_05.sub",
					"down_image" : "d:/ymir work/ui/public/parameter_slot_05.sub",

					"children" :
					(
						{
							"name":"Money_Icon",
							"type":"image",

							"x":-18,
							"y":2,

							"image":"d:/ymir work/ui/game/windows/money_icon.sub",
						},

						{
							"name" : "Money",
							"type" : "text",

							"x" : 3,
							"y" : 3,

							"horizontal_align" : "right",
							"text_horizontal_align" : "right",

							"text" : "123456789",
						},
					),
				},

			),
		},
	),
}

# Change presentation only; original named controls keep their callbacks.
def inventory_theme(node):
 name=node.get("name", "")
 if name == "TitleBar": node.update(x=184,y=6,width=176)
 elif name == "TitleName": node.update(x=76,y=3,text="Envanter",text_horizontal_align="center")
 elif name == "Equipment_Base":
  node.update(type="window",x=10,y=38,width=150,height=190)
  node.pop("image",None)
 elif name == "ItemSlot":
  node.update(x_step=32,y_step=32,x_blank=0,y_blank=0)
  node.pop("image",None)
 elif name == "Money_Slot":
  node.update(x=204,y=355)
  node.pop("horizontal_align",None); node.pop("vertical_align",None)
 elif name == "Money_Icon": node.update(x=-15,y=3)
 elif name == "Inventory_Tab_01_Print": node["text"]="1"
 elif name == "Inventory_Tab_02_Print": node["text"]="2"
 for child in node.get("children",()): inventory_theme(child)
inventory_theme(window)
board=window["children"][0]
board["children"] += ({"name":"EquipmentTitleBar","type":"titlebar","style":("attach",),"x":6,"y":6,"width":158,"children":(
 {"name":"EquipmentHeading","type":"text","x":67,"y":3,"text":"Ekipman","text_horizontal_align":"center"},
)},)
