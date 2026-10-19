import os, re, subprocess, shutil

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "pdf")
os.makedirs(OUT, exist_ok=True)

CFG = [
    ("拼好模主篇（发布版）.md", 2),
    ("拼好模副篇（发布版）.md", 2),
    ("内核旋钮架构（发布版）.md", 3),
    ("MCP 控制层协议规范（发布版）.md", 3),
    ("园丁计划（发布版）.md", 2),
]

SUB = {"\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4"}
CIRC = {"\u246a": 11, "\u246b": 12, "\u246c": 13, "\u246d": 14, "\u246e": 15}
MINUS = "\u2212"


def is_sep(line):
    s = line.strip()
    return s.startswith("|") and set(s) <= set("|-: ")


def conv_outside_code(s, fn):
    parts = s.split("`")
    for i in range(0, len(parts), 2):
        parts[i] = fn(parts[i])
    for i in range(1, len(parts), 2):
        parts[i] = fix_code_blocks(parts[i])
    return "`".join(parts)


def fix_code_blocks(s):
    """代码块与行内代码用 FangSong/等宽字体，不接受 \\ensuremath，只能换 ASCII。"""
    s = s.replace(MINUS, "-")
    return s


def apply_all(body):
    """先处理围栏代码块（整块原样），再逐行处理行内代码。"""
    out = []
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                j += 1
            block = lines[i:j + 1]
            out.extend([block[0]] + [fix_code_blocks(x) for x in block[1:-1]] + block[-1:])
            i = j + 1
        else:
            out.append(conv_outside_code(lines[i], prep_text))
            i += 1
    return "\n".join(out)


def prep_text(x):
    for k, v in SUB.items():
        x = x.replace(k, "\\textsubscript{" + v + "}")
    for c, n in CIRC.items():
        x = x.replace(c, "（" + str(n) + "）")
    # SimSun 无 U+2212，改走数学模式的减号。
    # 不可用 $-$：前接数字时 pandoc 不认其为数学开界，$ 退化为字面量并使后续配对错位，
    # 会把大段汉字吞进 latinmodern-math 而成片缺字。
    x = x.replace(MINUS, r"\ensuremath{-}")
    return x


def fix_tables(md):
    lines = md.split("\n")
    out = list(lines)
    i = 0
    while i < len(out) - 1:
        if out[i].strip().startswith("|") and is_sep(out[i + 1]):
            j = i
            rows = []
            while j < len(out) and out[j].strip().startswith("|"):
                rows.append(out[j])
                j += 1
            ncol = len(out[i].strip().strip("|").split("|"))
            if ncol >= 2 and len(rows) >= 3:
                lens = [0] * ncol
                for r in rows:
                    if is_sep(r):
                        continue
                    cells = r.strip().strip("|").split("|")
                    for k in range(min(ncol, len(cells))):
                        L = len(re.sub(r"[*`\s]", "", cells[k]))
                        lens[k] = max(lens[k], min(L, 46))
                w = [l + 8 for l in lens]
                tot = sum(w)
                dashes = [max(6, round(126 * x / tot)) for x in w]
                out[i + 1] = "|" + "|".join(":" + "-" * d for d in dashes) + "|"
            i = j
        else:
            i += 1
    return "\n".join(out)


def cover_escape(s):
    """封面用 LaTeX 直排：汉字之间的空格会被吞掉，须显式补。"""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
    s = s.replace("_", r"\_").replace("$", r"\$")
    s = re.sub(r"(?<=[^\s])\s+(?=[^\s])", r"\\hspace{0.34em}", s)
    return s


def cover_marks(s):
    """封面引语的记号转写，须在 cover_escape 之后做，否则反斜杠会被转义掉。"""
    for k, v in SUB.items():
        s = s.replace(k, "\\textsubscript{" + v + "}")
    for c, n in CIRC.items():
        s = s.replace(c, "（" + str(n) + "）")
    return s.replace(MINUS, r"\ensuremath{-}")


LATEX = r"""
\begin{titlepage}
\centering
\vspace*{3.0cm}
{\Huge\bfseries %(TITLE)s\par}
\vspace{0.9cm}
{\LARGE %(SUB1)s\par}
\vspace{0.3cm}
{\large %(SUB2)s\par}
\vspace{2.0cm}
{\large %(QUOTE)s\par}
\vfill
{\large 著作权人：邵寿鹏\par}
\vspace{0.22cm}
{\large 开源署名：魔法徽章（mofahuizhang）\par}
\vspace{1.0cm}
{\large 发布版 1.0\par}
\vspace{0.22cm}
{\large 2026 年 10 月 19 日\par}
\vspace{1.4cm}
\end{titlepage}
"""

