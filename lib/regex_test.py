import regex


lua_block_pattern = regex.compile(r"""(?isx)
(?P<block>
    # Group 1: Blocks with 'do', like for/while loops
    (?: \b (?:for|while) \b [^;]*? \b do \b
        (?: (?!\b(?:function|if|for|while|do|repeat|end|until|then)\b). | (?&block) )*?
        \b end \b
    )
    | # --- OR ---
    # Group 2: If/then blocks (can contain else/elseif)
    (?: \b if \b [^;]*? \b then \b
        (?: (?!\b(?:function|if|for|while|do|repeat|end|until|then)\b). | (?&block) )*?
        \b end \b
    )
    | # --- OR ---
    # Group 3: Simple blocks like function/do
    (?: \b (?:function|do) \b
        (?: (?!\b(?:function|if|for|while|do|repeat|end|until|then)\b). | (?&block) )*?
        \b end \b
    )
    | # --- OR ---
    # Group 4: Repeat/until blocks
    (?: \b repeat \b
        (?: (?!\b(?:function|if|for|while|do|repeat|end|until|then)\b). | (?&block) )*?
        \b until \b
    )
)""")
# This pattern uses the same robust block matching logic internally
# to parse complex multi-variable assignments.

multivar_pattern = regex.compile(r"""(?isxm)
(?(DEFINE)
    # Recursive pattern for a complete Lua code block, using the robust logic above.
    (?<block>
        (?: \b (?:for|while) \b [^;]*? \b do \b (?:(?!\b(?:function|if|for|while|do|repeat|end|until|then)\b).|(?&block))*? \b end \b)
        |
        (?: \b if \b [^;]*? \b then \b (?:(?!\b(?:function|if|for|while|do|repeat|end|until|then)\b).|(?&block))*? \b end \b)
        |
        (?: \b (?:function|do) \b (?:(?!\b(?:function|if|for|while|do|repeat|end|until|then)\b).|(?&block))*? \b end \b)
        |
        (?: \b repeat \b (?:(?!\b(?:function|if|for|while|do|repeat|end|until|then)\b).|(?&block))*? \b until \b)
    )
    # Recursive pattern for a table constructor.
    (?<table> \{ (?: [^{}] | (?&table) )* \} )
    # A single value in an assignment list (now with greedy matching for expressions).
    (?<value> \s* (?: (?&block) | (?&table) | [^,]+ ) \s* )
)

# Main pattern to find 'local var1, var2 = val1, val2' at the start of a line.
^ \s* \blocal \s+
# Capture variable names.
(?P<vars> [\w\s,]+? ) \s* = \s*
# Capture the list of values.
(?P<vals> (?&value) (?: , (?&value) )* )
""")
# A more comprehensive test case
lua_code = """
local a, c, d = 2e-2, { k = "v" }, function () if true then print('ok') end end
eo = leo;

function complex_function(t)
  for k, v in pairs(t) do
    if v > 10 then
      repeat
        v = v - 1
      until v <= 10
    end
  end
  local abilityObjectMapFunc = function (ability)
    for _, curAbility in ipairs(pcInfo.Object.Ability) do
      if curAbility.name == ability.name then
        return curAbility;
      end
    end
    return ability;
  end
  return ability;
end
"""


def extract_nested_tags(xml_string: str, tag_name: str) -> list[str]:
    """
    Extracts all occurrences of a specified tag, allowing for nesting,
    including the tag itself.

    Args:
        xml_string (str): The XML/HTML string.
        tag_name (str): The name of the tag to match (e.g., "div", "p").

    Returns:
        list[str]: A list of strings, each being a full matched tag with its content.
    """
    # Pattern explanation:
    # <{tag_name}> : Matches the opening tag.
    # (             : Starts a capturing group for the content.
    #   (?:         : Non-capturing group for alternatives:
    #     [^<]* : Any character that is not '<', zero or more times.
    #     |         : OR
    #     (?R)      : Recursively matches the entire pattern (a nested tag).
    #   )* : Repeat the non-capturing group zero or more times.
    # )             : Ends the content capturing group.
    # </{tag_name}> : Matches the closing tag.
    #
    # The `(?R)` is crucial here to allow the pattern to match itself, enabling nesting.
    # This will capture the full tag, including its start and end markers.

    # Ensure tag_name is properly escaped if it could contain regex special chars, though unlikely for tag names.
    escaped_tag_name: str = regex.escape(tag_name)
    tag_pattern: str = rf"<{escaped_tag_name}>( (?: [^<]* | (?R) )* )</{escaped_tag_name}>"
    compiled_regex = regex.compile(tag_pattern, regex.VERBOSE)

    # findall with a capturing group will return the content of the group.
    # If we want the *entire* match (including tags), we don't put ( ) around the whole thing,
    # or access group(0) in finditer.
    # Let's adjust to return the *entire* matched tag, including outer tags.
    full_tag_pattern: str = rf"<{escaped_tag_name}>(?:[^<]*|(?R))*</{escaped_tag_name}>"
    compiled_full_regex = regex.compile(full_tag_pattern, regex.VERBOSE)

    matched_tags: list[str] = compiled_full_regex.findall(xml_string)
    return matched_tags
html_example: str = """
<body>
    <div>
        <p>This is paragraph 1.</p>
        <div>
            <span>Nested span.</span>
            <p>Paragraph 2 within div.</p>
        </div>
        <p>Paragraph 3.</p>
    </div>
    <span>Another span.</span>
</body>
"""
block_pattern = regex.compile(
    r"""(?isx)
    (?P<block>
        # Block openers
        \b(?:function|if|for|while|repeat|do)\b
        .*?
        # Handle nested blocks recursively
        (?:
            (?&block)
            .*?
        )*?
        # Block closers
        \b(?:end|until)\b
    )
    """,
    regex.VERBOSE | regex.DOTALL
)
div_tags: list[str] = extract_nested_tags(html_example, "div")
def main():
    # print(div_tags)

    print("--- Testing multivar_pattern ---")
    for match in multivar_pattern.finditer(lua_code):
        print("\nMatched local assignment:")
        print(f"  Whole match: {match.group(0)}")
        print(f"  Variables:   {match.group('vars')}")
        print(f"  Values:      {match.group('vals')}")

    print("\n\n--- Testing lua_block_pattern ---")
    for match in lua_block_pattern.finditer(lua_code):
        print("\nMatched block:")
        print(match.group(0))


