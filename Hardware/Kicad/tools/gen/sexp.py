"""Minimal S-expression reader used to pull pin tables out of KiCad libraries."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


class Sym(str):
    """Unquoted atom."""


def parse(text):
    stack, cur = [], []
    pos = 0
    while True:
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        lp, rp, s, atom = m.groups()
        if lp:
            stack.append(cur)
            cur = []
        elif rp:
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif s is not None:
            cur.append(s.replace('\\"', '"').replace("\\\\", "\\"))
        elif atom is not None:
            cur.append(Sym(atom))
    return cur[0] if len(cur) == 1 else cur


def find_all(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def find(node, head):
    r = find_all(node, head)
    return r[0] if r else None


def walk(node, head):
    """Yield every sub-list whose head is `head` (depth first)."""
    if isinstance(node, list):
        if node and node[0] == head:
            yield node
        for c in node:
            yield from walk(c, head)