YAML = r"""---
title: ""
documentclass: ctexart
classoption: "UTF8,11pt"
geometry: "margin=2.3cm,top=2.5cm,bottom=2.5cm"
CJKmainfont: SimSun
CJKsansfont: SimHei
monofont: SimSun
toc-title: 目录
colorlinks: false
header-includes:
  - \linespread{1.42}
  - \usepackage{longtable,array,etoolbox}
  - \AtBeginEnvironment{longtable}{\footnotesize}
  - \setlength{\LTleft}{0pt}
  - \setlength{\LTright}{0pt}
  - \setlength{\tabcolsep}{3.2pt}
  - \renewcommand{\arraystretch}{1.14}
  - \setlength{\parindent}{0pt}
  - \setlength{\parskip}{0.5em}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyfoot[C]{\small\thepage}
  - \renewcommand{\headrulewidth}{0pt}
  - \xeCJKsetup{CJKspace=true}
  - \xeCJKDeclareCharClass{CJK}{"0370 -> "03FF, "2190 -> "21FF, "2200 -> "22FF, "2460 -> "24FF, "2500 -> "257F, "25A0 -> "25FF}
---

"""


def build(fn, depth):
    src = os.path.join(D, fn)
    t = open(src, encoding="utf-8").read()
    k = t.find("\n## ")
    head, body = t[:k], t[k:]

    title = re.search(r"^# (.+)$", head, re.M).group(1).strip()
    sub = re.search(r"^\*\*(.+?)\*\*$", head, re.M).group(1).strip()
    sub1, _, sub2 = sub.partition(" · ")
    quote = ""
    for line in head.split("\n"):
        line = line.strip()
        if line.startswith("> ") and ("题签引语" in line or "一句话" in line):
            quote = line[2:]
            quote = re.sub(r"^\*{0,2}(题签引语|一句话)\*{0,2}：", "", quote)
            break

    body = apply_all(body)
    body = fix_tables(body)

    ph = {
        "TITLE": cover_escape(title),
        "SUB1": cover_escape(sub1),
        "SUB2": cover_escape(sub2),
        "QUOTE": cover_marks(cover_escape(quote)),
    }
    md = YAML + (LATEX % ph) + "\n" + body

    tag = re.sub(r"[^0-9A-Za-z]", "", fn)[:12]
    work = os.path.join(OUT, "_w_" + tag)
    os.makedirs(work, exist_ok=True)
    mdp = os.path.join(work, "b.md")
    open(mdp, "w", encoding="utf-8").write(md)

    r = subprocess.run(["pandoc", mdp, "-s", "-o", "b.tex", "--toc",
                        "--toc-depth=%d" % depth], cwd=work,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print("PANDOC FAIL", fn, (r.stderr or "")[-600:])
        return False

    texp = os.path.join(work, "b.tex")
    tex = open(texp, encoding="utf-8").read()
    a = tex.find("\\begin{titlepage}")
    b = tex.find("\\end{titlepage}")
    if a >= 0 and b > a:
        blk = tex[a:b + len("\\end{titlepage}")]
        tex = tex[:a] + tex[b + len("\\end{titlepage}"):]
        tex = tex.replace("\\begin{document}", "\\begin{document}\n" + blk, 1)
        open(texp, "w", encoding="utf-8").write(tex)

    for i in range(2):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "b.tex"],
                           cwd=work, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            print("XELATEX FAIL", fn, "pass", i + 1)
            print((r.stdout or "")[-1200:])
            return False

    log = open(os.path.join(work, "b.log"), encoding="utf-8", errors="replace").read()
    miss = sorted(set(re.findall(r"Missing character: There is no (.{1,24}?) in font", log)))

    dst = os.path.join(OUT, title.replace("/", "·") + ".pdf")
    shutil.copyfile(os.path.join(work, "b.pdf"), dst)

    txt = subprocess.run(["pdftotext", dst, "-"], capture_output=True,
                         encoding="utf-8", errors="replace")
    pages = (txt.stdout or "").count("\f")
    print("OK %-24s %3d 页  %8d 字节  缺字:%s"
          % (title, pages, os.path.getsize(dst), "、".join(miss) if miss else "无"))
    return True


ok = sum(1 for fn, d in CFG if build(fn, d))
print("完成 %d/%d" % (ok, len(CFG)))
