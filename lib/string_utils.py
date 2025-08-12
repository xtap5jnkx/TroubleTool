from lib import re_utils


def local_func_search(text):
    return re_utils.FUNC_DEF_RE.search(text)


def normalize_block(block: list[str]):
    # normal block has \n at the end of line but some file has no last line (no \n)
    return block if not block else block[:-1] + [block[-1].rstrip()]


def split_string_to_set(input_string: str, split_str: str):
    return {part.strip() for part in input_string.split(split_str)}


def trim_lines(lines: list[str]):
    non_empty_lines = [line.rstrip() for line in lines if line.rstrip()]
    return "\n".join(non_empty_lines)


def normalize_code_text(raw_code: str):
    lines = raw_code.splitlines()
    return trim_lines(lines)


def strip_def_func(line):
    line = re_utils.FUNC_DEF_RE.sub("", line)
    return line


def strip_normalize_def_func(raw_code: str):
    return normalize_code_text(strip_def_func(raw_code))


def strip_var_def(line):
    # line = re_utils.VAR_DEF_LOCAL_RE.sub("", line)
    line = re_utils.VAR_DEF_RE.sub("", line)
    return line


def strip_normalize_var_def(raw_code: str):
    return normalize_code_text(strip_var_def(raw_code))


def strip_strings_comments(line):
    line = re_utils.LINE_SINGLE_QUOTED_RE.sub("", line)
    line = re_utils.LINE_DOUBLE_QUOTED_RE.sub("", line)
    line = re_utils.LONG_BRACKET_STRINGS_RE.sub("", line)
    line = re_utils.BLOCK_COMMENT_RE.sub("", line)
    line = re_utils.LINE_COMMENT_RE.sub("", line)
    return line


def strip_normalize_code_text(raw_code: str):
    return normalize_code_text(strip_strings_comments(raw_code))
