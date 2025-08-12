from typing import Optional
from xml.sax.saxutils import quoteattr

from lxml import etree as et

from lib.utils import Utils

Element = et._Element
ElementTree = et._ElementTree
Comment = et._Comment

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

        with open(fileout, "w", encoding="utf-8") as f:
            f.write(content)
        self._clear_changes()
        return 1

    def _get_element_key(self, element: Element):
        """
        Generates a unique key for an element based on its tag and its first attribute.
        Returns a tuple: (tag, first_attribute_key, first_attribute_value).
        """
        first_attr_pair = next(iter(element.attrib.items()), (None, None))
        return (element.tag, first_attr_pair[0], first_attr_pair[1])

    # def _build_xpath(self, path: list[Element], current: Element | None = None):
    def _build_xpath(self, path: list[Element]):
        # elements = path if current is None else path + [current]
        segments = []
        # for elem in elements:
        for elem in path:
            tag = elem.tag
            key_attr = next(iter(elem.attrib.items()), None)
            if key_attr:
                k, v = key_attr
                if "'" in v:
                    segments.append(f'{tag}[@{k}="{v}"]')
                else:
                    segments.append(f"{tag}[@{k}='{v}']")
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
        self, parent: Element, new_element: Element, path_to_parent: list[Element]
    ):
        if self.is_create_patch is None:
            parent.append(new_element)
            return

        xpath_to_parent = self._build_xpath(path_to_parent)
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
        self, target: Element, source: Element, path_to_target: list[Element]
    ):
        if self.is_create_patch is None:
            target.attrib.update(source.attrib)
            return

        diff = {k: v for k, v in source.attrib.items() if target.attrib.get(k) != v}

        if diff:
            self._changes.append(
                {
                    "xpath": self._build_xpath(path_to_target),
                    "type": "update",
                    "diff": diff,
                }
            )

    def _merge_elements(
        self, target_root: Element, source_root: Element, base_path: list[Element]
    ):
        stack = [
            (target_root, source_root, list(base_path))
        ]  # stack holds tuples of (target, source, path)

        while stack:
            tgt_elem, src_elem, path = stack.pop()

            tgt_children_index = {
                self._get_element_key(child): child
                for child in tgt_elem
                if not isinstance(child, Comment)
            }

            for src_child in src_elem:
                if isinstance(src_child, Comment):
                    continue

                src_key = self._get_element_key(src_child)
                tgt_child = tgt_children_index.get(src_key)

                attrib_key = src_key[1]
                not_unique = not attrib_key or attrib_key[0].isupper()

                if tgt_child is None:
                    if not_unique:
                        continue
                    self._handle_new_element(tgt_elem, src_child, path)
                    continue

                current_path = path + [tgt_child]
                # Queue deeper children to stack
                if len(src_child):
                    stack.append((tgt_child, src_child, current_path))

                if not_unique:
                    continue

                if tgt_child.attrib == src_child.attrib:
                    continue

                self._handle_updated_attributes(tgt_child, src_child, current_path)

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
        self._merge_elements(self.root, update_root, [])

    # def _merge_elements_recurse(self, target: Element, source: Element, path: list):
    #     target_children_index = {
    #         self._get_element_key(child): child
    #         for child in target
    #         if not isinstance(child, Comment)
    #     }
    #     for src_child in source:
    #         if isinstance(src_child, Comment):
    #             continue
    #
    #         src_key = self._get_element_key(src_child)
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
