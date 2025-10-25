import os
from typing import Optional
from xml.sax.saxutils import quoteattr

from lxml import etree as et

from lib.utils import Utils

Element = et._Element
ElementTree = et._ElementTree
Comment = et._Comment

STAGE_KEYS = {"ActionKey", "Key", "ObjectKey", "Name"}
STAGE_KEYS2 = {"Group"}
parser = et.XMLParser(collect_ids=False, remove_comments=True)


class XmlUtils:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._tree: Optional[ElementTree] = None
        self._root: Optional[Element] = None
        self._base_str: Optional[bytes] = None
        self._changes: list[dict] = []
        self._change_index: dict = {}
        self.is_create_patch: Optional[bool] = None
        self.et = self.ET = et
        self.read()

    @property
    def tree(self) -> ElementTree:
        if self._tree is None:
            raise ValueError("XML tree not initialized or empty")
        return self._tree

    @tree.setter
    def tree(self, value: ElementTree):
        self._tree = value

    @property
    def root(self) -> Element:
        if self._root is None:
            raise ValueError("XML root not initialized or empty")
        return self._root

    @root.setter
    def root(self, value: Element):
        self._root = value

    def read(self):
        self._tree = et.parse(self.file_path, parser=parser)
        self._root = self._tree.getroot()
        self._base_str = et.tostring(self._root, encoding="utf-8")

    def writeto(self, fileout: str):
        if self._base_str == et.tostring(self.root, encoding="utf-8"):
            return False

        et.indent(self.root, space="\t")
        self.tree.write(fileout, encoding="utf-8", xml_declaration=True)
        return True

    def _clear_changes(self):
        self._changes.clear()
        self._change_index.clear()

    def create_patch(self, fileout: str, relative_path: str):
        if not self._changes:
            return 2
        rel_path = relative_path.replace("\\", "/")
        change_blocks = [
            f'def patch(game_files):\n\txml = game_files.xml("{rel_path}")\n'
        ]

        for change in self._changes:
            xpath = change["xpath"]
            if xpath:
                target = f"\n\ttarget = xml.root.xpath({quoteattr(xpath)})[0]\n"
            else:
                target = "\n\ttarget = xml.root\n"
            change_blocks.append(target)

            if change["type"] == "new":
                elements: list[Element] = change["element"]
                if len(elements) > 1:
                    root = et.Element("root")
                    root.extend(elements)
                    et.indent(root, space="\t")
                    xml_str = et.tostring(root, encoding="unicode")
                    change_blocks.append(f'''\telements = xml.ET.fromstring("""{xml_str}""")
\ttarget.extend(elements)\n''')
                else:
                    xml_str = et.tostring(elements[0], encoding="unicode").strip()
                    change_blocks.append(
                        f'\ttarget.append(xml.ET.fromstring("""{xml_str}"""))\n'
                    )

            elif change["type"] == "update":
                attr_map = [
                    f'\ttarget.set("{k}", {quoteattr(v)})\n'
                    # f'\ttarget.attrib["{k}"] = {quoteattr(v)}\n'
                    for k, v in change["diff"].items()
                ]
                change_blocks.extend(attr_map)

        content = "".join(change_blocks)

        if not Utils.should_write(content, fileout):
            self._clear_changes()
            return 3

        with open(fileout, "wb") as f:
            f.write(content.encode("utf-8"))
        self._clear_changes()
        return 1

    def _get_element_identifier(self, element: Element, ext: str):
        """
        Generates a unique identifier for an element.
        Return (tag, name, value); otherwise, (tag, None, None).
        """
        if ext == ".stage":
            # ignore Condition tags + Action tags without ActionKey
            if element.tag == "Condition" or (element.tag == "Action" and not element.attrib.get("ActionKey")):
                return (element.tag, None, None)

            matching_attributes = []
            matching_attributes2 = []

            for name, value in element.attrib.items():
                if name in STAGE_KEYS:
                    matching_attributes.append((name, value))
                elif name in STAGE_KEYS2:
                    matching_attributes2.append((name, value))

            if matching_attributes:
                return (element.tag, *matching_attributes, *matching_attributes2)

            return (element.tag, None, None)

        n, v = next(iter(element.attrib.items()), (None, None))
        return (element.tag, n, v)

    # def _build_xpath(self, path: list[Element], current: Element | None = None):
    def _build_xpath(self, path: list[Element], ext: str):
        # elements = path if current is None else path + [current]
        segments = []
        for ele in path:
            tag = ele.tag
            ele_id = self._get_element_identifier(ele, ext)

            # Check if multiple key-value pairs are returned
            if isinstance(ele_id[1], tuple):
                segment = tag
                for name, value in ele_id[1:]:
                    if '"' in value:
                        segment += f"[@{name}='{value}']"
                    else:
                        segment += f'[@{name}="{value}"]'
                segments.append(segment)
            elif ele_id[1]:
                t, n, v = ele_id
                if '"' in v:
                    segments.append(f"{tag}[@{n}='{v}']")
                else:
                    segments.append(f'{tag}[@{n}="{v}"]')
            else:
                segments.append(tag)
        return "/".join(segments)  # no "/" + because it point at root
        # "/" + for search from root, "//" + for search from everywhere

    def _add_comment_if_needed(
        self,
        parent: Element,
        comment_text: str,
        *,
        before: Element | None = None,
    ):
        if before is not None:
            index = parent.index(before)
            if index > 0:
                prev = parent[index - 1]
                if (
                    isinstance(prev, Comment)
                    and prev.text
                    and prev.text.strip() == comment_text
                ):
                    return  # Already has the comment
            parent.insert(index, et.Comment(f" {comment_text} "))
            return

        # len(parent) > 0: Make sure parent has at least one child element.
        # parent[-1]: Gets the last child of parent.
        if len(parent) > 0 and isinstance(parent[-1], Comment):
            if parent[-1].text and parent[-1].text.strip() == comment_text:
                return False
        parent.append(et.Comment(f" {comment_text} "))

    def _handle_new_element(
        self, parent: Element, new_element: Element, path_to_parent: list[Element], ext: str
    ):
        if self.is_create_patch is None:
            parent.append(new_element)
            return

        xpath_to_parent = self._build_xpath(path_to_parent, ext)
        key = (xpath_to_parent, "new")

        # Coalesce new elements under the same parent
        change = self._change_index.get(key)
        if change:
            change["element"].append(new_element)
        else:
            change = {
                "xpath": xpath_to_parent,
                "type": "new",
                "element": [new_element],
            }
            self._changes.append(change)
            self._change_index[key] = change

    def _handle_updated_attributes(
        self, target: Element, source: Element, path_to_target: list[Element], ext
    ):
        if self.is_create_patch is None:
            target.attrib.update(source.attrib)
            return

        diff = {k: v for k, v in source.attrib.items() if target.attrib.get(k) != v}

        if diff:
            self._changes.append(
                {
                    "xpath": self._build_xpath(path_to_target, ext),
                    "type": "update",
                    "diff": diff,
                }
            )

    def _merge_elements(
        self, target_root: Element, source_root: Element, base_path: list[Element], ext: str
    ):
        stack = [
            (target_root, source_root, list(base_path))
        ]  # stack holds tuples of (target, source, path)

        while stack:
            tgt_ele, src_ele, path = stack.pop()

            tgt_children_index = {
                self._get_element_identifier(child, ext): child
                for child in tgt_ele
                if not isinstance(child, Comment)
            }

            for src_child in src_ele:
                if isinstance(src_child, Comment):
                    continue
                if ext == ".stage" and (src_child.tag == "Condition" or (src_child.tag == "Action" and not src_child.attrib.get("ActionKey"))):
                    # ignore Condition tags + Action tags without ActionKey
                    continue

                ele_id = self._get_element_identifier(src_child, ext)
                if isinstance(ele_id[1], tuple):
                    name, value = ele_id[1][0], ele_id[1][1]
                else:
                    name, value = ele_id[1], ele_id[2]
                tgt_child = tgt_children_index.get(ele_id)

                not_unique = not name or (name[0].isupper() if ext != ".stage" else False)

                # # If .stage file and the element has "ObjectKey" attribute, skip this element if it's not inside an Action with ActionKey
                # if ext == ".stage" and name == "ObjectKey":
                #     parent = tgt_ele
                #     is_inside_action = False
                #     # Traverse up the ancestors of tgt_ele to find an "Action" with "ActionKey"
                #     while parent is not None:
                #         if parent.tag == "Action":
                #             is_inside_action = True
                #             break
                #         parent = parent.getparent()
                #     if not is_inside_action:
                #         continue

                if tgt_child is None:
                    if not_unique:
                        continue

                    self._handle_new_element(tgt_ele, src_child, path, ext)
                    continue

                current_path = path + [tgt_child]
                # Queue deeper children to stack
                if len(src_child):
                    stack.append((tgt_child, src_child, current_path))

                if not_unique or tgt_child.attrib == src_child.attrib:
                    continue

                self._handle_updated_attributes(tgt_child, src_child, current_path, ext)

    def merge_with(self, update_file: str, is_create_patch: Optional[bool]):
        update_tree = et.parse(update_file, parser=parser)
        update_root = update_tree.getroot()

        if self.root.tag != update_root.tag:
            raise ValueError(f"Root tags differ: {self.root.tag} vs {update_root.tag}")

        # if update_root.attrib:
        #     if self.root.attrib != update_root.attrib:
        #         self.create_base_str()
        #         self.root.attrib.update(update_root.attrib)

        self.is_create_patch = is_create_patch
        self._clear_changes()
        self._merge_elements(self.root, update_root, [], os.path.splitext(update_file)[1])

    # def _merge_elements_recurse(self, target: Element, source: Element, path: list):
    #     target_children_index = {
    #         self._get_element_identifier(child): child
    #         for child in target
    #         if not isinstance(child, Comment)
    #     }
    #     for src_child in source:
    #         if isinstance(src_child, Comment):
    #             continue
    #
    #         src_key = self._get_element_identifier(src_child)
    #         tgt_child = target_children_index.get(src_key)
    #
    #         attrib_key = src_key[1]
    #         not_unique = not attrib_key or attrib_key[0].isupper()
    #
    #         if tgt_child is None:
    #             # if not have first attr or first attr is not unique
    #             if not_unique:
    #                 continue
    #             # self._add_comment_if_needed(target, "NEW")
    #             if not self.is_rewrite:
    #                 target.append(src_child)
    #                 continue
    #
    #             xpath = self._build_xpath(path)
    #             key = (xpath, "new")
    #             new_element = src_child
    #
    #             # if same xpath, add to list
    #             change = self._change_index.get(key)
    #             if change:
    #                 change["element"].append(new_element)
    #             else:
    #                 change = {"xpath": xpath, "type": "new", "element": [new_element]}
    #                 self._changes.append(change)
    #                 self._change_index[key] = change
    #             continue
    #
    #         # Recurse first befoe checking attributes at this level
    #         if len(src_child):
    #             path.append(tgt_child)
    #             self._merge_elements(tgt_child, src_child, path)
    #             path.pop()
    #
    #         if not_unique:
    #             continue
    #
    #         if src_child.attrib == tgt_child.attrib:
    #             continue
    #         # self._add_comment_if_needed(target, "UPDATE", before=tgt_child)
    #         if not self.is_rewrite:
    #             tgt_child.attrib.update(src_child.attrib)
    #             continue
    #         diff_new = {}
    #         for k, new_val in src_child.attrib.items():
    #             old_val = tgt_child.attrib.get(k)
    #             if old_val != new_val:
    #                 diff_new[k] = new_val
    #         if diff_new:
    #             self._changes.append(
    #                 {
    #                     "xpath": self._build_xpath(path + [tgt_child]),
    #                     "type": "update",
    #                     "diff": diff_new,
    #                 }
    #             )
