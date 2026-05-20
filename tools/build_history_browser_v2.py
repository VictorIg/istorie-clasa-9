from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

from build_history_browser import (
    DATA_DIR,
    ROOT,
    SITE_DIR,
    TOPICS,
    clean_text,
    discover_papers,
    file_url,
    norm,
    question_regex,
    rel_path,
    score_topic,
    slug,
    strip_diacritics,
    write_csv,
)
from pypdf import PdfReader


TEACHER_PDF = ROOT / "Tabel linkuri clasa 9-a Contemporana.pdf"


def extract_pdf_pages(path: Path) -> list[str]:
    try:
        return [(page.extract_text() or "") for page in PdfReader(str(path)).pages]
    except Exception:
        return []


def page_offsets(pages: list[str]) -> tuple[str, list[tuple[int, int]]]:
    chunks: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for page_number, page in enumerate(pages, start=1):
        offsets.append((cursor, page_number))
        chunks.append(page)
        cursor += len(page) + 2
    return "\n\n".join(chunks), offsets


def page_for_offset(offsets: list[tuple[int, int]], offset: int) -> int:
    page = 1
    for start, page_number in offsets:
        if start <= offset:
            page = page_number
        else:
            break
    return page


def subject_spans(text: str) -> list[tuple[str, int, int]]:
    normalized = strip_diacritics(text)
    patterns = [
        (r"SUBIECTUL\s+I\b", "I"),
        (r"SUBIECTUL\s+(?:al\s+)?II(?:-lea)?\b", "II"),
        (r"SUBIECTUL\s+(?:al\s+)?III(?:-lea)?\b", "III"),
    ]
    found: list[tuple[int, str]] = []
    for pattern, subject in patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            found.append((match.start(), subject))
    found.sort()
    spans: list[tuple[str, int, int]] = []
    for index, (start, subject) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(text)
        spans.append((subject, start, end))
    return spans


def item_tasks_from_subject(
    paper_id: str,
    subject: str,
    subject_text: str,
    subject_start: int,
    offsets: list[tuple[int, int]],
    test_path: str,
    barem_path: str,
) -> list[dict[str, object]]:
    normalized = strip_diacritics(subject_text)
    matches = list(question_regex().finditer(normalized))
    tasks: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(subject_text)
        item = match.group(1)
        text = clean_text(subject_text[start:end])
        if len(text) < 18:
            continue
        absolute_start = subject_start + start
        page = page_for_offset(offsets, absolute_start)
        task_ref = f"{subject}.{item}"
        task_id = f"{paper_id}-{slug(task_ref)}"
        tasks.append(
            {
                "task_id": task_id,
                "paper_id": paper_id,
                "task_ref": task_ref,
                "subject": subject,
                "item": item,
                "task_level": "item",
                "page": page,
                "task_text": text,
                "classification_text": clean_text(subject_text + " " + text),
                "test_path": test_path,
                "test_url": file_url(test_path, page),
                "barem_path": barem_path,
                "barem_url": file_url(barem_path) if barem_path else "",
            }
        )
    return tasks


def extract_tasks() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    papers = discover_papers()
    paper_rows: list[dict[str, object]] = []
    tasks: list[dict[str, object]] = []
    for paper in papers:
        test_path = rel_path(paper.test_path)
        barem_path = rel_path(paper.barem_path) if paper.barem_path else ""
        paper_rows.append(
            {
                "paper_id": paper.paper_id,
                "year": paper.year,
                "session": paper.session,
                "variant": paper.variant,
                "test_path": test_path,
                "barem_path": barem_path,
                "page_count": paper.page_count,
            }
        )
        pages = extract_pdf_pages(paper.test_path)
        full_text, offsets = page_offsets(pages)
        for subject, start, end in subject_spans(full_text):
            section_text = clean_text(full_text[start:end])
            if len(section_text) < 30:
                continue
            page = page_for_offset(offsets, start)
            if subject == "II":
                tasks.append(
                    {
                        "task_id": f"{paper.paper_id}-ii-all",
                        "paper_id": paper.paper_id,
                        "task_ref": "II.all",
                        "subject": "II",
                        "item": "all",
                        "task_level": "section",
                        "page": page,
                        "task_text": section_text,
                        "classification_text": section_text,
                        "test_path": test_path,
                        "test_url": file_url(test_path, page),
                        "barem_path": barem_path,
                        "barem_url": file_url(barem_path) if barem_path else "",
                    }
                )
            elif subject == "III":
                tasks.append(
                    {
                        "task_id": f"{paper.paper_id}-iii-essay",
                        "paper_id": paper.paper_id,
                        "task_ref": "III.essay",
                        "subject": "III",
                        "item": "essay",
                        "task_level": "essay",
                        "page": page,
                        "task_text": section_text,
                        "classification_text": section_text,
                        "test_path": test_path,
                        "test_url": file_url(test_path, page),
                        "barem_path": barem_path,
                        "barem_url": file_url(barem_path) if barem_path else "",
                    }
                )

            if subject in {"I", "II"}:
                tasks.extend(
                    item_tasks_from_subject(
                        paper.paper_id,
                        subject,
                        full_text[start:end],
                        start,
                        offsets,
                        test_path,
                        barem_path,
                    )
                )
    return paper_rows, tasks


