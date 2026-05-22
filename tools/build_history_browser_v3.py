from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

from build_history_browser import (
    DATA_DIR,
    EXAM_ROOT,
    ROOT,
    SITE_DIR,
    TOPICS,
    clean_text,
    norm,
    question_regex,
    rel_path,
    score_topic,
    session_label,
    slug,
    strip_diacritics,
    variant_from_name,
    write_csv,
)
from pypdf import PdfReader


REVIEW_PATH = DATA_DIR / "reviewed_task_topics.csv"
CLASS12_REVIEW_PATH = DATA_DIR / "reviewed_task_topics_class12.csv"
CLASS12_MANUAL_TASKS_PATH = DATA_DIR / "manual_tasks_class12.csv"
PDF_SITE_DIR = SITE_DIR / "pdfs"
CLASS12_TOPIC_PDF = ROOT / "!Tabel linkuri istorie NLM și DOCS.pdf"
CLASS12_EXAM_ROOT = ROOT / "!Teste clasa 12 2016 - 2026"
CLASS_9_ID = "9"
CLASS_12_ID = "12"


TASK_FIELDS = ["class_id", "task_id", "paper_id", "year", "session", "variant", "task_ref", "subject", "item", "task_level", "page", "task_text", "test_path", "test_url"]


CLASSES = [
    {"class_id": CLASS_9_ID, "label": "Clasa a 9-a", "description": "Examen gimnazial"},
    {"class_id": CLASS_12_ID, "label": "Clasa a 12-a", "description": "BAC"},
]


EPOCHS = [
    {"class_id": CLASS_9_ID, "epoch_id": "all", "label": "Toate temele", "sort_order": 0},
    {"class_id": CLASS_12_ID, "epoch_id": "antica", "label": "Epoca antică", "sort_order": 1},
    {"class_id": CLASS_12_ID, "epoch_id": "medievala", "label": "Epoca medievală", "sort_order": 2},
    {"class_id": CLASS_12_ID, "epoch_id": "moderna", "label": "Epoca modernă", "sort_order": 3},
    {"class_id": CLASS_12_ID, "epoch_id": "contemporana", "label": "Epoca contemporană", "sort_order": 4},
]


CLASS12_RECYCLED_CLASS9_LINKS = {
    # BAC contemporary topics that substantially overlap with the class 9 contemporary program.
    "contemporana-1": [1],
    "contemporana-2": [4],
    "contemporana-3": [2],
    "contemporana-4": [3],
    "contemporana-5": [4],
    "contemporana-6": [3, 4],
    "contemporana-7": [11],
    "contemporana-8": [12],
    "contemporana-9": [12],
    "contemporana-10": [6, 7],
    "contemporana-11": [9],
    "contemporana-12": [5],
    "contemporana-13": [13, 14],
    "contemporana-14": [15, 16],
    "contemporana-15": [16],
    "contemporana-16": [15, 21],
    "contemporana-17": [17],
    "contemporana-19": [19],
    "contemporana-20": [20, 21],
    "contemporana-21": [20],
    "contemporana-22": [24],
    "contemporana-23": [18],
    "contemporana-24": [22],
    "contemporana-25": [23],
    "contemporana-26": [26],
    "contemporana-27": [25],
    "contemporana-28": [26],
}


def site_pdf_url(paper_id: object, page: int | None = None) -> str:
    url = f"pdfs/{paper_id}.pdf"
    if page:
        url += f"#page={page}"
    return url


def topic_uid(class_id: str, topic_id: object) -> str:
    return f"{class_id}-{topic_id}"


def class9_topics() -> list[dict[str, object]]:
    topics: list[dict[str, object]] = []
    for topic in TOPICS:
        topic_id = str(topic["topic_id"])
        topics.append(
            {
                "class_id": CLASS_9_ID,
                "epoch_id": "all",
                "topic_id": topic_id,
                "topic_number": topic_id,
                "topic_uid": topic_uid(CLASS_9_ID, topic_id),
                "display_title": topic["display_title"],
                "quiz_link": topic.get("quiz_link", ""),
                "notebook_link": topic.get("notebook_link", ""),
                "doc_link": topic.get("doc_link", ""),
                "doc_links": [topic["doc_link"]] if topic.get("doc_link") else [],
                "reused_from_class9": "",
                "sort_order": int(topic_id),
                "status": "ready",
            }
        )
    return topics


def compact_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def class12_pdf_text() -> str:
    if not CLASS12_TOPIC_PDF.exists():
        return ""
    return "\n".join((page.extract_text() or "") for page in PdfReader(str(CLASS12_TOPIC_PDF)).pages)


def split_epoch_sections(text: str) -> list[tuple[str, str]]:
    markers = [
        ("antica", r"Epoca\s+antic[ăa]"),
        ("medievala", r"epoca\s+medieval[ăa]"),
        ("moderna", r"Epoca\s+modern[ăa]"),
        ("contemporana", r"Epoca\s+contemporan[ăa]"),
    ]
    found: list[tuple[int, str]] = []
    for epoch_id, pattern in markers:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found.append((match.start(), epoch_id))
    found.sort()
    sections: list[tuple[str, str]] = []
    for index, (start, epoch_id) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(text)
        sections.append((epoch_id, text[start:end]))
    return sections


def numbered_topic_spans(section: str) -> list[tuple[int, int, int]]:
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    expected = 1
    while expected < 120:
        match = re.search(rf"(?<![\w/]){expected}\s+(?=[A-ZĂÂÎȘŞȚŢa-zăâîșşțţ„\",,])", section[cursor:])
        if not match:
            break
        start = cursor + match.start()
        spans.append((expected, start, 0))
        cursor = start + len(str(expected)) + 1
        expected += 1
    completed: list[tuple[int, int, int]] = []
    for index, (number, start, _) in enumerate(spans):
        end = spans[index + 1][1] if index + 1 < len(spans) else len(section)
        completed.append((number, start, end))
    return completed


