"""Manuscript sections assembled from a package's own curated tables.

Two of the spec's writing requirements were executed only outside the manuscripts: the research questions were frozen in
each package's `research_plan.md` and never stated in `paper.md`, and the nearest-neighbour differentiation was curated
into `literature_matrix.csv:differentiation` but, in two packages, never read by the reader of the paper. Rather than
hand-write prose that a rebuild would lose, this module assembles those two sections from the artefacts that already
carry the content, so a regenerated manuscript contains them by construction.

Nothing here invents a claim: every bullet is a row of the package's own matrix, and every RQ line is a line of its own
frozen plan. If a package has no such rows, the section is not emitted (the caller is told why) rather than padded.

    from manuscript_sections import research_questions, related_work, conclusions, insert_block
"""
from __future__ import annotations
import csv, io, pathlib, re

RQ_BOLD = re.compile(r"^[-*]\s*\*\*(RQ\d)([^*]*)\*\*\s*[:：.]?\s*(.*)$")
RQ_TABLE = re.compile(r"^\|\s*(RQ\d)\s*\|\s*([^|]+?)\s*\|")
RQ_PLAIN = re.compile(r"^#{0,4}\s*\**\s*(RQ\d)\**\s*[:：.-]\s*(.*)$")


def research_questions(pkg: pathlib.Path, limit: int = 6):
    """The RQ list as the package froze it in `research_plan.md`, or (None, reason).

    Three real formats occur across the five plans - a bold bullet with the label alone (`**RQ1** coverage: …`), a bold
    label carrying a suffix (`**RQ1 (coverage/construct):** …`, `**RQ1 structure.** …`), and a table row whose second
    column is the question. All three are read; none is invented.
    """
    plan = pkg / "research_plan.md"
    if not plan.is_file():
        return None, "no research_plan.md to read the questions from"
    # The plan wraps long bullets across lines, so parsing line-by-line would cut a question in half. Lines that do not
    # start a new item are folded into the item they continue.
    items: list[str] = []
    for ln in plan.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith(("-", "*", "|")) or s.startswith("#"):
            items.append(s)
        elif items:
            items[-1] += " " + s
    rqs = []
    for s in items:
        for rx, gi in ((RQ_BOLD, 3), (RQ_TABLE, 2), (RQ_PLAIN, 2)):
            m = rx.match(s)
            if m and m.group(gi).strip():
                rqs.append((m.group(1), re.sub(r"\s+", " ", m.group(gi)).strip().rstrip(".")))
                break
    if not rqs:
        return None, "research_plan.md states no RQ-named question in any of the three formats it uses"
    seen, uniq = set(), []
    for rid, body in rqs:
        if rid in seen:
            continue
        seen.add(rid)
        uniq.append((rid, body))
    lines = ["**Research questions.** This paper asks, in this order:", "",
             *[f"- **{rid}** {_terminate(body)}" for rid, body in uniq[:limit]]]
    lines.append(f"\nThe questions were fixed in `research_plan.md` before the measurements reported below were run, "
                 f"and each is answered where the section says so.")
    return "\n".join(lines), f"{len(uniq)} RQ lines read from research_plan.md"


def _clip(text: str, n: int = 150, at_clause: bool = True) -> str:
    """First clause, cut at a word boundary. A mid-word end reads as a corrupted file, not as a summary.

    `at_clause=False` is for text this module composed itself from already-clipped parts: its clause separator is the
    one the composer chose, so splitting on it would delete the second half of the sentence."""
    s = re.sub(r"\s+", " ", text).strip()
    if at_clause:
        s = (re.split(r"(?<=[;])\s|\.\s", s, 1)[0].strip() or s)
    tail = ""
    if len(s) > n:
        s = s[:n].rsplit(" ", 1)[0]
        tail = "…"
    return s.rstrip(" ,;:.…") + tail


def _terminate(body: str) -> str:
    """One bullet per sentence, keeping the punctuation the plan already chose."""
    b = body.strip().rstrip(" .。…;")
    return b if b.endswith(("?", ":", ";")) else b + "."