def teacher_layout_text() -> str:
    return "\n".join(
        (page.extract_text(extraction_mode="layout") or "")
        for page in PdfReader(str(TEACHER_PDF)).pages
    )


def parse_teacher_bullets() -> list[dict[str, object]]:
    text = teacher_layout_text()
    (DATA_DIR / "teacher_table_layout.txt").write_text(text, encoding="utf-8")
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*(\d{1,2})\s{2,}", line)
        if match:
            starts.append((index, int(match.group(1))))
    starts.append((len(lines), 999))

    rows: list[dict[str, object]] = []
    bullet = chr(9679)
    for (start, topic_id), (end, _) in zip(starts, starts[1:]):
        if topic_id > 26:
            continue
        right_column = " ".join(line[90:].strip() for line in lines[start:end] if len(line) > 90)
        parts = [clean_text(part) for part in right_column.split(bullet)[1:]]
        for part in parts:
            parsed = parse_teacher_reference(topic_id, part)
            rows.extend(parsed)
    return rows


def parse_teacher_reference(topic_id: int, raw: str) -> list[dict[str, object]]:
    ref, _, description = raw.partition("–")
    if not description:
        ref, _, description = raw.partition("-")
    match = re.match(r"\s*(20\d{2}),\s*([^:]+):\s*(.+)$", ref.strip())
    if not match:
        return []
    year = int(match.group(1))
    session_raw = match.group(2).strip()
    item_raw = match.group(3).strip()
    variant = ""
    variant_match = re.search(r"\((Test\s*[12])\)", session_raw, re.IGNORECASE)
    if variant_match:
        variant = re.sub(r"\s+", " ", variant_match.group(1).title())
        session_raw = re.sub(r"\s*\(Test\s*[12]\)", "", session_raw, flags=re.IGNORECASE).strip()
    targets = task_refs_from_teacher_item(item_raw)
    rows = []
    for task_ref in targets:
        rows.append(
            {
                "topic_id": topic_id,
                "year": year,
                "session_raw": session_raw,
                "variant": variant,
                "task_ref": task_ref,
                "raw_reference": raw,
                "teacher_description": description.strip(),
            }
        )
    return rows


def task_refs_from_teacher_item(value: str) -> list[str]:
    normalized = norm(value).replace("subiectul al ii-lea", "subiectul ii")
    refs: list[str] = []
    if "subiectul iii" in normalized or re.search(r"\bitem\s+iii\b", normalized):
        refs.append("III.essay")
    if "subiectul ii" in normalized:
        refs.append("II.all")
    for subject, item in re.findall(r"itemi?\s+([ivx]+)\.?\s*(\d+)", normalized):
        roman = subject.upper()
        if roman == "III":
            refs.append("III.essay")
        else:
            refs.append(f"{roman}.{item}")
    for item in re.findall(r"itemi?\s+(\d+)", normalized):
        if "subiectul iii" in normalized:
            refs.append("III.essay")
        elif "subiectul ii" in normalized or "ii." in normalized:
            refs.append(f"II.{item}")
        else:
            refs.append(f"I.{item}")
    if not refs and "subiectul i" in normalized:
        refs.append("I.all")
    deduped: list[str] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    return deduped or ["unparsed"]