def topic_title_from_row(row_text: str, number: int) -> str:
    row = compact_space(row_text)
    row = re.sub(rf"^{number}\s+", "", row)
    first_url = re.search(r"https?://", row)
    title_part = row[: first_url.start()] if first_url else row
    title_part = re.sub(r"\b(?:A1|A2|Studio|Test\s+gril[ăa](?:\s+20\s+întreb[ăa]ri)?|Test\s+grila(?:\s+20\s+întrebări)?)\s*:", " ", title_part, flags=re.IGNORECASE)
    title_part = re.sub(r"\b(?:Link\s+în\s+NLM|Nr|Tema\s+din\s+programul\s+BAC)\b", " ", title_part, flags=re.IGNORECASE)
    return compact_space(title_part).strip(" -–:")


def links_from_row(row_text: str) -> tuple[list[str], list[str], list[str]]:
    urls = re.findall(r"https?://[^\s]+", row_text)
    clean_urls = [url.rstrip(".,;)") for url in urls]
    docs = [url for url in clean_urls if "docs.google.com/document" in url]
    notebooks = [url for url in clean_urls if "notebooklm.google.com/notebook" in url]
    forms = [url for url in clean_urls if "forms.gle" in url or "docs.google.com/forms" in url]
    return docs, notebooks, forms


def class12_topics() -> list[dict[str, object]]:
    text = class12_pdf_text()
    if not text:
        return []
    topics: list[dict[str, object]] = []
    global_order = 1
    for epoch_id, section in split_epoch_sections(text):
        for number, start, end in numbered_topic_spans(section):
            row = section[start:end]
            title = topic_title_from_row(row, number)
            if not title or len(title) < 4:
                continue
            docs, notebooks, forms = links_from_row(row)
            local_id = f"{epoch_id}-{number}"
            topics.append(
                {
                    "class_id": CLASS_12_ID,
                    "epoch_id": epoch_id,
                    "topic_id": local_id,
                    "topic_number": number,
                    "topic_uid": topic_uid(CLASS_12_ID, local_id),
                    "display_title": title,
                    "quiz_link": forms[0] if forms else "",
                    "notebook_link": notebooks[0] if notebooks else "",
                    "doc_link": docs[0] if docs else "",
                    "doc_links": docs,
                    "reused_from_class9": "",
                    "sort_order": global_order,
                    "status": "ready" if (docs or notebooks or forms) else "links_pending",
                }
            )
            global_order += 1
    return topics


def apply_recycled_class9_links(topics: list[dict[str, object]]) -> list[dict[str, object]]:
    class9_by_number = {
        int(topic["topic_number"]): topic
        for topic in topics
        if topic["class_id"] == CLASS_9_ID
    }
    for topic in topics:
        if topic["class_id"] != CLASS_12_ID:
            continue
        source_numbers = CLASS12_RECYCLED_CLASS9_LINKS.get(str(topic["topic_id"]), [])
        if not source_numbers:
            continue
        source_topics = [class9_by_number[number] for number in source_numbers if number in class9_by_number]
        if not source_topics:
            continue
        docs: list[str] = list(topic.get("doc_links") or [])
        notebooks: list[str] = []
        quizzes: list[str] = []
        for source in source_topics:
            if source.get("doc_link") and source["doc_link"] not in docs:
                docs.append(str(source["doc_link"]))
            if source.get("notebook_link"):
                notebooks.append(str(source["notebook_link"]))
            if source.get("quiz_link"):
                quizzes.append(str(source["quiz_link"]))
        if not topic.get("doc_link") and docs:
            topic["doc_link"] = docs[0]
        if not topic.get("notebook_link") and notebooks:
            topic["notebook_link"] = notebooks[0]
        if not topic.get("quiz_link") and quizzes:
            topic["quiz_link"] = quizzes[0]
        topic["doc_links"] = docs
        topic["reused_from_class9"] = ", ".join(str(number) for number in source_numbers)
        if topic.get("doc_link") or topic.get("notebook_link") or topic.get("quiz_link"):
            topic["status"] = "reused_class9_links"
    return topics


def all_topics() -> list[dict[str, object]]:
    return apply_recycled_class9_links(class9_topics() + class12_topics())


def copy_reviewed_pdfs(
    papers: list[dict[str, object]],
    tasks: list[dict[str, object]],
    reviewed: list[dict[str, object]],
) -> None:
    task_by_id = {str(task["task_id"]): task for task in tasks}
    paper_by_id = {str(paper["paper_id"]): paper for paper in papers}
    used_paper_ids = {
        str(task_by_id[str(tag["task_id"])]["paper_id"])
        for tag in reviewed
        if str(tag["task_id"]) in task_by_id
    }
    if PDF_SITE_DIR.exists():
        for pdf in PDF_SITE_DIR.glob("*.pdf"):
            pdf.unlink()
    PDF_SITE_DIR.mkdir(parents=True, exist_ok=True)
    for paper_id in sorted(used_paper_ids):
        paper = paper_by_id.get(paper_id)
        if not paper:
            continue
        shutil.copy2(ROOT / str(paper["test_path"]), PDF_SITE_DIR / f"{paper_id}.pdf")