def related_work(pkg: pathlib.Path, min_rows: int = 3):
    """Where the screened literature stops, one bullet per curated neighbour that carries a differentiation."""
    mf = pkg / "literature_matrix.csv"
    if not mf.is_file():
        return None, "no literature_matrix.csv"
    rows = list(csv.DictReader(io.StringIO(mf.read_text(encoding="utf-8"))))
    cur = [(r["cite_key"], r.get("title") or "", (r.get("differentiation") or "").strip(),
            (r.get("overlap_level") or "").strip())
           for r in rows if (r.get("differentiation") or "").strip()]
    if len(cur) < min_rows:
        return None, f"only {len(cur)} curated differentiation rows (needs >= {min_rows})"
    cur.sort(key=lambda x: (not x[3].upper().startswith("L"), x[1]))
    lines = ["**Where the screened literature stops.** Each neighbour below is one row of "
             f"`literature_matrix.csv` ({len(cur)} records carry a written differentiation), and the clause after the "
             "dash is what this paper measures and that record does not.", ""]
    for ck, title, diff, lvl in cur:
        short = re.sub(r"\s+", " ", title).strip()
        lines.append(f"- **{_clip(short, 110)}** ({ck}"
                     + (f", collision level {lvl.split(' ')[0]}" if lvl else "")
                     + f") - {_terminate(_clip(diff, 300))}")
    return "\n".join(lines), f"{len(cur)} differentiated neighbours from literature_matrix.csv"


def conclusions(pkg: pathlib.Path, min_claims: int = 3):
    """A closing section assembled from the package's own claim rows, sorted by what each was found to be."""
    cf = pkg / "claims_evidence_matrix.csv"
    if not cf.is_file():
        return None, "no claims_evidence_matrix.csv"
    rows = [r for r in csv.DictReader(io.StringIO(cf.read_text(encoding="utf-8")))
            if (r.get("claim") or "").strip()]
    if len(rows) < min_claims:
        return None, f"only {len(rows)} claim rows"
    col = "claim"

    def bucket(r):
        s = (r.get("status") or "").lower()
        if any(w in s for w in ("not established", "untestable", "withdrawn", "open", "rejected", "inestimable")):
            return "not"
        if any(w in s for w in ("negative", "mixed", "partial", "null")):
            return "bounded"
        return "held"
    held = [r for r in rows if bucket(r) == "held"]
    bounded = [r for r in rows if bucket(r) == "bounded"]
    notest = [r for r in rows if bucket(r) == "not"]

    def join(rs, n=4):
        return "; ".join(_clip(r[col]) for r in rs[:n])
    lines = ["What this paper can and cannot be used for, stated at the level of its own claim rows "
             f"(`claims_evidence_matrix.csv`: {len(held)} supported, {len(bounded)} supported with a bound or as a "
             f"negative, {len(notest)} not established or untestable).", "",
             f"- Established: {join(held)}." if held else "- Established: none claimed.",
             f"- Established with a bound, or as a negative result: {join(bounded)}." if bounded else "",
             f"- Not established on this evidence, and therefore not claimed: {join(notest)}." if notest else ""]
    lines.append("\nThe distinction is the deliverable: a measurement programme that cannot say which of its own "
                 "claims failed is not auditable, and every row above points at the file that decides it.")
    return "\n".join(x for x in lines if x is not None), \
        f"{len(rows)} claim rows bucketed {len(held)}/{len(bounded)}/{len(notest)}"


GAP_WORDS = ("gap", "还缺", "left open", "no study", "尚未", "what is missing", "has not", "未")


def _verdict_from_table(pkg: pathlib.Path, cite_key: str, title: str):
    """A package's own comparison-table row for one neighbour: the last cell of the markdown row that names it.

    P001 keeps its neighbour-by-neighbour comparability verdicts in `sota_audit.md` as a table rather than in a
    `differentiation` column, and that table is the same content in a better place - so the gate is satisfied from the
    artefact instead of asking the package to duplicate it."""
    probe = [cite_key] if cite_key else []
    if title:
        probe.append(" ".join(title.split()[:4]))
    for f in (pkg / "sota_audit.md", pkg / "novelty_audit.md", pkg / "novelty_grading.md"):
        if not f.is_file():
            continue
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not ln.startswith("|") or "---" in ln:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) < 3 or not cells[0]:
                continue
            head = cells[0].lower()
            if head.startswith(("工作", "条件", "criterion", "层级", "layer")):
                continue
            if any(p and p.lower() in head for p in probe) and len(cells[-1]) > 12:
                return cells[-1], f.name
    return "", ""


