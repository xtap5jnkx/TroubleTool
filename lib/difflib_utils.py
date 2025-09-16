import difflib
from typing import List, Dict

# diff = tuple(difflib.ndiff(a, b)) # if not cast to list, need to recompute because diff is an iterator

# removed = [line[2:] for line in diff if line.startswith("- ")]
# added = [line[2:] for line in diff if line.startswith("+ ")]

# print("Removed:", removed)
# print("Added:", added)


# need remove empty lines in lua files to make it work
def summarize_diff(a: List[str], b: List[str]) -> List[Dict[str, str]]:
    """
    Compares two lists of strings and generates a structured list of differences.

    This function uses difflib.SequenceMatcher to find and categorize the
    differences between two sequences of strings (lines of text).

    Args:
        a: A list of strings representing the original text.
        b: A list of strings representing the new text.

    Returns:
        A list of dictionaries, where each dictionary represents a change
        and has a 'type' key ('delete', or 'replace').
    """
    result = []
    matcher = difflib.SequenceMatcher(None, a, b)
    prev_context = ""

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # if tag == "equal":
        #     if i2 > i1:
        #         prev_context = a[i2 - 1]

        if tag == "delete":
            old_block = "".join(a[i1:i2])
            result.append({
                "type": "delete",
                "old": old_block,
            })
            # result.append(f'removed """{old_block}"""')

        elif tag == "insert":
            prev_context = a[i2 - 1]
            next_context = "".join(b[j2:j2+1]).rstrip()
            old_block = prev_context + next_context
            new_block = prev_context + "".join(b[j1:j2]) + next_context

            result.append({
                "type": "replace",
                "old": old_block,
                "new": new_block,
            })
            # result.append(f'insert, replace "{old_block}" with "{new_block}"')

        elif tag == "replace":
            # old_lines = [line.rstrip("\n") for line in a[i1:i2]]
            # new_lines = [line.rstrip("\n") for line in b[j1:j2]]

            # old_block = "\n".join(old_lines)
            # new_block = "\n".join(new_lines)

            old_block = "".join(a[i1:i2]).rstrip()
            new_block = "".join(b[j1:j2]).rstrip()

            result.append({
                "type": "replace",
                "old": old_block,
                "new": new_block,
            })
            # result.append(f'replaced:\nr"""{old_block}"""\nwith:\nr"""{new_block}"""')

            # old_block = "\n".join(f'"{ol}"' for ol in old_lines)
            # new_block = "\n".join(f'"{nl}"' for nl in new_lines)
            # result.append(f"replaced:\n{old_block}\nwith:\n{new_block}")

    return result


if __name__ == "__main__":

    with open("a.lua", "r", encoding="utf-8") as f:
        a = f.readlines()

    with open("b.lua", "r", encoding="utf-8") as f:
        b = f.readlines()

    # print(repr("\n".join(summarize_diff(a, b))))
    # print("\n".join(summarize_diff(a, b)))

    diff = summarize_diff(a, b)

    for d in diff:
        print("###")
        print(d)
        print("###")
        for k, v in d.items():
            print(k, v)
