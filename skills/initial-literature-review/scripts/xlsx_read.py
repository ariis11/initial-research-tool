#!/usr/bin/env python3
"""xlsx_read.py -- read an .xlsx with the standard library only.

University libraries publish their subscribed holdings as Excel files, and knowing
exactly what the university licenses is what turns a list of 149 missing PDFs
into "open these, send the rest to interlibrary loan". No xlsx library is
installed here and an .xlsx is a zip of XML, so this reads it directly rather
than adding a dependency for one file format.

Only what is needed: shared strings, inline strings and numbers, by row.
"""
from __future__ import annotations

import re, sys, zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col(ref: str) -> int:
    """'BC12' -> 54. Cells with no value are skipped in the XML, so a row has
    to be rebuilt by column index or the columns silently shift."""
    letters = re.match(r"([A-Z]+)", ref or "")
    n = 0
    for ch in (letters.group(1) if letters else ""):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def rows(path: str, sheet: str = "xl/worksheets/sheet1.xml"):
    z = zipfile.ZipFile(path)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    for _, el in ET.iterparse(z.open(sheet), events=("end",)):
        if el.tag != f"{NS}row":
            continue
        out: list[str] = []
        for cl in el.findall(f"{NS}c"):
            i = _col(cl.get("r", ""))
            while len(out) <= i:
                out.append("")
            t = cl.get("t")
            if t == "s":
                v = cl.find(f"{NS}v")
                out[i] = shared[int(v.text)] if v is not None and v.text else ""
            elif t == "inlineStr":
                out[i] = "".join(x.text or "" for x in cl.iter(f"{NS}t"))
            else:
                v = cl.find(f"{NS}v")
                out[i] = v.text or "" if v is not None else ""
        yield out
        el.clear()


if __name__ == "__main__":
    p = sys.argv[1]
    sh = sys.argv[2] if len(sys.argv) > 2 else "xl/worksheets/sheet1.xml"
    for i, r in enumerate(rows(p, sh)):
        print(r)
        if i > 6:
            break