def match_paper_id(row: dict[str, object], paper_rows: list[dict[str, object]]) -> str:
    wanted_session = norm(str(row["session_raw"]))
    wanted_variant = norm(str(row["variant"]))
    candidates = [paper for paper in paper_rows if int(paper["year"]) == int(row["year"])]
    for paper in candidates:
        paper_session = norm(str(paper["session"]))
        if wanted_session in paper_session or paper_session in wanted_session:
            if wanted_variant and norm(str(paper["variant"])) != wanted_variant:
                continue
            return str(paper["paper_id"])
    return ""


def seed_tags_from_teacher(
    teacher_rows: list[dict[str, object]],
    paper_rows: list[dict[str, object]],
    task_ids: set[str],
) -> list[dict[str, object]]:
    tags: list[dict[str, object]] = []
    for row in teacher_rows:
        paper_id = match_paper_id(row, paper_rows)
        if not paper_id:
            row["paper_id"] = ""
            row["matched_task_id"] = ""
            continue
        row["paper_id"] = paper_id
        task_ref = str(row["task_ref"])
        task_id = f"{paper_id}-{slug(task_ref)}"
        if task_id not in task_ids and task_ref.startswith("II."):
            task_id = f"{paper_id}-ii-all"
        if task_id not in task_ids:
            row["matched_task_id"] = ""
            continue
        row["matched_task_id"] = task_id
        tags.append(
            {
                "task_id": task_id,
                "topic_id": row["topic_id"],
                "source": "teacher_demo",
                "confidence": "teacher",
                "score": 1000,
                "matched_keywords": "",
                "note": row["teacher_description"],
            }
        )
    return tags


def add_teacher_placeholder_tasks(
    teacher_rows: list[dict[str, object]],
    paper_rows: list[dict[str, object]],
    tasks: list[dict[str, object]],
) -> None:
    task_ids = {str(task["task_id"]) for task in tasks}
    papers_by_id = {str(paper["paper_id"]): paper for paper in paper_rows}
    for row in teacher_rows:
        paper_id = match_paper_id(row, paper_rows)
        if not paper_id:
            continue
        task_ref = str(row["task_ref"])
        task_id = f"{paper_id}-{slug(task_ref)}"
        if task_id in task_ids:
            continue
        if task_ref.startswith("II.") and f"{paper_id}-ii-all" in task_ids:
            continue
        paper = papers_by_id[paper_id]
        subject, _, item = task_ref.partition(".")
        placeholder = {
            "task_id": task_id,
            "paper_id": paper_id,
            "year": paper["year"],
            "session": paper["session"],
            "variant": paper["variant"],
            "task_ref": task_ref,
            "subject": subject,
            "item": item or "all",
            "task_level": "teacher_reference",
            "page": 1,
            "task_text": f"{row['raw_reference']} {row['teacher_description']}".strip(),
            "classification_text": f"{row['raw_reference']} {row['teacher_description']}".strip(),
            "test_path": paper["test_path"],
            "test_url": file_url(str(paper["test_path"]), 1),
            "barem_path": paper["barem_path"],
            "barem_url": file_url(str(paper["barem_path"])) if paper["barem_path"] else "",
        }
        tasks.append(placeholder)
        task_ids.add(task_id)


def auto_tags(tasks: list[dict[str, object]], existing_pairs: set[tuple[str, str]]) -> list[dict[str, object]]:
    tags: list[dict[str, object]] = []
    for task in tasks:
        scored = []
        text = str(task["classification_text"])
        for topic in TOPICS:
            score, hits = score_topic(text, int(topic["topic_id"]))
            if score >= 4:
                scored.append((score, int(topic["topic_id"]), hits))
        scored.sort(reverse=True)
        for score, topic_id, hits in scored[:3]:
            pair = (str(task["task_id"]), str(topic_id))
            if pair in existing_pairs:
                continue
            tags.append(
                {
                    "task_id": task["task_id"],
                    "topic_id": topic_id,
                    "source": "auto_suggestion",
                    "confidence": "medium" if score < 7 else "high",
                    "score": score,
                    "matched_keywords": "; ".join(hits),
                    "note": "",
                }
            )
    return tags