def discover_test_papers() -> list[dict[str, object]]:
    papers: list[dict[str, object]] = []
    for path in sorted(EXAM_ROOT.rglob("*.pdf")):
        lower = path.name.lower()
        if "barem" in lower or "borderou" in lower or "test" not in lower:
            continue
        try:
            year = int(next(part for part in path.parts if re.fullmatch(r"20\d{2}", part)))
        except StopIteration:
            continue
        session = session_label(path.parent.name)
        variant = variant_from_name(path)
        paper_id = slug(f"{year} {session} {variant or 'test'}")
        try:
            page_count = len(PdfReader(str(path)).pages)
        except Exception:
            page_count = 0
        papers.append(
            {
                "class_id": CLASS_9_ID,
                "paper_id": paper_id,
                "year": year,
                "session": session,
                "variant": variant,
                "path": path,
                "test_path": rel_path(path),
                "page_count": page_count,
            }
        )
    if CLASS12_EXAM_ROOT.exists():
        for path in sorted(CLASS12_EXAM_ROOT.rglob("*.pdf")):
            lower = path.name.lower()
            if "barem" in lower or "borderou" in lower or "test" not in lower:
                continue
            try:
                year = int(next(part for part in path.parts if re.fullmatch(r"20\d{2}", part)))
            except StopIteration:
                continue
            relative_parts = [part.lower() for part in path.relative_to(CLASS12_EXAM_ROOT).parts]
            is_real = any("real" in part for part in relative_parts)
            profile_slug = "profil real" if is_real else "profil umanistic"
            profile_label = "Profil real" if is_real else "Profil umanistic"
            session_part = path.parent.name
            if norm(session_part) == "real" and len(path.parents) > 1:
                session_part = path.parent.parent.name
            session = session_label(session_part)
            test_variant = variant_from_name(path)
            variant = f"{profile_label} · {test_variant}" if test_variant else profile_label
            paper_id = slug(f"bac {year} {profile_slug} {session} {test_variant or 'test'}")
            try:
                page_count = len(PdfReader(str(path)).pages)
            except Exception:
                page_count = 0
            papers.append(
                {
                    "class_id": CLASS_12_ID,
                    "paper_id": paper_id,
                    "year": year,
                    "session": session,
                    "variant": variant,
                    "path": path,
                    "test_path": rel_path(path),
                    "page_count": page_count,
                }
            )
    return papers


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
        (r"SUBIECTUL\s+(?:al\s+)?IV(?:-lea)?\b", "IV"),
        (r"SUBIECTUL\s+(?:al\s+)?V(?:-lea)?\b", "V"),
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


def make_task(
    paper: dict[str, object],
    task_ref: str,
    subject: str,
    item: str,
    task_level: str,
    page: int,
    task_text: str,
) -> dict[str, object]:
    test_path = str(paper["test_path"])
    return {
        "task_id": f"{paper['paper_id']}-{slug(task_ref)}",
        "class_id": paper["class_id"],
        "paper_id": paper["paper_id"],
        "year": paper["year"],
        "session": paper["session"],
        "variant": paper["variant"],
        "task_ref": task_ref,
        "subject": subject,
        "item": item,
        "task_level": task_level,
        "page": page,
        "task_text": task_text,
        "classification_text": task_text,
        "test_path": test_path,
        "test_url": site_pdf_url(paper["paper_id"], page),
    }