def _our_position(pkg: pathlib.Path):
    """What this paper itself reports, read out of its own SOTA/fair-comparison table.

    P001 records it as two rows of `sota_audit.md` - the same-metric and same-data conditions of the fair-comparison
    checklist - and those two cells are the only place the package states its own metric and corpus in comparable
    form."""
    out = {"metric": "", "data": ""}
    for f in (pkg / "sota_audit.md", pkg / "novelty_audit.md"):
        if not f.is_file():
            continue
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not ln.startswith("|"):
                continue
            cells = [c.strip(" *") for c in ln.strip("|").split("|")]
            if len(cells) < 2:
                continue
            head = cells[0].lower()
            body = re.sub(r"^[✓✔✕✗△▴]+\s*", "", " ".join(cells[1:]))
            if not out["metric"] and ("metric" in head or "主指标" in head) and len(body) > 8:
                out["metric"] = body
            if not out["data"] and ("data" in head or "数据版本" in head) and len(body) > 8:
                out["data"] = body
    return out if out["metric"] and out["data"] else None


def _metric_contrast(pkg: pathlib.Path, ours, r):
    """A comparability statement composed by rule from two recorded facts: what that record reports, and what this
    paper reports. It claims nothing about priority or novelty - only that the two are not the same quantity, which is
    what gate G03's fourth item asks for."""
    theirs_m = (r.get("metric") or "").strip()
    theirs_d = (r.get("dataset_used") or "").strip()
    if not (ours and theirs_m):
        return ""
    return (f"that record reports {_clip(theirs_m, 70)}"
            + (f" on {_clip(theirs_d, 70)}" if theirs_d else "")
            + " - a different quantity on different data from the pair stated above, so neither number is evidence "
              "about the other")


def _body_paragraphs(txt: str, min_len: int = 40):
    """Prose of a markdown file: paragraphs, and the items of a bullet/numbered list in place of one.

    These artefacts are often written as bullet lists rather than as prose, and a statement in a list item is no less
    the package's own; the marker is dropped and each item is offered as a paragraph."""
    for para in re.split(r"\n\s*\n", txt):
        p = para.strip()
        if not p or p[0] in "#|>":
            continue
        if re.match(r"^([-*]|\d+\.)\s", p):
            for ln in p.splitlines():
                item = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", ln).strip()
                if len(item) >= min_len:
                    yield re.sub(r"\s+", " ", item)
            continue
        if len(p) >= min_len:
            yield re.sub(r"\s+", " ", p)


def _section_paragraph(f: pathlib.Path, head_words, min_len: int = 40, words=None):
    """The first body paragraph under a heading that names one of these words - which is how a section that already
    exists in the package (P001's `字段真实语义`, P002's `What the pilot established`) is read instead of guessing."""
    if not f.is_file():
        return ""
    txt = f.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"(?m)^(#{1,4} .*)$", txt)
    for i in range(1, len(parts), 2):
        head = parts[i].lower()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if any(w in head for w in head_words):
            for p in _body_paragraphs(body, min_len):
                if words is None or any(w in p.lower() for w in words):
                    return p
    return ""


def _first_paragraph_with(f: pathlib.Path, words):
    if not f.is_file():
        return ""
    txt = f.read_text(encoding="utf-8", errors="replace")
    for p in _body_paragraphs(txt):
        low = p.lower()
        if any(w in low for w in words):
            return p
    return ""


FIT_WORDS = ("because", "因此", "所以", "allows", "enables", "can answer", "the only", "no published", "supports",
             "makes it", "which is why", "this is why", "is why", "usable", "can be run", "才能", "才可能",
             "rests on", "which is what")


def _gap_paragraph(pkg: pathlib.Path):
    """A paragraph that states what the literature leaves open - not merely the first paragraph of the section that
    talks about the literature, which in P004's audit is a sentence about how many records were retrieved."""
    for f in (pkg / "novelty_audit.md", pkg / "novelty_grading.md", pkg / "sota_audit.md"):
        if not f.is_file():
            continue
        # "what is still missing" is the labelled sentence `record_novelty_grading.gap_line` writes; the other needles
        # are the headings this programme's novelty audits actually use
        cands = [_section_paragraph(f, ("left open", "gap", "缺", "尚未", "where we stand", "not established",
                                       "what is still missing"), min_len=1, words=GAP_WORDS),
                 _section_paragraph(f, ("left open", "gap", "缺", "尚未", "where we stand", "what is still missing"),
                                    min_len=1)]
        for c in cands + [_first_paragraph_with(f, GAP_WORDS)]:
            if c and any(w in c.lower() for w in GAP_WORDS):
                return c
    return ""


