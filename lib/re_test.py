import re

from lib import re_utils
from lib.utils import Utils

# total 21, 11 funcs, 10 vars
lua_code = """
local function GetAbilityRangeRadiusText(ability)
  result = result..'$ColorEnd$';
end
--[[
    This is block comment.
    So, it can go on...
    and on...
    and on....
]]
local default_fcompval = function( value, index ) return value end
---@class ActionFactory
---@field protected actions table[]
---@field protected ds DirectingScripter
---@field protected RefId number
---@field protected RefOffset number
ActionFactory = {};
ActionFactory.__index = ActionFactory;
---@param ds DirectingScripter
---@return ActionFactory
function ActionFactory.new(ds)
	local ret = {actions = {}, ds = ds, RefId = nil, RefOffset = nil};
	setmetatable(ret, ActionFactory);
	return ret;
end
---@param giver unit
---@param obj unit
---@param buffName string
---@param buffLevel number
---@param modifier? fun(buff:class_Buff)
---@param isAbilityBuff? boolean
---@param invoker? any
---@param isDead? boolean
function ActionFactory:InsertBuff(giver, obj, buffName, buffLevel, modifier, isAbilityBuff, invoker, isDead)
	InsertBuffActions(self.actions, giver, obj, buffName, buffLevel, true, modifier, isAbilityBuff, invoker, isDead);
end
neo.default_fcompval = function( value, index ) return value end
local c['a'] = a["a"];
c["a"] = a["a"];
--[==[
    This is also a block comment
    We can include "]=]" inside this comment
--]==]
vtest, let,     boo = 1e-10, oto.et, true;
local b.a = c[1], d.b;
b.a = c[1], d.b;
---[[
    print'Lua is lovely. print'
--]]
local fcompf = function( a,b ) if a < b then return 1; end end
fcompf = function( a,b ) if a < b then return 1; end end
local a.a = 1;
---[[
  print 'Lua is love. execute'
--[=[]]
  print 'Lua is life. comment'
--]=]
local g_priorMasteriesByBuff = {
	Luck = { 'LastStand', 'Module_ESPArmor', 'CalculatedRisk', 'HeavyMoltAfterDeath' },
};
local AppendMessage = function(fullMessage, addMessage)
  if fullMessage == '' then
    return addMessage;
  else
    return fullMessage..' '..addMessage;
  end
end--local c=1;
local g_abilityBuffKeyList = { 'ApplyTargetBuff', 'ApplyTargetSubBuff', 'ApplyTargetThirdBuff', 'CancelTargetBuff', 'RemoveBuff' };
local AddMessageRemover = function(b) b.UseAddedMessage = false; end;
function GetAbilityRangeRadiusText:new  (ability)
  return result;
end
--[[
  print 'Lua is love. comment'
--[=[]]
  print 'execute'
--]=]
function GetAbilityRangeRadiusText(ability)
  local result = '$White$'..ability.RangeRadius;
  result = result..'$ColorEnd$';
  return result;
end
o.pri = function(self) return b; end
function o:greet()
    print("call from o:greet: Hello, " .. self.name)
end
function alem() print(o.a, next()); end
o.a, obj.name = 8, "bla"
o.__index = o
function obj:greet()
    print("call from obj:greet: Hello, " .. self.name)
    p = o:new("neo")
    p:greet()
    print(obj.name, var2)
    print(next())
end
local obj = {}
o = { name="abc"}
local function next() return o:greet(), var1; end
local bao = 1;
function o:new(name)
    local instance = setmetatable({}, o)
    instance.name = name
    return instance
end
function Command_goray(company, dc)
if tostring(SafeIndex(company, unpack(string.split('MissionCleared/Tutorial_PugoShopAfter', '/')))) ~= 'true' then
    dc:UpdateCompanyProperty(company, 'MissionCleared/Tutorial_PugoShopAfter', 'true');
end
end
local var1, var2, var3 = 8, 9, 10
function BuffHelper.IsRelation(from, to, relation)
    local realRelation = GetRelation(from, to)
    return BuffHelper.IsRelationMatched(realRelation, relation);alem
end
if _G['BuffHelper'] == nil then
    _G['BuffHelper'] = {}
end
function BuffHelper.ForEachObjectInRange(obj, rangeType, pos, doFunc)
    local targetRange = BuffHelper.CalculateRangeAroundObject(obj, rangeType, pos);
    local targetObjects = BuffHelper.GetObjectsInRange(GetMission(obj), targetRange);

    for _, target in ipairs(targetObjects) do
        doFunc(target);
    end
end
"""


def main():
    # show_definitions()
    # return
    blocks = re_utils.DEF.split(lua_code)

    # Parse each block and add it to the dictionary.
    definitions = {}
    for block in blocks:
        clean_block = block.strip()
        if not clean_block:
            continue

        # Handle `function name(...) ... end`
        func_match = re_utils.FUNC_DEF.match(clean_block)
        if func_match:
            definitions[func_match.group(0)] = clean_block
            # # Extract the function name as the key
            # name_match = re.search(r"function\s+([\w.:]+)", clean_block)
            # if name_match:
            #     key = name_match.group(1).strip()
            #     # The value is the rest of the definition (parameters and body)
            #     header_match = re.match(r"function\s+[\w.:]+\s*", clean_block)
            #     if not header_match:
            #         raise ValueError(
            #             f"Failed to extract header for block: {clean_block}"
            #         )
            #     value = clean_block[header_match.end() :].strip()
            #     definitions[key] = value
        # Handle assignment-based definitions (e.g., `a = b`, `local x = y`)
        elif "=" in clean_block:
            key, _ = clean_block.split("=", 1)
            # key, value = clean_block.split("=", 1)
            # definitions[key.rstrip()] = value.lstrip()
            definitions[key.rstrip()] = clean_block
    for key, value in definitions.items():
        print("-" * 20)
        print(f"key: {key}")
        print(f"value: {value}")


@Utils.log_time("show_definitions")
def show_definitions():
    blocks = re_utils.COMMENT.sub("", lua_code)
    blocks = re_utils.DEF.split(blocks)

    # 3. The first item from split is often empty/whitespace, so we filter it out.
    matches = [b for b in blocks if b.strip()]

    functions = []
    variables = []

    # 4. Classify each match as a function or variable. This part remains the same.
    for match in matches:
        if re.search(r"=\s*function|\bfunction\b", match):
            functions.append(match.strip())
        else:
            variables.append(match.strip())

    # 5. Print the separated results.
    print("--- Functions ---")
    for func in functions:
        print(func)
        print("-" * 20)

    print("\n--- Variables ---")
    for var in variables:
        print(var)
        print("-" * 20)
    print(f"Total {len(functions)} functions, {len(variables)} variables")