def build_html(papers: list[dict[str, object]], tasks: list[dict[str, object]], tags: list[dict[str, object]]) -> None:
    payload = {"topics": TOPICS, "papers": papers, "tasks": tasks, "tags": tags}
    json_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Navigator istorie clasa a 9-a</title>
  <style>
    :root {{ --bg:#f6f7f3; --panel:#fff; --ink:#1f2933; --muted:#667085; --line:#d8ded4; --accent:#176b64; --accent-soft:#e4f0ed; --teacher:#12613c; --auto:#8a5a16; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial, Helvetica, sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ height:64px; padding:14px 20px; border-bottom:1px solid var(--line); background:#fff; display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    h1 {{ margin:0; font-size:20px; letter-spacing:0; }}
    .layout {{ display:grid; grid-template-columns:minmax(280px,380px) 1fr; min-height:calc(100vh - 64px); }}
    aside {{ padding:14px; border-right:1px solid var(--line); background:#fbfcfa; max-height:calc(100vh - 64px); overflow:auto; }}
    main {{ padding:18px; max-height:calc(100vh - 64px); overflow:auto; }}
    input, select {{ width:100%; border:1px solid var(--line); border-radius:6px; padding:9px 10px; font:inherit; background:#fff; color:var(--ink); }}
    .topic-list {{ display:grid; gap:8px; margin-top:12px; }}
    .topic {{ border:1px solid var(--line); border-radius:6px; background:#fff; padding:10px; text-align:left; cursor:pointer; }}
    .topic.active {{ border-color:var(--accent); background:var(--accent-soft); }}
    .topic strong {{ display:block; font-size:14px; line-height:1.25; }}
    .meta {{ color:var(--muted); font-size:12px; line-height:1.4; }}
    .filters {{ display:grid; grid-template-columns:1fr 150px 180px 160px; gap:10px; margin-bottom:14px; }}
    .summary {{ display:flex; justify-content:space-between; gap:16px; margin-bottom:12px; }}
    h2 {{ margin:0; font-size:22px; line-height:1.25; letter-spacing:0; }}
    a {{ color:var(--accent); text-underline-offset:2px; }}
    .links {{ display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; font-size:12px; }}
    .task-list {{ display:grid; gap:10px; }}
    .task {{ border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:12px; display:grid; gap:8px; }}
    .task-head {{ display:flex; justify-content:space-between; gap:12px; }}
    .badge {{ border:1px solid var(--line); border-radius:999px; padding:3px 8px; font-size:12px; background:#fff; white-space:nowrap; }}
    .text {{ font-size:14px; line-height:1.45; max-height:220px; overflow:auto; }}
    .tagline {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .tag {{ border-radius:999px; padding:3px 8px; font-size:12px; }}
    .tag.teacher {{ background:#e3f2e9; color:var(--teacher); }}
    .tag.auto {{ background:#f5efe4; color:var(--auto); }}
    .empty {{ border:1px dashed var(--line); border-radius:8px; padding:24px; color:var(--muted); background:#fff; }}
    @media (max-width:850px) {{ .layout {{ grid-template-columns:1fr; }} aside, main {{ max-height:none; }} aside {{ border-right:0; border-bottom:1px solid var(--line); }} .filters {{ grid-template-columns:1fr; }} .summary {{ display:grid; }} .links {{ justify-content:flex-start; }} }}
  </style>
</head>
<body>
  <header><h1>Navigator istorie clasa a 9-a</h1><div id="meta" class="meta"></div></header>
  <div class="layout">
    <aside><input id="topicSearch" type="search" placeholder="Caută tema"><div id="topicList" class="topic-list"></div></aside>
    <main>
      <div class="filters">
        <input id="taskSearch" type="search" placeholder="Caută în sarcini">
        <select id="yearFilter"></select>
        <select id="sessionFilter"></select>
        <select id="sourceFilter"><option value="teacher_demo" selected>Doar demo profesor</option><option value="">Demo + sugestii</option><option value="auto_suggestion">Sugestii automate nevalidate</option></select>
      </div>
      <section class="summary"><div><h2 id="activeTitle"></h2><div id="activeMeta" class="meta"></div></div><div id="topicLinks" class="links"></div></section>
      <div id="taskList" class="task-list"></div>
    </main>
  </div>
  <script id="history-data" type="application/json">{json_payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('history-data').textContent);
    const topicsById = new Map(data.topics.map(t => [String(t.topic_id), t]));
    const tagsByTask = new Map();
    const tagsByTopic = new Map();
    for (const tag of data.tags) {{
      const tid = String(tag.topic_id);
      if (!tagsByTask.has(tag.task_id)) tagsByTask.set(tag.task_id, []);
      tagsByTask.get(tag.task_id).push(tag);
      if (!tagsByTopic.has(tid)) tagsByTopic.set(tid, []);
      tagsByTopic.get(tid).push(tag);
    }}
    let activeTopic = '1';
    const topicList = document.getElementById('topicList');
    const taskList = document.getElementById('taskList');
    const topicSearch = document.getElementById('topicSearch');
    const taskSearch = document.getElementById('taskSearch');
    const yearFilter = document.getElementById('yearFilter');
    const sessionFilter = document.getElementById('sessionFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    document.getElementById('meta').textContent = `${{data.papers.length}} teste | ${{data.tasks.length}} sarcini | ${{data.tags.length}} mapări`;
    function options(values, label) {{ return `<option value="">${{label}}</option>` + values.map(v => `<option value="${{v}}">${{v}}</option>`).join(''); }}
    yearFilter.innerHTML = options([...new Set(data.papers.map(p => p.year))].sort((a,b)=>b-a), 'Toți anii');
    sessionFilter.innerHTML = options([...new Set(data.papers.map(p => p.session))].sort(), 'Toate sesiunile');
    function renderTopics() {{
      const q = topicSearch.value.trim().toLowerCase();
      topicList.innerHTML = data.topics.filter(t => !q || t.display_title.toLowerCase().includes(q) || String(t.topic_id) === q).map(t => {{
        const all = tagsByTopic.get(String(t.topic_id)) || [];
        const teacher = all.filter(x => x.source === 'teacher_demo').length;
        return `<button class="topic ${{String(t.topic_id)===activeTopic?'active':''}}" data-topic="${{t.topic_id}}"><strong>${{t.topic_id}}. ${{t.display_title}}</strong><span class="meta">${{teacher}} demo profesor · ${{all.length}} total</span></button>`;
      }}).join('');
      for (const button of topicList.querySelectorAll('button')) button.addEventListener('click', () => {{ activeTopic = button.dataset.topic; renderTopics(); renderTasks(); }});
    }}
    function link(label, href) {{ return href ? `<a href="${{href}}" target="_blank" rel="noreferrer">${{label}}</a>` : ''; }}
    function renderTasks() {{
      const topic = topicsById.get(activeTopic);
      const q = taskSearch.value.trim().toLowerCase();
      const year = yearFilter.value;
      const session = sessionFilter.value;
      const source = sourceFilter.value;
      const topicTags = (tagsByTopic.get(activeTopic) || []).filter(tag => !source || tag.source === source);
      const taskIds = new Set(topicTags.map(t => t.task_id));
      document.getElementById('activeTitle').textContent = `${{topic.topic_id}}. ${{topic.display_title}}`;
      document.getElementById('activeMeta').textContent = `${{topicTags.filter(t=>t.source==='teacher_demo').length}} mapări din demo profesor · ${{topicTags.length}} total în filtrul curent`;
      document.getElementById('topicLinks').innerHTML = [link('Test grilă', topic.quiz_link), link('NotebookLM', topic.notebook_link), link('Document', topic.doc_link)].filter(Boolean).join('');
      const rows = data.tasks.filter(task => taskIds.has(task.task_id)).filter(task => !q || task.task_text.toLowerCase().includes(q)).filter(task => !year || String(task.year || data.papers.find(p=>p.paper_id===task.paper_id)?.year) === year).filter(task => !session || data.papers.find(p=>p.paper_id===task.paper_id)?.session === session);
      const paperById = new Map(data.papers.map(p => [p.paper_id, p]));
      rows.sort((a,b) => (paperById.get(b.paper_id).year - paperById.get(a.paper_id).year) || a.task_ref.localeCompare(b.task_ref));
      if (!rows.length) {{ taskList.innerHTML = '<div class="empty">Nu există sarcini pentru filtrul curent.</div>'; return; }}
      taskList.innerHTML = rows.map(task => {{
        const paper = paperById.get(task.paper_id);
        const tags = (tagsByTask.get(task.task_id)||[]).filter(tag => String(tag.topic_id)===activeTopic || !source).sort((a,b)=>b.score-a.score);
        const tagHtml = tags.map(tag => `<span class="tag ${{tag.source==='teacher_demo'?'teacher':'auto'}}">${{tag.source==='teacher_demo'?'demo profesor':'sugestie'}} · tema ${{tag.topic_id}}</span>`).join('');
        const variant = paper.variant ? ` · ${{paper.variant}}` : '';
        const note = tags.find(t => String(t.topic_id)===activeTopic)?.note || '';
        return `<article class="task"><div class="task-head"><div><strong>${{paper.year}} · ${{paper.session}}${{variant}}</strong><div class="meta">Referință ${{task.task_ref}} · ${{task.task_level}} · pagina ${{task.page}}</div></div><span class="badge">${{task.task_ref}}</span></div>${{note ? `<div class="meta"><strong>Demo:</strong> ${{note}}</div>` : ''}}<div class="text">${{task.task_text}}</div><div class="tagline">${{tagHtml}}</div><div class="links"><a href="${{task.test_url}}" target="_blank" rel="noreferrer">Test PDF</a>${{task.barem_url ? `<a href="${{task.barem_url}}" target="_blank" rel="noreferrer">Barem PDF</a>` : ''}}</div></article>`;
      }}).join('');
    }}
    topicSearch.addEventListener('input', renderTopics); taskSearch.addEventListener('input', renderTasks); yearFilter.addEventListener('change', renderTasks); sessionFilter.addEventListener('change', renderTasks); sourceFilter.addEventListener('change', renderTasks);
    renderTopics(); renderTasks();
  </script>
</body>
</html>"""
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SITE_DIR.mkdir(exist_ok=True)
    papers, tasks = extract_tasks()
    teacher_rows = parse_teacher_bullets()
    add_teacher_placeholder_tasks(teacher_rows, papers, tasks)
    task_ids = {str(task["task_id"]) for task in tasks}
    teacher_tags = seed_tags_from_teacher(teacher_rows, papers, task_ids)
    pairs = {(str(tag["task_id"]), str(tag["topic_id"])) for tag in teacher_tags}
    tags = teacher_tags + auto_tags(tasks, pairs)
    for task in tasks:
        paper = next(p for p in papers if p["paper_id"] == task["paper_id"])
        task["year"] = paper["year"]
        task["session"] = paper["session"]
        task["variant"] = paper["variant"]
    write_csv(DATA_DIR / "topics.csv", TOPICS, ["topic_id", "display_title", "quiz_link", "notebook_link", "doc_link"])
    write_csv(DATA_DIR / "papers.csv", papers, ["paper_id", "year", "session", "variant", "test_path", "barem_path", "page_count"])
    write_csv(DATA_DIR / "tasks.csv", tasks, ["task_id", "paper_id", "year", "session", "variant", "task_ref", "subject", "item", "task_level", "page", "task_text", "test_path", "test_url", "barem_path", "barem_url"])
    write_csv(DATA_DIR / "teacher_demo_mappings.csv", teacher_rows, ["topic_id", "year", "session_raw", "variant", "task_ref", "paper_id", "matched_task_id", "raw_reference", "teacher_description"])
    write_csv(DATA_DIR / "task_topics.csv", tags, ["task_id", "topic_id", "source", "confidence", "score", "matched_keywords", "note"])
    build_html(papers, tasks, tags)
    matched = sum(1 for row in teacher_rows if row.get("matched_task_id"))
    print(f"papers={len(papers)} tasks={len(tasks)} teacher_refs={len(teacher_rows)} teacher_matched={matched} tags={len(tags)}")
    print(f"wrote {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