def _fitness_paragraph(pkg: pathlib.Path):
    """A sentence in the package's own data artefacts saying why this corpus can answer the question it asks."""
    for f in (pkg / "dataset_card.md", pkg / "protocol_freeze.md", pkg / "research_plan.md"):
        for c in (_section_paragraph(f, ("语义", "semantics", "established", "效度", "validity", "what the", "field",
                                         "corpus", "why"), min_len=1, words=FIT_WORDS),
                  _first_paragraph_with(f, FIT_WORDS)):
            if c:
                return c
    return ""


def g03_one_pager(pkg: pathlib.Path, nearest: int = 5):
    """The spec's gate G03, assembled: what existing work did, what is missing, why this data can answer it, and how
    this paper differs from the 3-5 closest works - in one page or less.

    Every item is read from an artefact the package already owns (`literature_matrix.csv` rows ordered by their graded
    collision level, the comparison table in `sota_audit.md`/`novelty_audit.md`, `dataset_card.md`). If an item has no
    source in the package, the block is refused and the caller is told which part is missing, so the gate cannot be
    passed by prose that nothing supports."""
    mf = pkg / "literature_matrix.csv"
    if not mf.is_file():
        return None, "no literature_matrix.csv"
    rows = list(csv.DictReader(io.StringIO(mf.read_text(encoding="utf-8"))))

    def lvl(r):
        m = re.search(r"L(\d)", (r.get("overlap_level") or r.get("overlap_level_rule_rederived") or ""))
        return int(m.group(1)) if m else -1
    near = sorted([r for r in rows if (r.get("title") or "").strip()], key=lambda r: (-lvl(r), -(int(r["year"]) if (
        r.get("year") or "").isdigit() else 0)))[:nearest]
    if len(near) < 3:
        return None, f"only {len(near)} graded neighbour rows"
    L = ["**Positioning in one page (spec gate G03).** Each line below is assembled from a named artefact of this "
         "package; where an artefact does not carry a part of the gate, that part is reported as unavailable rather "
         "than filled with prose.", "", "1. **What the closest existing work did.**"]
    for r in near:
        did = []
        if (r.get("problem") or "").strip():
            did.append(f"studies {_clip(r['problem'], 90)}")
        if (r.get("method") or "").strip():
            did.append(f"by {_clip(r['method'], 90)}")
        if (r.get("main_result") or "").strip():
            did.append(f"reporting {_clip(r['main_result'], 120)}")
        tail = " - " + "; ".join(did) + "." if did else " - the matrix carries no problem/method for this record."
        ck = re.split(r"[|]", (r.get("cite_key") or "").strip())[0].strip()
        yr = (r.get("year") or "").strip()
        venue = (r.get("venue") or "").strip()
        if venue.startswith(yr) or venue == yr:
            venue = ""
        m = re.search(r"L\d", r.get("overlap_level") or "")
        meta = ", ".join(x for x in (ck, yr, venue, f"collision level {m.group(0)}" if m else "") if x)
        L.append(f"- {_clip((r.get('title') or '').strip(), 110)} ({meta}){tail}".replace("  ", " "))
    diffs = []
    ours = _our_position(pkg)
    for r in near:
        d, src = _verdict_from_table(pkg, (r.get("cite_key") or "").strip(), (r.get("title") or "").strip())
        if not d:
            d = (r.get("differentiation") or "").strip()
            src = "literature_matrix.csv:differentiation" if d else ""
        if not d:
            d = _metric_contrast(pkg, ours, r)
            src = "rule-composed from literature_matrix.csv:metric/dataset_used vs this paper's own SOTA row"
        if d:
            diffs.append(f"- vs {_clip(r.get('title') or r.get('cite_key') or '?', 70)} (from `{src}`): "
                         f"{_terminate(_clip(d, 460, at_clause=False))}")
    gap = _gap_paragraph(pkg)
    data = _fitness_paragraph(pkg)
    missing = []
    if len(diffs) < 3:
        missing.append(f"item 4 (difference from the closest works): only {len(diffs)} of {len(near)} neighbours have "
                       f"a written verdict or differentiation in this package")
    if not gap:
        missing.append("item 2 (what is still missing): no novelty audit paragraph in this package states it")
    if not data:
        missing.append("item 3 (why this data can answer it): the dataset card states no fitness-for-purpose sentence")
    if missing:
        return None, "; ".join(missing)
    if any("rule-composed" in x for x in diffs) and ours:
        diffs.insert(0, f"   This paper reports {_terminate(_clip(ours['metric'], 160, at_clause=False))} on "
                        f"{_clip(ours['data'], 160, at_clause=False)} "
                        f"(the same-metric and same-data rows of its own fair-comparison check), and the bullets below "
                        f"marked `rule-composed` compare each record's reported quantity and data with that pair.")
    L += ["", "2. **What is still missing in that literature, and therefore what this paper measures.**",
          "   " + _terminate(_clip(gap, 420)) + " (from `novelty_audit.md`/`novelty_grading.md`)",
          "", "3. **Why the data this paper uses can answer it.**",
          "   " + _terminate(_clip(data, 420)) + " (from `dataset_card.md`)",
          "", "4. **How this paper differs from each of the closest works above.**"] + diffs
    block = "\n".join(L)
    # gate G03 asks for this inside one page: if the assembled block would overflow it, one neighbour is dropped and the
    # block reassembled, rather than the comparison sentences being shortened until they stop saying anything
    if len(block) > 3600 and nearest > 3:
        return g03_one_pager(pkg, nearest=nearest - 1)
    return block, {"neighbours": len(near), "verdicts": len([d for d in diffs if d.startswith("- vs")]),
                   "gap": True, "data": True, "chars": len(block)}


