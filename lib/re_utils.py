import re

# LINE_SINGLE_QUOTED_RE = re.compile(r"'(?:\\.|[^'\\\n])*'")
# LINE_DOUBLE_QUOTED_RE = re.compile(r'"(?:\\.|[^"\\\n])*"')
# LONG_BRACKET_STRINGS_RE = re.compile(r"(?s)(?<!--)\[(=*)\[.*?\]\1\]")

# BLOCK_COMMENT_RE = re.compile(r"(?s)(?<!-)--\[(=*)\[.*?\]\1\]")
# LINE_COMMENT_RE = re.compile(r"--[^\n]*")
COMMENT = re.compile(r"""(?xm)
    (?s)^--\[(=*)\[.*?\]\1\] # (?s) only for this branch
    |^--[^\n]*
""")

# BLOCK_START_RE = re.compile(r"\b(function|if|for|while|repeat|do)\b")
# BLOCK_END_RE = re.compile(r"\b(until|end)\b")
# FUNC_DEF_RE = re.compile(r"^function\s+([^(\s]+)\s*(\(|$)")
# FUNC_END_RE = re.compile(r"^(end)\b")

# 2. Split the code into blocks using the starter pattern as a separator.
# The lookahead `(?=...)` splits *before* the starter, and `(?m)` makes `^` work per-line.
DEF = re.compile(r"""(?mx)(?=(?:
    ^(?:local\s+)?function\s+[.\w:]+
    # |^if\s+.+ # there is a file with wrong ident break this, command.lua
    |^(?:local\s+)?[.\w]+\s*=\s*function\b
    |^(?:local\s+)?\w[ \t\w,.\[\]"']+\s*=
))""")

# for extract key value
FUNC_DEF = re.compile(r"^(?:local\s+)?function\s+[.\w:]+")
STARTSWITH_IF = re.compile(r"^if\s+.+")

# local def can't have object, add all to identifier map
LOCAL_DEF = re.compile(r"^local\s+(?:function\s+)?([ \t,\w]+)")
OBJECT_IN_IF = re.compile(r"_G\[['\"]([A-Za-z_]\w*)['\"]\]")

OBJECT_IN_FUNC = re.compile(r"^function\s+(\w+)(?:[.:]\w+)+")
STARTSWITH_FUNC = re.compile(r"^function\b")
# var can't contain ":"
OBJECT_IN_VAR = re.compile(r"^(\w+)(?:[.]\w+)+")

IDENTIFIERS = re.compile(r"\b[a-zA-Z_]\w*\b")

# FUNC_DEF_RE = re.compile(r"""(?x)(?=(?:
#     ^(?:local\s+)?[.\w]+\s*=\s*function\b
#     |^(?:local\s+)?function\s+[.\w:]+
# ))""")
# # FUNC_LOCAL_DEF_RE = re.compile(r"(?ms)^local\s+function\s+(\w+(?:[.:]\w+)*).*?^end\b")
# FUNC_DEF_RE = re.compile(r"(?ms)^(?:local\s+)?function\s+(\w+(?:[.:]\w+)*).*?^end\b")
# # VAR_DEF_LOCAL_RE = re.compile(
# #     r"""(?msx)
# #     ^local\s+(.+?)\s*=(?:(?:\s*function\b.*?^end\b)|(?:[^;]*;))
# #     """
# # )
# VAR_DEF_RE = re.compile(
#     r"(?ms)^(?:local\s+)?(\w.*?)\s*=(?:(?:\s*function\b.*?^end\b)|(?:[^;]*;))"
# )