def item_tasks_from_subject(
    paper: dict[str, object],
    subject: str,
    subject_text: str,
    subject_start: int,
    offsets: list[tuple[int, int]],
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
        page = page_for_offset(offsets, subject_start + start)
        task_ref = f"{subject}.{item}"
        tasks.append(make_task(paper, task_ref, subject, item, "item", page, text))
    return tasks


def extract_tasks() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    paper_objects = discover_test_papers()
    papers: list[dict[str, object]] = []
    tasks: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []

    for paper_obj in paper_objects:
        paper = {
            "class_id": paper_obj["class_id"],
            "paper_id": paper_obj["paper_id"],
            "year": paper_obj["year"],
            "session": paper_obj["session"],
            "variant": paper_obj["variant"],
            "test_path": paper_obj["test_path"],
            "page_count": paper_obj["page_count"],
        }
        papers.append(paper)
        pages = extract_pdf_pages(Path(paper_obj["path"]))
        full_text, offsets = page_offsets(pages)
        extracted_chars = len(clean_text(full_text))
        if extracted_chars == 0:
            issues.append(
                {
                    "paper_id": paper_obj["paper_id"],
                    "class_id": paper_obj["class_id"],
                    "year": paper_obj["year"],
                    "session": paper_obj["session"],
                    "variant": paper_obj["variant"],
                    "test_path": paper_obj["test_path"],
                    "issue": "no_extractable_text",
                    "note": "PDF appears image-only or otherwise has no text layer.",
                }
            )
            continue

        spans = subject_spans(full_text)
        if not spans:
            issues.append(
                {
                    "paper_id": paper_obj["paper_id"],
                    "class_id": paper_obj["class_id"],
                    "year": paper_obj["year"],
                    "session": paper_obj["session"],
                    "variant": paper_obj["variant"],
                    "test_path": paper_obj["test_path"],
                    "issue": "no_subject_markers",
                    "note": "Text exists, but SUBIECTUL markers were not found.",
                }
            )
            continue

        for subject, start, end in spans:
            section_text = clean_text(full_text[start:end])
            if len(section_text) < 30:
                continue
            page = page_for_offset(offsets, start)
            class_id = str(paper["class_id"])
            if class_id == CLASS_9_ID and subject == "II":
                tasks.append(make_task(paper, "II.all", "II", "all", "section", page, section_text))
            elif class_id == CLASS_9_ID and subject == "III":
                tasks.append(make_task(paper, "III.essay", "III", "essay", "essay", page, section_text))
            elif class_id == CLASS_12_ID and subject in {"I", "II", "III", "V"}:
                tasks.append(make_task(paper, f"{subject}.all", subject, "all", "section", page, section_text))
            elif class_id == CLASS_12_ID and subject == "IV":
                tasks.append(make_task(paper, "IV.essay", "IV", "essay", "essay", page, section_text))
            if class_id == CLASS_9_ID and subject in {"I", "II"}:
                tasks.extend(item_tasks_from_subject(paper, subject, full_text[start:end], start, offsets))

    return papers, dedupe_tasks(tasks + load_manual_tasks()), issues


def dedupe_tasks(tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {}
    for task in tasks:
        task_id = str(task["task_id"])
        existing = by_id.get(task_id)
        if not existing or len(str(task["task_text"])) > len(str(existing["task_text"])):
            by_id[task_id] = task
    return list(by_id.values())


def load_manual_tasks() -> list[dict[str, object]]:
    if not CLASS12_MANUAL_TASKS_PATH.exists():
        return []
    with CLASS12_MANUAL_TASKS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def ensure_review_template(path: Path) -> None:
    if path.exists():
        return
    write_csv(path, [], ["task_id", "topic_id", "status", "note"])


def load_review_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for class_id, path in ((CLASS_9_ID, REVIEW_PATH), (CLASS_12_ID, CLASS12_REVIEW_PATH)):
        ensure_review_template(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row["class_id"] = class_id
                rows.append(row)
    return rows


def reviewed_tags(review_rows: list[dict[str, str]], task_ids: set[str]) -> tuple[list[dict[str, object]], set[tuple[str, str]]]:
    tags: list[dict[str, object]] = []
    rejected: set[tuple[str, str]] = set()
    for row in review_rows:
        task_id = (row.get("task_id") or "").strip()
        topic_id = (row.get("topic_id") or "").strip()
        class_id = (row.get("class_id") or CLASS_9_ID).strip()
        status = norm(row.get("status") or "approved")
        note = (row.get("note") or "").strip()
        if not task_id or not topic_id:
            continue
        pair = (task_id, topic_id)
        if status in {"reject", "rejected", "remove", "removed"}:
            rejected.add(pair)
            continue
        if task_id in task_ids and status in {"approve", "approved", "manual", "reviewed"}:
            tags.append(
                {
                    "task_id": task_id,
                    "class_id": class_id,
                    "topic_id": topic_id,
                    "topic_uid": topic_uid(class_id, topic_id),
                    "source": "reviewed",
                    "confidence": "reviewed",
                    "score": 1000,
                    "matched_keywords": "",
                    "note": note,
                }
            )
    return tags, rejected


def auto_candidates(tasks: list[dict[str, object]], blocked_pairs: set[tuple[str, str]]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for task in tasks:
        if str(task.get("class_id")) != CLASS_9_ID:
            continue
        scored = []
        for topic in TOPICS:
            score, hits = score_topic(str(task["classification_text"]), int(topic["topic_id"]))
            if score >= 5:
                scored.append((score, int(topic["topic_id"]), hits))
        scored.sort(reverse=True)
        for score, topic_id, hits in scored[:3]:
            pair = (str(task["task_id"]), str(topic_id))
            if pair in blocked_pairs:
                continue
            candidates.append(
                {
                    "task_id": task["task_id"],
                    "class_id": CLASS_9_ID,
                    "topic_id": topic_id,
                    "topic_uid": topic_uid(CLASS_9_ID, topic_id),
                    "source": "candidate",
                    "confidence": "unreviewed",
                    "score": score,
                    "matched_keywords": "; ".join(hits),
                    "note": "",
                }
            )
    return candidates


def build_html(
    papers: list[dict[str, object]],
    tasks: list[dict[str, object]],
    reviewed: list[dict[str, object]],
    candidates: list[dict[str, object]],
    issues: list[dict[str, object]],
) -> None:
    topics = all_topics()
    payload = {
        "classes": CLASSES,
        "epochs": EPOCHS,
        "topics": topics,
        "papers": papers,
        "tasks": tasks,
        "reviewed": reviewed,
        "candidates": candidates,
        "issues": issues,
    }
    json_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Navigator istorie</title>
  <style>
    :root {{
      --bg:#f5f3ff; --surface:#ffffff; --panel:#ffffff; --ink:#182033; --muted:#647084;
      --line:#dfe3f7; --line-strong:#b9c2ee; --accent:#2563eb; --accent-2:#f97316;
      --accent-soft:#eaf0ff; --teal:#0f9f8f; --rose:#e11d48; --violet:#7c3aed;
      --shadow:0 22px 65px rgba(37,99,235,.16);
    }}
    * {{ box-sizing:border-box; }}
    [hidden] {{ display:none !important; }}
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background:
      radial-gradient(circle at 10% -10%, rgba(37,99,235,.18), transparent 32%),
      radial-gradient(circle at 92% 0%, rgba(249,115,22,.16), transparent 28%),
      linear-gradient(135deg,#f7f7ff 0%,#eef9ff 48%,#fff7ed 100%);
      color:var(--ink); letter-spacing:0; }}
    button {{ font:inherit; }}
    button {{ color:inherit; }}
    a {{ color:var(--accent); text-underline-offset:3px; }}
    .shell {{ min-height:100vh; display:grid; grid-template-rows:auto 1fr; }}
    header {{ min-height:68px; padding:14px 22px; background:rgba(255,255,255,.78); border-bottom:1px solid rgba(185,194,238,.7); display:flex; align-items:center; justify-content:space-between; gap:18px; position:sticky; top:0; z-index:5; backdrop-filter:blur(16px); box-shadow:0 10px 34px rgba(37,99,235,.08); }}
    h1 {{ margin:0; font-size:21px; line-height:1.1; letter-spacing:0; }}
    .subtitle {{ margin-top:4px; color:var(--muted); font-size:12px; }}
    .stats {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .pill {{ border:1px solid rgba(37,99,235,.16); border-radius:999px; padding:6px 10px; background:rgba(255,255,255,.76); color:#2d3f63; font-size:12px; white-space:nowrap; box-shadow:0 8px 24px rgba(37,99,235,.08); }}
    .nav-controls {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:0 18px 14px; padding-top:14px; }}
    .seg-btn {{ border:1px solid rgba(37,99,235,.18); border-radius:999px; padding:8px 12px; background:#fff; color:#2d3f63; cursor:pointer; font-size:13px; box-shadow:0 8px 20px rgba(37,99,235,.07); }}
    .seg-btn.active {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
    .epoch-tabs {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .app {{ display:grid; grid-template-columns:320px minmax(0,1fr); min-height:calc(100vh - 68px); }}
    aside {{ border-right:1px solid rgba(185,194,238,.65); background:rgba(255,255,255,.58); padding:16px; overflow:auto; max-height:calc(100vh - 68px); backdrop-filter:blur(12px); }}
    .topic-list {{ display:grid; gap:8px; }}
    .topic {{ width:100%; border:1px solid rgba(185,194,238,.8); border-radius:8px; padding:10px 11px; background:rgba(255,255,255,.86); text-align:left; cursor:pointer; transition:border-color .14s ease, background .14s ease, transform .14s ease, box-shadow .14s ease; }}
    .topic:hover {{ border-color:var(--accent); transform:translateY(-1px); box-shadow:0 12px 28px rgba(37,99,235,.1); }}
    .topic.active {{ border-color:rgba(37,99,235,.55); background:linear-gradient(135deg,#eef4ff,#ecfeff); box-shadow:0 14px 34px rgba(37,99,235,.16); }}
    .topic strong {{ display:block; font-size:13px; line-height:1.3; }}
    .meta {{ color:var(--muted); font-size:12px; line-height:1.45; }}
    main {{ min-width:0; padding:18px; overflow:hidden; }}
    .notice {{ display:flex; gap:10px; align-items:flex-start; border:1px solid #f0d3ac; background:#fff8ed; color:#6b3f12; border-radius:8px; padding:10px 12px; margin-bottom:14px; font-size:13px; line-height:1.35; }}
    .summary {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:14px; }}
    h2 {{ margin:0; font-size:24px; line-height:1.18; letter-spacing:0; }}
    .topic-links {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .topic-links a, .ghost-btn {{ border:1px solid rgba(37,99,235,.18); border-radius:8px; padding:8px 10px; background:#fff; color:#1d4ed8; text-decoration:none; font-size:12px; cursor:pointer; box-shadow:0 8px 20px rgba(37,99,235,.08); }}
    .topic-links a:hover, .ghost-btn:hover {{ border-color:var(--accent); color:#fff; background:var(--accent); }}
    .workspace {{ display:grid; grid-template-columns:minmax(360px,520px) minmax(0,1fr); gap:14px; height:calc(100vh - 166px); min-height:560px; }}
    .results, .viewer {{ min-width:0; border:1px solid rgba(185,194,238,.82); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); overflow:hidden; }}
    .results {{ display:grid; grid-template-rows:auto 1fr; }}
    .result-head {{ padding:12px 14px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:10px; align-items:center; background:linear-gradient(135deg,#ffffff,#eef4ff); }}
    .count {{ color:var(--muted); font-size:12px; }}
    .task-list {{ overflow:auto; padding:10px; display:grid; gap:8px; align-content:start; }}
    .task {{ width:100%; border:1px solid rgba(185,194,238,.86); border-radius:8px; background:#fff; padding:11px; text-align:left; cursor:pointer; display:grid; gap:8px; transition:border-color .14s ease, background .14s ease, transform .14s ease, box-shadow .14s ease; }}
    .task:hover {{ border-color:var(--accent); transform:translateY(-1px); box-shadow:0 14px 30px rgba(37,99,235,.11); }}
    .task.active {{ border-color:rgba(37,99,235,.62); background:linear-gradient(135deg,#eff6ff,#ecfeff); box-shadow:0 16px 36px rgba(37,99,235,.16); }}
    .task-top {{ display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }}
    .task-title {{ font-weight:700; font-size:14px; line-height:1.25; }}
    .badge {{ border:1px solid rgba(37,99,235,.18); border-radius:999px; padding:4px 8px; background:#eef4ff; white-space:nowrap; font-size:12px; color:#1d4ed8; }}
    .task-detail {{ display:flex; gap:6px; flex-wrap:wrap; }}
    .chip {{ border-radius:999px; padding:4px 8px; font-size:11px; background:#f1f5ff; color:#395170; }}
    .chip.reviewed {{ background:#dcfce7; color:#166534; }}
    .chip.candidate {{ background:#ffedd5; color:#9a3412; }}
    .viewer {{ display:grid; grid-template-rows:auto 1fr; background:#111827; }}
    .viewer.empty {{ background:#fff; }}
    .viewer-bar {{ min-height:54px; padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.12); display:flex; justify-content:space-between; gap:12px; align-items:center; color:#fff; }}
    .viewer.empty .viewer-bar {{ color:var(--ink); border-bottom:1px solid var(--line); background:linear-gradient(135deg,#ffffff,#eef4ff); }}
    .viewer-title {{ font-weight:700; font-size:13px; line-height:1.25; }}
    .viewer-meta {{ font-size:12px; color:#c9d1d5; margin-top:2px; }}
    .viewer.empty .viewer-meta {{ color:var(--muted); }}
    .viewer-actions {{ display:flex; gap:8px; align-items:center; }}
    .viewer-actions a, .viewer-actions button {{ border:1px solid rgba(255,255,255,.22); border-radius:8px; padding:7px 9px; background:rgba(255,255,255,.08); color:#fff; text-decoration:none; font-size:12px; cursor:pointer; white-space:nowrap; }}
    .viewer.empty .viewer-actions button {{ border-color:var(--line); background:#fff; color:#33434a; }}
    .viewer-frame-wrap {{ min-height:0; position:relative; }}
    iframe {{ width:100%; height:100%; border:0; background:#3c4448; display:block; }}
    .mobile-pdf {{ display:none; }}
    .empty-state {{ height:100%; min-height:380px; display:grid; place-items:center; padding:24px; color:var(--muted); text-align:center; background:linear-gradient(135deg,#ffffff,#eef4ff 48%,#fff7ed); }}
    .empty-state strong {{ display:block; color:var(--ink); margin-bottom:6px; }}
    .no-results {{ border:1px dashed var(--line-strong); border-radius:8px; padding:22px; color:var(--muted); background:#fff; }}
    @media (max-width:1100px) {{
      .app {{ grid-template-columns:280px minmax(0,1fr); }}
      .workspace {{ grid-template-columns:1fr; height:auto; }}
      .viewer {{ min-height:620px; }}
    }}
    @media (max-width:780px) {{
      .shell {{ display:block; }}
      header {{ min-height:0; padding:10px 14px; position:static; align-items:center; flex-direction:row; }}
      h1 {{ font-size:17px; }}
      .stats {{ display:none; }}
      .nav-controls {{ margin:0; padding:10px; overflow-x:auto; flex-wrap:nowrap; }}
      .seg-btn {{ white-space:nowrap; padding:7px 10px; font-size:12px; }}
      .epoch-tabs {{ flex-wrap:nowrap; }}
      .app {{ grid-template-columns:1fr; }}
      aside {{ max-height:none; border-right:0; border-bottom:1px solid var(--line); padding:10px 10px 8px; overflow:hidden; position:sticky; top:0; z-index:4; }}
      .topic-list {{ display:flex; gap:8px; overflow-x:auto; padding-bottom:4px; scroll-snap-type:x proximity; }}
      .topic {{ min-width:220px; max-width:260px; scroll-snap-align:start; padding:9px 10px; }}
      .topic strong {{ font-size:12px; }}
      main {{ overflow:visible; padding:12px; }}
      .summary {{ display:grid; }}
      h2 {{ font-size:19px; }}
      .topic-links {{ justify-content:flex-start; }}
      .workspace {{ display:block; height:auto; min-height:0; }}
      .results {{ display:block; }}
      .task-list {{ overflow:visible; }}
      .desktop-viewer {{ display:none; }}
      .mobile-pdf {{ display:grid; gap:8px; border:1px solid rgba(37,99,235,.24); border-radius:8px; background:#0f172a; color:#fff; padding:8px; box-shadow:0 16px 34px rgba(15,23,42,.18); }}
      .mobile-pdf-bar {{ display:flex; justify-content:space-between; gap:10px; align-items:center; font-size:12px; }}
      .mobile-pdf-title {{ font-weight:700; line-height:1.25; }}
      .mobile-pdf-actions {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
      .mobile-pdf-actions a, .mobile-pdf-actions button {{ border:1px solid rgba(255,255,255,.28); border-radius:8px; padding:7px 9px; background:rgba(255,255,255,.1); color:#fff; text-decoration:none; font-size:12px; }}
      .mobile-pdf-frame {{ width:100%; height:min(72vh,620px); border:0; border-radius:6px; background:#303840; }}
      .mobile-pdf-note {{ color:#d6e2ff; font-size:12px; line-height:1.35; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Navigator istorie</h1>
      </div>
      <div id="meta" class="stats"></div>
    </header>
    <nav class="nav-controls" aria-label="Selectare clasă și epocă">
      <div id="classTabs" class="epoch-tabs"></div>
      <div id="epochTabs" class="epoch-tabs"></div>
    </nav>
    <div class="app">
      <aside>
        <div id="topicList" class="topic-list"></div>
      </aside>
      <main>
        <section class="summary">
          <div><h2 id="activeTitle"></h2><div id="activeMeta" class="meta"></div></div>
          <div id="topicLinks" class="topic-links"></div>
        </section>
        <section class="workspace" id="workspace">
          <div class="results">
            <div class="result-head"><strong>Teste asociate</strong><span id="resultCount" class="count"></span></div>
            <div id="taskList" class="task-list"></div>
          </div>
          <div id="viewer" class="viewer desktop-viewer empty">
            <div class="viewer-bar">
              <div><div id="viewerTitle" class="viewer-title">Alege un test din listă</div><div id="viewerMeta" class="viewer-meta">PDF-ul se va deschide aici, în aceeași pagină.</div></div>
              <div class="viewer-actions"><button id="closeViewer" type="button">Închide</button><a id="openExternal" href="#" target="_blank" rel="noreferrer" hidden>Deschide separat</a></div>
            </div>
            <div class="viewer-frame-wrap"><div id="viewerEmpty" class="empty-state"><div><strong>Niciun PDF selectat</strong><span>Selectează un rând pentru a deschide testul la pagina relevantă.</span></div></div><iframe id="pdfFrame" title="Vizualizare test PDF" hidden></iframe></div>
          </div>
        </section>
      </main>
    </div>
  </div>
  <script id="history-data" type="application/json">{json_payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('history-data').textContent);
    const classesById = new Map(data.classes.map(c => [String(c.class_id), c]));
    const topicsByUid = new Map(data.topics.map(t => [String(t.topic_uid), t]));
    const paperById = new Map(data.papers.map(p => [p.paper_id, p]));
    const taskById = new Map(data.tasks.map(t => [t.task_id, t]));
    const reviewedByTopic = new Map();
    const candidateByTopic = new Map();
    const tagsByTask = new Map();
    for (const source of [data.reviewed, data.candidates]) {{
      for (const tag of source) {{
        const map = tag.source === 'reviewed' ? reviewedByTopic : candidateByTopic;
        const topic = String(tag.topic_uid || `${{tag.class_id || '9'}}-${{tag.topic_id}}`);
        if (!map.has(topic)) map.set(topic, []);
        map.get(topic).push(tag);
        if (!tagsByTask.has(tag.task_id)) tagsByTask.set(tag.task_id, []);
        tagsByTask.get(tag.task_id).push(tag);
      }}
    }}
    let activeClass = '9';
    let activeEpoch = 'all';
    let activeTopic = String((data.topics.find(t => t.class_id === activeClass && (reviewedByTopic.get(String(t.topic_uid)) || []).length) || data.topics.find(t => t.class_id === activeClass) || data.topics[0]).topic_uid);
    let activeTaskId = '';
    const classTabs = document.getElementById('classTabs');
    const epochTabs = document.getElementById('epochTabs');
    const topicList = document.getElementById('topicList');
    const taskList = document.getElementById('taskList');
    const viewer = document.getElementById('viewer');
    const pdfFrame = document.getElementById('pdfFrame');
    const viewerEmpty = document.getElementById('viewerEmpty');
    const openExternal = document.getElementById('openExternal');
    const mobileQuery = window.matchMedia('(max-width: 780px)');
    function classTopics() {{
      return data.topics
        .filter(t => t.class_id === activeClass && (activeClass !== '12' || t.epoch_id === activeEpoch))
        .sort((a,b) => a.sort_order - b.sort_order);
    }}
    function setDefaultTopic() {{
      const topics = classTopics();
      const mapped = topics.find(t => (reviewedByTopic.get(String(t.topic_uid)) || []).length);
      activeTopic = String((mapped || topics[0] || data.topics[0]).topic_uid);
    }}
    function renderMeta() {{
      const classPapers = data.papers.filter(p => p.class_id === activeClass);
      const classTasks = data.tasks.filter(t => t.class_id === activeClass);
      const classReviewed = data.reviewed.filter(t => t.class_id === activeClass);
      const reviewedTaskCount = new Set(classReviewed.map(tag => tag.task_id)).size;
      const labels = activeClass === '12'
        ? [`${{classTopics().length}} teme`, `${{data.topics.filter(t => t.class_id === activeClass).length}} total teme BAC`, 'mapări în lucru']
        : [`${{classPapers.length}} teste`, `${{classTasks.length}} sarcini`, `${{reviewedTaskCount}} sarcini mapate`, `${{classReviewed.length}} legături tema-test`];
      document.getElementById('meta').innerHTML = labels.map(item => `<span class="pill">${{item}}</span>`).join('');
    }}
    function renderClassTabs() {{
      classTabs.innerHTML = data.classes.map(c => `<button class="seg-btn ${{c.class_id === activeClass ? 'active' : ''}}" type="button" data-class="${{c.class_id}}">${{c.label}}</button>`).join('');
      for (const button of classTabs.querySelectorAll('button')) button.addEventListener('click', () => {{
        activeClass = button.dataset.class;
        activeEpoch = activeClass === '12' ? 'antica' : 'all';
        activeTaskId = '';
        closeViewer();
        setDefaultTopic();
        renderAll();
      }});
    }}
    function renderEpochTabs() {{
      const epochs = data.epochs.filter(e => e.class_id === activeClass).sort((a,b) => a.sort_order - b.sort_order);
      epochTabs.hidden = activeClass !== '12';
      epochTabs.innerHTML = activeClass === '12' ? epochs.map(e => `<button class="seg-btn ${{e.epoch_id === activeEpoch ? 'active' : ''}}" type="button" data-epoch="${{e.epoch_id}}">${{e.label}}</button>`).join('') : '';
      for (const button of epochTabs.querySelectorAll('button')) button.addEventListener('click', () => {{
        activeEpoch = button.dataset.epoch;
        activeTaskId = '';
        closeViewer();
        setDefaultTopic();
        renderAll();
      }});
    }}
    function visibleTagsForTopic(topicUid) {{
      return reviewedByTopic.get(topicUid) || [];
    }}
    function renderTopics() {{
      const topics = classTopics();
      topicList.innerHTML = topics.map(t => {{
        const reviewed = (reviewedByTopic.get(String(t.topic_uid)) || []).length;
        const countLabel = activeClass === '12' ? (reviewed ? `${{reviewed}} teste asociate` : 'fără mapări încă') : `${{reviewed}} teste asociate`;
        return `<button class="topic ${{String(t.topic_uid)===activeTopic?'active':''}}" data-topic="${{t.topic_uid}}"><strong>${{t.topic_number || t.topic_id}}. ${{t.display_title}}</strong><span class="meta">${{countLabel}}</span></button>`;
      }}).join('');
      for (const button of topicList.querySelectorAll('button')) button.addEventListener('click', () => {{
        activeTopic = button.dataset.topic;
        activeTaskId = '';
        closeViewer();
        renderTopics();
        renderTasks();
        document.getElementById('activeTitle').scrollIntoView({{block:'start', behavior:'smooth'}});
      }});
    }}
    function link(label, href) {{ return href ? `<a href="${{href}}" target="_blank" rel="noreferrer">${{label}}</a>` : ''; }}
    function topicTasks() {{
      const tags = visibleTagsForTopic(activeTopic);
      const taskIds = new Set(tags.map(t => t.task_id));
      let rows = data.tasks.filter(task => task.class_id === activeClass && taskIds.has(task.task_id));
      rows.sort((a,b) => (paperById.get(b.paper_id).year - paperById.get(a.paper_id).year) || a.task_ref.localeCompare(b.task_ref));
      return rows;
    }}
    function renderTasks() {{
      const topic = topicsByUid.get(activeTopic);
      document.getElementById('activeTitle').textContent = `${{topic.topic_number || topic.topic_id}}. ${{topic.display_title}}`;
      const reviewedCount = (reviewedByTopic.get(activeTopic)||[]).length;
      document.getElementById('activeMeta').textContent = activeClass === '12'
        ? `${{data.epochs.find(e => e.epoch_id === topic.epoch_id && e.class_id === topic.class_id)?.label || ''}} · ${{reviewedCount ? reviewedCount + ' teste asociate' : 'mapările cu testele vor fi adăugate ulterior'}}`
        : `${{reviewedCount}} teste asociate, revizuite manual`;
      const docLinks = [...new Set(topic.doc_links && topic.doc_links.length ? topic.doc_links : (topic.doc_link ? [topic.doc_link] : []))];
      const docHtml = docLinks.map((href, index) => link(docLinks.length > 1 ? `Sinteza A2 ${{index + 1}}` : 'Sinteza A2', href));
      document.getElementById('topicLinks').innerHTML = [link('Test grila', topic.quiz_link), link('NotebookLM', topic.notebook_link), ...docHtml].filter(Boolean).join('') || '<span class="meta">Linkurile pentru această temă vor fi completate ulterior.</span>';
      const rows = topicTasks();
      if (activeTaskId && !rows.some(task => task.task_id === activeTaskId)) closeViewer();
      document.getElementById('resultCount').textContent = rows.length ? `${{rows.length}} rezultate` : '0 rezultate';
      if (!rows.length) {{
        taskList.innerHTML = `<div class="no-results">${{activeClass === '12' ? 'Tema este în catalog, dar sarcinile BAC asociate nu au fost mapate încă.' : 'Nu exista sarcini asociate acestei teme.'}}</div>`;
        return;
      }}
      taskList.innerHTML = rows.map(task => {{
        const paper = paperById.get(task.paper_id);
        const relevantTags = (tagsByTask.get(task.task_id)||[]).filter(tag => tag.source === 'reviewed' && String(tag.topic_uid) === activeTopic);
        const tagHtml = relevantTags.map(tag => `<span class="chip reviewed">tema ${{tag.topic_id}}</span>`).join('');
        const variant = paper.variant ? ` · ${{paper.variant}}` : '';
        return `<button class="task ${{task.task_id === activeTaskId ? 'active' : ''}}" data-task="${{task.task_id}}">
          <div class="task-top"><div><div class="task-title">${{paper.year}} · ${{paper.session}}${{variant}}</div><div class="meta">Pagina ${{task.page}} · ${{task.task_level === 'section' ? 'Subiectul II' : task.task_level === 'essay' ? 'Eseu' : 'Item'}}</div></div><span class="badge">${{task.task_ref}}</span></div>
          <div class="task-detail">${{tagHtml}}<span class="chip">PDF</span></div>
        </button>`;
      }}).join('');
      for (const button of taskList.querySelectorAll('.task')) button.addEventListener('click', () => openTask(button.dataset.task));
      if (!activeTaskId && !mobileQuery.matches) openTask(rows[0].task_id);
    }}
    function removeMobilePdf() {{
      document.querySelectorAll('.mobile-pdf').forEach(el => el.remove());
    }}
    function createMobilePdf(task, paper, variant) {{
      removeMobilePdf();
      const activeButton = [...taskList.querySelectorAll('.task')].find(el => el.dataset.task === task.task_id);
      if (!activeButton) return;
      const panel = document.createElement('div');
      panel.className = 'mobile-pdf';
      panel.innerHTML = `
        <div class="mobile-pdf-bar">
          <div class="mobile-pdf-title">${{paper.year}} · ${{paper.session}}${{variant}} · ${{task.task_ref}}</div>
          <div class="mobile-pdf-actions">
            <button type="button" data-close-mobile>Închide</button>
            <a href="${{task.test_url}}" target="_blank" rel="noreferrer">Deschide PDF</a>
          </div>
        </div>
        <iframe class="mobile-pdf-frame" title="Test PDF" src="${{task.test_url}}"></iframe>
        <div class="mobile-pdf-note">Pe unele telefoane PDF-ul se afișează doar separat; folosește butonul Deschide PDF dacă zona de previzualizare rămâne goală.</div>`;
      activeButton.insertAdjacentElement('afterend', panel);
      panel.querySelector('[data-close-mobile]').addEventListener('click', closeViewer);
      panel.scrollIntoView({{block:'nearest', behavior:'smooth'}});
    }}
    function openTask(taskId) {{
      const task = taskById.get(taskId);
      if (!task) return;
      const paper = paperById.get(task.paper_id);
      activeTaskId = taskId;
      document.querySelectorAll('.task').forEach(el => el.classList.toggle('active', el.dataset.task === taskId));
      const variant = paper.variant ? ` · ${{paper.variant}}` : '';
      document.getElementById('viewerTitle').textContent = `${{paper.year}} · ${{paper.session}}${{variant}} · ${{task.task_ref}}`;
      document.getElementById('viewerMeta').textContent = `Pagina ${{task.page}} · se deschide in PDF-ul original`;
      openExternal.hidden = false;
      openExternal.style.display = 'inline-block';
      openExternal.href = task.test_url;
      if (mobileQuery.matches) {{
        viewer.classList.add('empty');
        viewerEmpty.hidden = false;
        viewerEmpty.style.display = 'grid';
        pdfFrame.hidden = true;
        pdfFrame.style.display = 'none';
        pdfFrame.removeAttribute('src');
        createMobilePdf(task, paper, variant);
        return;
      }}
      removeMobilePdf();
      viewer.classList.remove('empty');
      viewerEmpty.hidden = true;
      viewerEmpty.style.display = 'none';
      pdfFrame.hidden = false;
      pdfFrame.style.display = 'block';
      pdfFrame.src = task.test_url;
    }}
    function closeViewer() {{
      activeTaskId = '';
      viewer.classList.add('empty');
      document.getElementById('viewerTitle').textContent = 'Alege un test din lista';
      document.getElementById('viewerMeta').textContent = 'PDF-ul se va deschide aici, in aceeasi pagina.';
      viewerEmpty.hidden = false;
      viewerEmpty.style.display = 'grid';
      pdfFrame.hidden = true;
      pdfFrame.style.display = 'none';
      pdfFrame.removeAttribute('src');
      openExternal.hidden = true;
      openExternal.style.display = 'none';
      removeMobilePdf();
      document.querySelectorAll('.task').forEach(el => el.classList.remove('active'));
    }}
    document.getElementById('closeViewer').addEventListener('click', closeViewer);
    const handleLayoutChange = () => {{
      removeMobilePdf();
      if (activeTaskId) openTask(activeTaskId);
    }};
    if (mobileQuery.addEventListener) mobileQuery.addEventListener('change', handleLayoutChange);
    else mobileQuery.addListener(handleLayoutChange);
    function renderAll() {{
      renderMeta();
      renderClassTabs();
      renderEpochTabs();
      renderTopics();
      renderTasks();
    }}
    renderAll();
  </script>
</body>
</html>"""
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SITE_DIR.mkdir(exist_ok=True)
    papers, tasks, issues = extract_tasks()
    task_ids = {str(task["task_id"]) for task in tasks}
    review_rows = load_review_rows()
    reviewed, rejected = reviewed_tags(review_rows, task_ids)
    reviewed_pairs = {(str(tag["task_id"]), str(tag["topic_id"])) for tag in reviewed}
    candidates = auto_candidates(tasks, rejected | reviewed_pairs)
    copy_reviewed_pdfs(papers, tasks, reviewed)
    topics = all_topics()

    write_csv(DATA_DIR / "classes.csv", CLASSES, ["class_id", "label", "description"])
    write_csv(DATA_DIR / "epochs.csv", EPOCHS, ["class_id", "epoch_id", "label", "sort_order"])
    write_csv(DATA_DIR / "topics.csv", topics, ["class_id", "epoch_id", "topic_id", "topic_uid", "topic_number", "display_title", "quiz_link", "notebook_link", "doc_link", "doc_links", "reused_from_class9", "sort_order", "status"])
    write_csv(DATA_DIR / "papers.csv", papers, ["class_id", "paper_id", "year", "session", "variant", "test_path", "page_count"])
    write_csv(DATA_DIR / "tasks.csv", tasks, TASK_FIELDS)
    write_csv(DATA_DIR / "extraction_issues.csv", issues, ["class_id", "paper_id", "year", "session", "variant", "test_path", "issue", "note"])
    build_html(papers, tasks, reviewed, candidates, issues)
    print(f"papers={len(papers)} tasks={len(tasks)} reviewed={len(reviewed)} candidates={len(candidates)} extraction_issues={len(issues)}")
    print(f"wrote {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