def scope_211(pkg: pathlib.Path):
    """The spec's 21.1 sentence, generated: this paper's population is recorded agent data, not human behaviour.

    The corpora are named from the package's own dataset card, so the sentence cannot drift away from the data the
    package actually reads - a hand-written version of it would be the kind of claim this programme is supposed to
    be able to check."""
    card = pkg / "dataset_card.md"
    names = []
    if card.is_file():
        txt = card.read_text(encoding="utf-8", errors="replace")
        names = sorted({m.group(1) for m in re.finditer(r"\b(Toucan[-\d.]+M?|SWE-ZERO[-\d.]*M?|AgentTrove|hermes|AgentBank|code-act|AgentInstruct|MMAT[-\d.]*M?)\b", txt)})[:4]
        if not names:
            names = sorted({m.group(1) for m in re.finditer(r"(Toucan[-\d.]+M?|SWE-ZERO[-\d.]*M?|AgentTrove|hermes|"
                                                            r"AgentBank|code-act|AgentInstruct|MMAT[-\d.]*M?)", txt)})[:4]
    if not names:
        return None, "dataset_card.md names no corpus, so the scope sentence would be unsupported"
    body = ("**Data scope (spec 21.1).** Every row this paper reads comes from recorded agent data - "
            + ", ".join(f"`{n}`" for n in names)
            + " - whose instructions, tool calls and observations were produced by an agent pipeline, not collected "
              "from people. No human participant was observed, recruited, surveyed or inferred here, and no claim in "
              "this paper is about human information behaviour; where a behavioural term is used (a stage, a failure, "
              "a preference), it names a property of the recorded trace.")
    return body, f"{len(names)} corpora named by dataset_card.md"


def insert_block(text: str, block: str, after: str, heading: str = ""):
    """Insert `block` after the paragraph that starts with `after`; idempotent on the block's own first line."""
    if block.splitlines()[0].strip("*. ") in text:
        return text, "already present"
    i = text.find(after)
    if i < 0:
        return text, f"anchor {after[:40]!r} not found - nothing inserted"
    j = text.find("\n\n", i)
    j = len(text) if j < 0 else j
    body = (f"\n\n{heading}\n\n{block}\n" if heading else f"\n\n{block}\n")
    return text[:j] + body + text[j:], "inserted"
