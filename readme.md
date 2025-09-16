# TROUBLESHOOTER: Abandoned Children – Modding & Tools

Inspired by [K0lb3/TROUBLESHOOTER-mine](https://github.com/K0lb3/TROUBLESHOOTER-mine)

A Python tool for extracting specific game files and managing mods for **TROUBLESHOOTER: Abandoned Children**.

---

## Table of Contents

* [Installation](#installation)
* [Extracting Files](#extracting-files)
* [Mod Manager](#mod-manager)
* [Installing Mods](#installing-mods)
* [Creating Patches](#creating-patches)

---

## Installation

1. **Install Python**. (>= 3.10 because of type hint)
2. Install dependencies:

```bash
pip install lxml cryptography customtkinter
```

* `cryptography` → for decrypting game files
* `customtkinter` → for the UI
* `lxml` → for parsing XML

3. Run the tool:

```bash
python TroubleTool.py
```

---

## Extracting Files

* Extracts specific files (e.g. `CEGUI/datafiles/lua_scripts`, `script`, `stage`, `xml`).
* Extracted files go into `Game_folder/Data`, and their path in the index file is updated to point there.
* Auto index backup before extract.
	* Index backup is only created if no `../Data/` in packs.
	* Index restore is only triggered if `../Data/` in packs.
* **auto-extraction** when install/create patch:
	* If a mod has no `.py` files, the tool auto-extracts required files.
	* If `.py` files exist, use auto-extracts text box.
	* To disable this, clear the auto-extract text box in the Mod UI.

---

## Mod Manager

* Extract mods into the `Mods` folder:

```
Game_folder/Mods/ModName/[xml|script|...]
```

or:

```
Game_folder/Mods/ModName/Data/[xml|script|...]
```

* Open `TroubleTool` → **Mods** → Select & order mods → Install or Create Patch.

---

## Installing Mods

The tool applies mods **in order**. Mods later in the list have higher priority and their changes override earlier ones when conflicts occur.

So lazy to update this, create patch first (convert xml, lua, stage, dkm files to py files) then install.

### File handling:

* **`.xml`** → merges unique elements (identified by first attribute, key in normal case).
* **`.stage`** (XML format) → merge unique elements (identified by attribute name "Key", elements related to "Action" tags are excluded).
* To modify all elements in `.xml` or `.stage` files, create a `.py` patch script and use XPath to select the elements you want to change.
* **`.lua`** → merges/adds top-level function & variable definitions with simple topological sorting for dependencies.
* **`Dictionary`** → merges into `Game_folder/Dictionary`.
* known types: `xml`, `lua`, `stage`, `dic`, `dkm` (XML parse, process if unknown).

### Special behavior:

* **`main.py` in mod** → Tool edits `main.settings.GAME_FOLDER` and runs only that file, and logs show in console.
* **`.py` in mod** → Tool calls its `patch` function.
* **`lua` subfolder in mod** → Support files for `.py` patches (not installed directly).

---

## Creating Patches

* Convert lua, xml, dkm, stage files to python files. Patch files created by the tool are simple by default. You can edit them manually or ask an AI assistant to improve and optimize the code.
* Keep `.zip` backups of mods — patch creation removes old files.
* Patches contain only changes, converting `.xml`, `.lua`, `.dkm`, `.stage` to `.py`. `.dic` → strips unchanged lines.
* If the tool generates very long patch code, you can use AI assistants (e.g., ChatGPT, Bard) to help shorten or simplify it while keeping the same functionality.

Example — **changing all item prices in `xml/Shop.xml`**:

```python
# Game_folder/Mods/ModName/change_shop_price.py
def patch(game_files):
	xml = game_files.xml("xml/Shop.xml") # relative path, e.g. "Dictionary/keymap.dkm", "stage/PvPTest.stage"

	for element in xml.root.xpath("//property[number(@Price)>1]"):
		element.set("Price", "1")

		# current_price = float(element.get("Price"))  # or int(), if always integer
		# new_price = current_price * 99
		# element.set("Price", str(int(new_price)))  # cast back to string for XML
```

---

### Lua Patch

* For `.lua` files, the patch generator will only produce either `add_definition` (new function/variable), `delete_code` or `replace_code`. `add_definition` add the definition if it doesn’t exist, otherwise they replace it.
* But for large Lua definitions, it’s often better to **replace only specific code blocks** or **insert new code**, rather than replacing the entire definition:

**Replace code:**

```python
def patch(game_files):
	# or lua = game_files.lua("script/server/ability.lua")
	script = game_files.script("script/server/ability.lua")

	script.replace_code(
		def_name = "function AbilityUseableCheck_Tame",
		old_code = """if target and not IsDead(target) then
			return 'Hide';""",
		new_code = """if target and not IsDead(target) then
			return; -- rex mod""",
		# from_file = "test", # use code from lua/test.lua
		count = 1 # replace only first found, -1: default, replace all found
	)
```

**`def_name` can be:**

* `local function funcName`
* `function funcName`
* `local varName`
* `varName`

**these forms are treated differently by the tool**

* The tool matches definitions **exactly** as they appear in the Lua source.
* If you specify `function MyFunc`, it will **not** match `local function MyFunc` (and vice versa).

* Use triple quotes (`"""..."""`) for multi-line code blocks.
* Preserve **tab characters** for indentation — the tool relies on exact formatting to locate code.
* If your editor uses spaces, convert them to tabs (`Indentation: Convert to tabs`) before saving, or the tool may fail to find the target code.

* For code with `\n` or special chars, prefix with `r` → `r"""..."""`.

```python
def patch(game_files):
	# 'lua' and 'script' are equivalent — both handle Lua script files
	lua = game_files.lua("CEGUI/datafiles/lua_scripts/client_Chat.lua")

	lua.replace_code(
		def_name = "function ChatTextKeyDown",
		old_code = r"YesNoDialog('시스템 공지 전송', '아래 내용으로 시스템 공지를 전송합니다. \n\\['..miribogi..'\\]\n전송합니까?', function()",
		new_code = r"YesNoDialog('시스템 공지 전송', '아래 내용으로 시스템 공지를 전송합니다. \n\\['..miribogi..'\\]\n전송합니까?', function()",
		# from_file = "test", # or use code from lua/test.lua
		count = 1
	)
```

---

**Insert code from a Lua file:**

```python
def add_ap_on_robbery(game_files):
	# Editing the description
	xml = game_files.xml("xml/Mastery.xml")
	element = xml.root.find("idspace[@id='Mastery']/class[@name='EvilRobber']/Desc_Base")
	description = '\nNOSTRO MOD: Gain 1 Action Point upon successful stealing.'

	element.append(xml.ET.fromstring(f"""<property CaseColor="Blue_ON" CaseType="None" CaseValueType="string" CaseValue="" CaseLineBreak="false" LineBreak="false" Text="{description}"/>"""))

	# # or:
	# prop = xml.ET.Element("property", {
	# 	"CaseColor": "Blue_ON",
	# 	"CaseType": "None",
	# 	"CaseValueType": "string",
	# 	"CaseValue": "",
	# 	"CaseLineBreak": "false",
	# 	"LineBreak": "false",
	# 	"Text": description
	# })
	# element.append(prop)


	# Editing scripts
	script = game_files.script("script/server/mastery_AbilityUsed_events.lua")
	script.insert_code(
		def_name = "function Mastery_Rob_AbilityUsed",
		target = "InsertBuffActions(actions, owner, owner, mastery.Buff.name, 1, true);",
		# code = r"""...""",
		from_file = "ViciousRobber",
		position = "after", # or "before"
		count = 1
	)

def patch(game_files):
	add_ap_on_robbery(game_files)
```

- `Game_folder/Mods/ModName/lua/ViciousRobber.lua`
```lua
	-- Nostro mod
	if mastery_EvilRobber then
		AddActionRestoreActions(actions, owner);
	end
```

---

**Remove code**

```python
def patch(game_files):
	script = game_files.script("script/server/Unit.lua")

	script.delete_code(
		def_name="function GetUnitChallengerMasteries",
		old_code=r"""				tryCount = tryCount + 1;
""",
		count=1
	)
```

or:

```python
def patch(game_files):
	foo = game_files.script("script/foo.lua")

	foo.replace_code(
		def_name = "function foo",
		old_code = """print("hello world");""",
		new_code = "",
		count = 1
	)
```

---

```python
def patch(game_files):
	foo = game_files.script("script/foo.lua")

	foo.add_definition("function foo", """function foo(x, y)
	return x + y;
end""")
```

---

## Credits

Thanks to **K0lb3**, **NostroTS**, **TSRexEviL**, **Malediction9** for inspiration.
