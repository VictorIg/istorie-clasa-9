from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "Missing dependency: pypdf. Run with the bundled Codex Python runtime "
        "or install pypdf in your Python environment."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
EXAM_ROOT = ROOT / "!Teste examene 2016 - 2024"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
MANUAL_TAGS_PATH = DATA_DIR / "manual_question_topics.csv"


TOPICS = [
    {
        "topic_id": 1,
        "title": "Romania in Primul razboi mondial",
        "display_title": "România în Primul Război Mondial",
        "quiz_link": "https://forms.gle/A4NkEdzADyPiMTUTA",
        "notebook_link": "https://notebooklm.google.com/notebook/d6132450-0e9d-4cea-bd48-a5f91565cd84",
        "doc_link": "https://docs.google.com/document/d/1e0eS6MCoM92cFC56URtOWjjWzqGb445r8nvxkzHHuZ8/edit?usp=sharing",
    },
    {
        "topic_id": 2,
        "title": "Miscarea nationala a romanilor din Basarabia si teritoriile din stanga Nistrului (1917-1918)",
        "display_title": "Mișcarea națională a românilor din Basarabia și teritoriile din stânga Nistrului (1917-1918)",
        "quiz_link": "https://forms.gle/DCQhEGK8JPLhGwcB9",
        "notebook_link": "https://notebooklm.google.com/notebook/68cdb58f-73d3-4cd9-8692-c30d58c5a72a",
        "doc_link": "https://docs.google.com/document/d/163utb7iCiDY3iMRYBUzdlvf7fAE78x13WUu232EA_O0/edit?usp=sharing",
    },
    {
        "topic_id": 3,
        "title": "Formarea Statului National Unitar Roman. Recunoasterea Marii Uniri de la 1918",
        "display_title": "Formarea Statului Național Unitar Român. Recunoașterea Marii Uniri de la 1918",
        "quiz_link": "https://forms.gle/sBoJE6UyTXGyghQE8",
        "notebook_link": "https://notebooklm.google.com/notebook/0363f358-7557-4471-83bd-293917c8fba9",
        "doc_link": "https://docs.google.com/document/d/1nghy6HD1osAHCOp5Kdsoql2o4Xvw5lhNI72e5HmWMho/edit?usp=sharing",
    },
    {
        "topic_id": 4,
        "title": "Conferinta de Pace de la Paris si Noua Ordine Internationala",
        "display_title": "Conferința de Pace de la Paris și Noua Ordine Internațională",
        "quiz_link": "https://forms.gle/Z5Xb3vd15sGfeSpT7",
        "notebook_link": "https://notebooklm.google.com/notebook/f9232623-6376-484b-b5ea-f68653ce30e7",
        "doc_link": "https://docs.google.com/document/d/1fLpsWAM9b9VOoOzIAKkh7rG9Q63-RT5ScMW7iHm_suE/edit?usp=sharing",
    },
    {
        "topic_id": 5,
        "title": "Statele Unite ale Americii",
        "display_title": "Statele Unite ale Americii",
        "quiz_link": "https://forms.gle/X9qqGSkfZjkx2QAD8",
        "notebook_link": "https://notebooklm.google.com/notebook/d066a62b-5dce-4ee7-b82a-f3661d0d572c",
        "doc_link": "https://docs.google.com/document/d/1yN39Ui-jFX3UYecZiC7iqRdbk6X8m4wbqqxqjNmYhpM/edit?usp=sharing",
    },
    {
        "topic_id": 6,
        "title": "Statele Europei de Vest (Marea Britanie, Franta, Germania, Italia, Spania)",
        "display_title": "Statele Europei de Vest (Marea Britanie, Franța, Germania, Italia, Spania)",
        "quiz_link": "https://forms.gle/Dmc1fqNsPU4QfkJy6",
        "notebook_link": "https://notebooklm.google.com/notebook/ea3be1ed-3d3d-473f-a462-c68c4fa2d53e",
        "doc_link": "https://docs.google.com/document/d/15Xka6XLlhkv41M-rNZYScMzlaROzSK89EuFXvJof5WA/edit?usp=sharing",
    },
    {
        "topic_id": 7,
        "title": "Romania in perioada interbelica",
        "display_title": "România în perioada interbelică",
        "quiz_link": "https://forms.gle/ADWLPXWjpHRRHpcd7",
        "notebook_link": "https://notebooklm.google.com/notebook/e3181c6e-e74f-4e16-93fc-ebe88eea8bec",
        "doc_link": "https://docs.google.com/document/d/1eCD4Kk7lfnXnfqEOXbkMvjCwE6J482pdpNQ89nN_SPM/edit?usp=sharing",
    },
    {
        "topic_id": 8,
        "title": "Basarabia in cadrul Romaniei Mari (1918-1940)",
        "display_title": "Basarabia în cadrul României Mari (1918-1940)",
        "quiz_link": "https://forms.gle/TF5cSbwxAGRBVu5p7",
        "notebook_link": "https://notebooklm.google.com/notebook/d2fe5d78-702d-4743-9191-e060c1c3398d",
        "doc_link": "",
    },
    {
        "topic_id": 9,
        "title": "RASSM (1924-1940) si politica expansionista a URSS",
        "display_title": "RASSM (1924-1940) și politica expansionistă a URSS",
        "quiz_link": "https://forms.gle/E2dhHodX6rmMZ2Ux7",
        "notebook_link": "https://notebooklm.google.com/notebook/c665c924-9d15-4db2-aa24-d8a7a69ffa78",
        "doc_link": "https://docs.google.com/document/d/1MxTtv3GtWk4S_Oc4xZjFSetYKdNkwUAi25yY4MmWdHM/edit?usp=sharing",
    },
    {
        "topic_id": 10,
        "title": "Cultura si stiinta universala si romaneasca in perioada interbelica",
        "display_title": "Cultura și știința universală și românească în perioada interbelică",
        "quiz_link": "https://forms.gle/UJ4HQPNQ6kPuheJJA",
        "notebook_link": "https://notebooklm.google.com/notebook/d7caaffb-cea9-464b-82fa-4f4931429385",
        "doc_link": "https://docs.google.com/document/d/1_KrzGzYXZaKcoQCUE4lw83DR4G0JqQ4_g_s6QBX3Yp8/edit?usp=sharing",
    },
    {
        "topic_id": 11,
        "title": "Aliante si tratate politico-militare in perioada interbelica",
        "display_title": "Alianțe și tratate politico-militare în perioada interbelică",
        "quiz_link": "https://forms.gle/AEU6syZhBZsoKAxf9",
        "notebook_link": "https://notebooklm.google.com/notebook/21c7a489-eb01-4015-afeb-a6511b60444c",
        "doc_link": "https://docs.google.com/document/d/1q-kGdHqYj_yObIJfEeINshH_DKzkG2ZUmiRK3JzdAWE/edit?usp=sharing",
    },
    {
        "topic_id": 12,
        "title": "Relatiile sovieto-romane intre 1918 si 1940. Pactul Ribbentrop-Molotov si consecintele lui pentru popoarele din Europa",
        "display_title": "Relațiile sovieto-române între 1918 și 1940. Pactul Ribbentrop-Molotov și consecințele lui pentru popoarele din Europa",
        "quiz_link": "https://forms.gle/NwRR6dxWxFyH4PYW9",
        "notebook_link": "https://notebooklm.google.com/notebook/11730e3e-519b-465c-903e-05c0958ae27b",
        "doc_link": "https://docs.google.com/document/d/1VJy-C07FcmGOY9lITSUms5N8L64cKi8VoQ9OBNG4y4w/edit?usp=sharing",
    },
    {
        "topic_id": 13,
        "title": "Pierderile teritoriale ale Romaniei in vara anului 1940",
        "display_title": "Pierderile teritoriale ale României în vara anului 1940",
        "quiz_link": "https://forms.gle/nJxtWusRPfPK3SbAA",
        "notebook_link": "https://notebooklm.google.com/notebook/0404e926-3a09-470b-b3cb-4a2211440f2c",
        "doc_link": "https://docs.google.com/document/d/10ckEdPzrS8TC7Osg9yN_7QVZLOmO3OGP-Rv9GE-moKU/edit?usp=sharing",
    },
    {
        "topic_id": 14,
        "title": "Formarea RSSM si instaurarea regimului comunist",
        "display_title": "Formarea RSSM și instaurarea regimului comunist",
        "quiz_link": "https://forms.gle/H9YBHQCBGBR6syvk7",
        "notebook_link": "https://notebooklm.google.com/notebook/a317ee79-f164-469d-a651-f0763d4ee81c",
        "doc_link": "https://docs.google.com/document/d/1D_DKdHuYbyMyST4XHVHJIHKcgEOgtq2A7R5JxnL8VdY/edit?usp=sharing",
    },
    {
        "topic_id": 15,
        "title": "Al Doilea Razboi Mondial",
        "display_title": "Al Doilea Război Mondial",
        "quiz_link": "https://forms.gle/1pLwGDxf5iq2fDVT8",
        "notebook_link": "https://notebooklm.google.com/notebook/b6a08560-ddda-4b81-b6f3-5cf2c5be2539",
        "doc_link": "https://docs.google.com/document/d/1qMoiO65ubJ_K1a9k9DqFHyVWsHRki7Uc_XjvatYv47M/edit?usp=sharing",
    },
    {
        "topic_id": 16,
        "title": "Romania, Basarabia si Transnistria in anii celui de-al Doilea Razboi Mondial",
        "display_title": "România, Basarabia și Transnistria în anii celui de-al Doilea Război Mondial",
        "quiz_link": "https://forms.gle/f6bzXPourP6TLHtg8",
        "notebook_link": "https://notebooklm.google.com/notebook/26811b89-6203-4bfc-8bf6-e73011e55a1b",
        "doc_link": "https://docs.google.com/document/d/1dbEWoj8pDEfmZXu4eE00bCw_nN0cQE1t9CLNhFUIKZ4/edit?usp=sharing",
    },
    {
        "topic_id": 17,
        "title": "Consecintele celui de-al Doilea Razboi Mondial",
        "display_title": "Consecințele celui de-al Doilea Război Mondial",
        "quiz_link": "https://forms.gle/am6ZDPkqw6abgE3Q6",
        "notebook_link": "https://notebooklm.google.com/notebook/b2c7f64a-a44d-4eb0-81e4-6e42455027c9",
        "doc_link": "https://docs.google.com/document/d/1zSO-LCOgZTSjF17DE_ZRFoB6oyCGUP5BYSN-xU0d4Ew/edit?usp=sharing",
    },
    {
        "topic_id": 18,
        "title": "Relatiile internationale in perioada 1945-1991. Constituirea si activitatea Organizatiei Natiunilor Unite",
        "display_title": "Relațiile internaționale în perioada 1945-1991. Constituirea și activitatea Organizației Națiunilor Unite",
        "quiz_link": "https://forms.gle/5j9Tx48HWNveCA9x8",
        "notebook_link": "https://notebooklm.google.com/notebook/b9de9536-089b-4c6c-9c8c-836497d93335",
        "doc_link": "https://docs.google.com/document/d/12HcjHTRWiyJHivZ1fu0WkTDfyWu52bpWWgxITa5uQhM/edit?usp=sharing",
    },
    {
        "topic_id": 19,
        "title": "Uniunea Sovietica in perioada postbelica",
        "display_title": "Uniunea Sovietică în perioada postbelică",
        "quiz_link": "https://forms.gle/yPPxt8oBoKskn8eTA",
        "notebook_link": "https://notebooklm.google.com/notebook/731a99e0-f9a3-4ead-ac8d-ce68a521f813",
        "doc_link": "https://docs.google.com/document/d/1bAyZPG-NQngwThHml0ZR_2X5MpL4axBWTLXjzFQ4AeI/edit?usp=sharing",
    },
    {
        "topic_id": 20,
        "title": "RSSM. Economie si societate (1944-1985)",
        "display_title": "RSSM. Economie și societate (1944-1985)",
        "quiz_link": "https://forms.gle/QsWTELF8CCxGAiu68",
        "notebook_link": "https://notebooklm.google.com/notebook/c41492d1-24cc-4121-bd22-969340b3f92d",
        "doc_link": "https://docs.google.com/document/d/1EnsrC616DQep_byFDXjhm9XTzi0kxxUzDo_z48akqHI/edit?usp=sharing",
    },
    {
        "topic_id": 21,
        "title": "Foametea, represiunile si deportarile staliniste din RSSM",
        "display_title": "Foametea, represiunile și deportările staliniste din RSSM",
        "quiz_link": "https://forms.gle/jpv94i5XDenk7gPS6",
        "notebook_link": "https://notebooklm.google.com/notebook/821cbe61-2ae8-426c-b513-2a7bb62980d5",
        "doc_link": "https://docs.google.com/document/d/1oQe7CM4tJ5ti7_OJprWW1AdHbmSSoXEO79Gb9wYaz6w/edit?usp=sharing",
    },
    {
        "topic_id": 22,
        "title": "RSSM intre 1985-1991. Proclamarea independentei Republicii Moldova",
        "display_title": "RSSM între 1985-1991. Proclamarea independenței Republicii Moldova",
        "quiz_link": "https://forms.gle/CENCwF16itzUjhsQ6",
        "notebook_link": "https://notebooklm.google.com/notebook/2caa332f-9794-4386-8116-ac4cc3e8796b",
        "doc_link": "https://docs.google.com/document/d/1ojS5yaWT7U9ZnJGe6BFJ2nOYzU0Ktkh7aLWKHlk-EIM/edit?usp=sharing",
    },
    {
        "topic_id": 23,
        "title": "Razboiul de pe Nistru",
        "display_title": "Războiul de pe Nistru",
        "quiz_link": "https://forms.gle/A22wQa6by4H8Sk438",
        "notebook_link": "https://notebooklm.google.com/notebook/b4d1f948-6803-468f-8263-6089a1447b44",
        "doc_link": "https://docs.google.com/document/d/1_LyhRWISnWXAI1dQEwezPvJbgA1R9JE9sXvCeRsyy84/edit?usp=sharing",
    },
    {
        "topic_id": 24,
        "title": "Cultura si stiinta in RSSM (1944-1991)",
        "display_title": "Cultura și știința în RSSM (1944-1991)",
        "quiz_link": "https://forms.gle/BwBgaP1EDcPmWCt4A",
        "notebook_link": "https://notebooklm.google.com/notebook/7badf872-47b9-4d3c-95cd-1f04da114c0d",
        "doc_link": "https://docs.google.com/document/d/1d3LsxNiEwm27gT6P71gZrWs7JjxZgsvyK6PS5RFc3ts/edit?usp=sharing",
    },
    {
        "topic_id": 25,
        "title": "Evolutia culturii in Republica Moldova",
        "display_title": "Evoluția culturii în Republica Moldova",
        "quiz_link": "https://forms.gle/9dBqzitUWK6hUEQv7",
        "notebook_link": "https://notebooklm.google.com/notebook/50c24983-091a-49c4-9efa-2b199d06224e",
        "doc_link": "https://docs.google.com/document/d/1AsBUiIklSKJ_97LnBhFAWCkGbQ1VlG_8XeXAt9AAdyI/edit?usp=sharing",
    },
    {
        "topic_id": 26,
        "title": "Cultura si stiinta universala in Epoca Contemporana",
        "display_title": "Cultura și știința universală în Epoca Contemporană",
        "quiz_link": "https://forms.gle/xxvw8qVFpBJHSYiw5",
        "notebook_link": "https://notebooklm.google.com/notebook/e504a999-9458-44ec-82c2-565d92b623d1",
        "doc_link": "https://docs.google.com/document/d/1gqRAZ9ldkg6Jmf4aThQMFO6JH0--h5AUklGs1RiK8Jk/edit?usp=sharing",
    },
]


KEYWORDS = {
    1: ["primul razboi", "1916", "antanta", "consiliul de coroana", "ferdinand", "neutralitatii"],
    2: ["sfatul tarii", "ion inculet", "miscarea nationala", "basarabia", "1917", "republica democratica moldoveneasca"],
    3: ["marea unire", "actul unirii", "27 martie 1918", "alba iulia", "cernauti", "bucovina", "transilvania", "trianon", "saint-germain"],
    4: ["conferinta de pace", "versailles", "liga natiunilor", "societatea natiunilor", "wilson", "14 puncte", "consiliul celor patru"],
    5: ["sua", "statele unite", "marea depresiune", "new deal", "roosevelt", "wall street", "somajului", "presedintii sua"],
    6: ["hitler", "mussolini", "nazist", "fascist", "totalitar", "germania", "italia", "franta", "marea britanie"],
    7: ["romania interbelica", "constitutia din 1923", "pluripartidist", "pnt", "pnl", "reforme democratice", "modernizarea societatii romanesti"],
    8: ["basarabia", "1918-1940", "scoala basarabeana", "structura proprietatii funciare", "populatiei basarabiei", "productiei agrare"],
    9: ["rassm", "1924", "pc(b)", "culaci", "colhoz", "dusmanul de clasa", "sovietizarea"],
    10: ["brancusi", "mateevici", "city lights", "chaplin", "radio", "electricitatea", "cultura nationala", "perioada interbelica"],
    11: ["mica intelegere", "intelegerea balcanica", "titulescu", "aliante", "securitate colectiva", "status-quo"],
    12: ["ribbentrop", "molotov", "sovieto-romane", "protocol aditional", "ultimatum", "28 iunie 1940"],
    13: ["pierderile teritoriale", "anul 1940", "cadrilater", "dictatul de la viena", "basarabia", "bucovina de nord", "transilvania de nord"],
    14: ["formarea rssm", "rssm", "regim comunist", "2 august 1940", "sovietic", "comunist"],
    15: ["al doilea razboi mondial", "1939", "1945", "pearl harbor", "stalingrad", "coalitia antihitlerista"],
    16: ["antonescu", "transnistria", "holocaust", "iasi-chisinau", "basarabia", "al doilea razboi mondial"],
    17: ["consecintele celui de-al doilea razboi", "nurnberg", "pierderi umane", "crime de razboi", "postbelic"],
    18: ["razboiul rece", "onu", "organizatia natiunilor unite", "nato", "pactul de la varsovia", "blocuri", "1945-1991"],
    19: ["uniunea sovietica", "stalin", "hrusciov", "brejnev", "perestroika", "postbelica"],
    20: ["rssm", "economie", "societate", "industrializare", "colectivizare", "colhoz", "1944-1985"],
    21: ["foametea", "foamete", "deportarile", "deportari", "represiunile", "staliniste", "siberia", "gulag", "operatiunea sud"],
    22: ["independenta republicii moldova", "27 august 1991", "frontul popular", "limba romana", "1985-1991", "declaratia de independenta"],
    23: ["razboiul de pe nistru", "nistru", "transnistria", "1992", "tighina", "conflictul armat"],
    24: ["cultura in rssm", "stiinta in rssm", "vieru", "druță", "druta", "1944-1991", "rssm"],
    25: ["cultura in republica moldova", "republica moldova", "cultura", "independenta"],
    26: ["cultura si stiinta universala", "epoca contemporana", "cosmos", "gagarin", "internet", "globalizare", "stiinta contemporana"],
}


QUESTION_VERBS = (
    "Studiaza",
    "Numeste",
    "Identifica",
    "Descrie",
    "Explica",
    "Determina",
    "Formuleaza",
    "Apreciaza",
    "Exprima",
    "Argumenteaza",
    "Utilizeaza",
    "Redacteaza",
    "Compara",
    "Completeaza",
    "Propune",
    "Selecteaza",
    "Mentioneaza",
    "Stabileste",
)


@dataclass
class Paper:
    paper_id: str
    year: int
    session: str
    variant: str
    test_path: Path
    barem_path: Path | None
    page_count: int


def strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def norm(value: str) -> str:
    value = strip_diacritics(value)
    value = value.replace("ţ", "t").replace("ş", "s").replace("Ţ", "T").replace("Ş", "S")
    value = value.replace("–", "-").replace("—", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", value.lower()).strip()


def slug(value: str) -> str:
    value = norm(value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "item"


def clean_text(value: str) -> str:
    value = value.replace("\u00ad", "")
    value = re.sub(r"\bL\s+(?:0\s+){1,8}\d\b", " ", value)
    value = re.sub(r"\b(?:0\s+){1,8}\d\b", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def rel_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def file_url(path: str, page: int | None = None) -> str:
    url = "/".join(quote(part) for part in path.split("/"))
    if page:
        url += f"#page={page}"
    return "../" + url


def session_label(raw: str) -> str:
    fixed = raw.replace("Esantion", "Esantion").replace("Suplimentara", "Suplimentara")
    fixed = fixed.replace("Sesiunea de baza", "Sesiunea de baza")
    return fixed


def variant_from_name(path: Path) -> str:
    name = path.stem.lower()
    match = re.search(r"test\s*([12])|test([12])", name)
    if match:
        return f"Test {match.group(1) or match.group(2)}"
    return ""


def pair_barem(test_path: Path) -> Path | None:
    folder = test_path.parent
    barems = sorted(p for p in folder.glob("*.pdf") if "barem" in p.name.lower())
    if not barems:
        return None
    variant = variant_from_name(test_path)
    if variant:
        number = variant[-1]
        for barem in barems:
            if re.search(rf"barem\s*{number}|barem{number}", barem.stem.lower()):
                return barem
    return barems[0]


def discover_papers() -> list[Paper]:
    papers: list[Paper] = []
    for path in sorted(EXAM_ROOT.rglob("*.pdf")):
        lower = path.name.lower()
        if "barem" in lower or "borderou" in lower:
            continue
        if "test" not in lower:
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
            Paper(
                paper_id=paper_id,
                year=year,
                session=session,
                variant=variant,
                test_path=path,
                barem_path=pair_barem(path),
                page_count=page_count,
            )
        )
    return papers


def infer_subject(text: str, fallback: str) -> str:
    normalized = norm(text)
    if "subiectul al iii" in normalized or "subiectul iii" in normalized:
        return "III"
    if "subiectul al ii" in normalized or "subiectul ii" in normalized:
        return "II"
    if "subiectul i" in normalized:
        return "I"
    return fallback


def subject_markers(text: str, fallback: str) -> list[tuple[int, str]]:
    markers: list[tuple[int, str]] = []
    patterns = [
        (r"SUBIECTUL\s+I\b", "I"),
        (r"SUBIECTUL\s+(?:al\s+)?II(?:-lea)?\b", "II"),
        (r"SUBIECTUL\s+(?:al\s+)?III(?:-lea)?\b", "III"),
    ]
    for pattern, subject in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            markers.append((match.start(), subject))
    markers.sort()
    if fallback and (not markers or markers[0][0] > 0):
        markers.insert(0, (0, fallback))
    return markers


def subject_at(markers: list[tuple[int, str]], position: int, fallback: str) -> str:
    current = fallback
    for marker_position, subject in markers:
        if marker_position <= position:
            current = subject
        else:
            break
    return current


def next_subject_marker(markers: list[tuple[int, str]], position: int) -> int | None:
    for marker_position, _subject in markers:
        if marker_position > position:
            return marker_position
    return None


def question_regex() -> re.Pattern[str]:
    verbs = "|".join(re.escape(v) for v in QUESTION_VERBS)
    return re.compile(rf"(?m)^\s*(\d{{1,2}})[.)]?\s+(?=({verbs})\b)", re.IGNORECASE)


def extract_items_from_page(text: str, fallback_subject: str, page_number: int) -> list[dict[str, str | int]]:
    source_text = text.replace("\u00ad", "")
    normalized_text = strip_diacritics(source_text)
    normalized_text = normalized_text.replace("Ş", "S").replace("ş", "s").replace("Ţ", "T").replace("ţ", "t")
    markers = subject_markers(normalized_text, fallback_subject)
    matches = list(question_regex().finditer(normalized_text))
    items: list[dict[str, str | int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        next_item = matches[index + 1].start() if index + 1 < len(matches) else len(normalized_text)
        next_subject = next_subject_marker(markers, start)
        end = min(next_item, next_subject) if next_subject else next_item
        chunk = clean_text(source_text[start:end])
        if len(chunk) < 25:
            continue
        subject = subject_at(markers, start, fallback_subject)
        item_number = match.group(1)
        items.append(
            {
                "subject": subject,
                "item": item_number,
                "page": page_number,
                "question_text": chunk,
            }
        )

    if not items and subject_at(markers, 0, fallback_subject) == "III":
        essay_match = re.search(r"Utilizeaza sursele.+", normalized_text, re.IGNORECASE | re.DOTALL)
        if essay_match:
            items.append(
                {
                    "subject": "III",
                    "item": "eseu",
                    "page": page_number,
                    "question_text": clean_text(source_text[essay_match.start() : essay_match.end()]),
                }
            )
    return items


def extract_questions(papers: list[Paper]) -> list[dict[str, str | int]]:
    questions: list[dict[str, str | int]] = []
    for paper in papers:
        try:
            reader = PdfReader(str(paper.test_path))
        except Exception:
            continue
        current_subject = ""
        per_paper_counter = 1
        for page_index, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            if not raw_text.strip():
                continue
            current_subject = infer_subject(raw_text, current_subject)
            if not current_subject:
                continue
            for item in extract_items_from_page(raw_text, current_subject, page_index):
                item_ref = f"{item['subject']}.{item['item']}"
                question_id = f"{paper.paper_id}-{slug(item_ref)}-{per_paper_counter:02d}"
                per_paper_counter += 1
                questions.append(
                    {
                        "question_id": question_id,
                        "paper_id": paper.paper_id,
                        "year": paper.year,
                        "session": paper.session,
                        "variant": paper.variant,
                        "subject": item["subject"],
                        "item": item["item"],
                        "item_ref": item_ref,
                        "page": item["page"],
                        "question_text": item["question_text"],
                        "test_path": rel_path(paper.test_path),
                        "test_url": file_url(rel_path(paper.test_path), int(item["page"])),
                        "barem_path": rel_path(paper.barem_path) if paper.barem_path else "",
                        "barem_url": file_url(rel_path(paper.barem_path), None) if paper.barem_path else "",
                    }
                )
    return questions


def score_topic(question_text: str, topic_id: int) -> tuple[int, list[str]]:
    haystack = norm(question_text)
    hits: list[str] = []
    score = 0
    for keyword in KEYWORDS[topic_id]:
        key = norm(keyword)
        if key and key in haystack:
            hits.append(keyword)
            score += 2 if len(key.split()) > 1 else 1
    return score, hits


def generate_tags(questions: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
    tags: list[dict[str, str | int]] = []
    for question in questions:
        scored = []
        for topic in TOPICS:
            score, hits = score_topic(str(question["question_text"]), int(topic["topic_id"]))
            if score:
                scored.append((score, int(topic["topic_id"]), hits))
        scored.sort(reverse=True)
        for score, topic_id, hits in scored[:4]:
            if score < 2:
                continue
            confidence = "high" if score >= 6 else "medium" if score >= 4 else "low"
            tags.append(
                {
                    "question_id": question["question_id"],
                    "topic_id": topic_id,
                    "confidence": confidence,
                    "score": score,
                    "review_status": "auto",
                    "matched_keywords": "; ".join(hits),
                    "note": "",
                }
            )
    return tags


def ensure_manual_tags_template() -> None:
    if MANUAL_TAGS_PATH.exists():
        return
    write_csv(
        MANUAL_TAGS_PATH,
        [],
        ["question_id", "topic_id", "action", "note"],
    )


def apply_manual_tags(tags: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
    if not MANUAL_TAGS_PATH.exists():
        return tags

    by_pair: dict[tuple[str, str], dict[str, str | int]] = {
        (str(tag["question_id"]), str(tag["topic_id"])): tag for tag in tags
    }
    with MANUAL_TAGS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            question_id = (row.get("question_id") or "").strip()
            topic_id = (row.get("topic_id") or "").strip()
            action = norm(row.get("action") or "add")
            note = (row.get("note") or "").strip()
            if not question_id or not topic_id:
                continue
            key = (question_id, topic_id)
            if action in {"remove", "reject", "rejected", "delete"}:
                by_pair.pop(key, None)
                continue
            if action in {"add", "approve", "approved", "manual", "keep"}:
                existing = by_pair.get(key)
                if existing:
                    existing["review_status"] = "approved" if action.startswith("approv") or action == "keep" else "manual"
                    existing["note"] = note
                else:
                    by_pair[key] = {
                        "question_id": question_id,
                        "topic_id": topic_id,
                        "confidence": "manual",
                        "score": 999,
                        "review_status": "manual",
                        "matched_keywords": "",
                        "note": note,
                    }
    return sorted(by_pair.values(), key=lambda tag: (str(tag["question_id"]), int(tag["topic_id"])))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def build_html(topics: list[dict[str, object]], papers: list[Paper], questions: list[dict[str, object]], tags: list[dict[str, object]]) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    paper_rows = [
        {
            "paper_id": p.paper_id,
            "year": p.year,
            "session": p.session,
            "variant": p.variant,
            "test_path": rel_path(p.test_path),
            "test_url": file_url(rel_path(p.test_path)),
            "barem_path": rel_path(p.barem_path) if p.barem_path else "",
            "barem_url": file_url(rel_path(p.barem_path)) if p.barem_path else "",
            "page_count": p.page_count,
        }
        for p in papers
    ]
    payload = {
        "topics": topics,
        "papers": paper_rows,
        "questions": questions,
        "tags": tags,
    }
    json_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html_doc = f"""<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Navigator istorie clasa a 9-a</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8f5;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #667085;
      --line: #d9ded6;
      --accent: #176b64;
      --accent-soft: #e3f0ed;
      --mark: #8a5a16;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: #fff;
      padding: 16px 22px;
      display: flex;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(260px, 360px) 1fr;
      min-height: calc(100vh - 65px);
    }}
    aside {{
      border-right: 1px solid var(--line);
      background: #fbfcfa;
      padding: 14px;
      overflow: auto;
      max-height: calc(100vh - 65px);
    }}
    main {{
      padding: 18px;
      overflow: auto;
      max-height: calc(100vh - 65px);
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      padding: 9px 10px;
      border-radius: 6px;
      font: inherit;
    }}
    .filters {{
      display: grid;
      grid-template-columns: 1.4fr 160px 180px;
      gap: 10px;
      margin-bottom: 14px;
    }}
    .topic-list {{
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }}
    button.topic {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 6px;
      padding: 10px;
      cursor: pointer;
      text-align: left;
      color: var(--ink);
      display: grid;
      gap: 5px;
    }}
    button.topic.active {{
      border-color: var(--accent);
      background: var(--accent-soft);
    }}
    .topic-title {{
      font-size: 14px;
      line-height: 1.25;
      font-weight: 700;
    }}
    .topic-count, .meta, .links {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .summary {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 12px;
    }}
    .summary h2 {{
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .links {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    a {{
      color: var(--accent);
      text-decoration-thickness: 1px;
      text-underline-offset: 2px;
    }}
    .question-list {{
      display: grid;
      gap: 10px;
    }}
    .question {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      gap: 8px;
    }}
    .question-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: start;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      white-space: nowrap;
      background: #fff;
    }}
    .text {{
      font-size: 14px;
      line-height: 1.45;
    }}
    .tagline {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .tag {{
      border-radius: 999px;
      background: #f5efe4;
      color: var(--mark);
      padding: 3px 8px;
      font-size: 12px;
    }}
    .empty {{
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 24px;
      color: var(--muted);
      background: #fff;
    }}
    @media (max-width: 820px) {{
      .layout {{ grid-template-columns: 1fr; }}
      aside, main {{ max-height: none; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .filters {{ grid-template-columns: 1fr; }}
      .summary {{ display: grid; }}
      .links {{ justify-content: flex-start; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Navigator istorie clasa a 9-a</h1>
    <div class="meta" id="corpusMeta"></div>
  </header>
  <div class="layout">
    <aside>
      <input id="topicSearch" type="search" placeholder="Cauta tema">
      <div class="topic-list" id="topicList"></div>
    </aside>
    <main>
      <div class="filters">
        <input id="questionSearch" type="search" placeholder="Cauta in intrebari">
        <select id="yearFilter"></select>
        <select id="sessionFilter"></select>
      </div>
      <section class="summary">
        <div>
          <h2 id="activeTitle"></h2>
          <div class="meta" id="activeMeta"></div>
        </div>
        <div class="links" id="topicLinks"></div>
      </section>
      <div class="question-list" id="questionList"></div>
    </main>
  </div>
  <script id="history-data" type="application/json">{json_payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('history-data').textContent);
    const tagsByQuestion = new Map();
    const tagsByTopic = new Map();
    const topicsById = new Map(data.topics.map(t => [String(t.topic_id), t]));
    for (const tag of data.tags) {{
      if (!tagsByQuestion.has(tag.question_id)) tagsByQuestion.set(tag.question_id, []);
      tagsByQuestion.get(tag.question_id).push(tag);
      if (!tagsByTopic.has(String(tag.topic_id))) tagsByTopic.set(String(tag.topic_id), []);
      tagsByTopic.get(String(tag.topic_id)).push(tag);
    }}
    let activeTopic = String(data.topics[0].topic_id);

    const topicList = document.getElementById('topicList');
    const questionList = document.getElementById('questionList');
    const topicSearch = document.getElementById('topicSearch');
    const questionSearch = document.getElementById('questionSearch');
    const yearFilter = document.getElementById('yearFilter');
    const sessionFilter = document.getElementById('sessionFilter');

    document.getElementById('corpusMeta').textContent = `${{data.papers.length}} teste | ${{data.questions.length}} itemi | ${{data.tags.length}} etichete`;

    function optionList(values, allLabel) {{
      return [`<option value="">${{allLabel}}</option>`, ...values.map(v => `<option value="${{String(v)}}">${{v}}</option>`)].join('');
    }}
    yearFilter.innerHTML = optionList([...new Set(data.papers.map(p => p.year))].sort((a, b) => b - a), 'Toti anii');
    sessionFilter.innerHTML = optionList([...new Set(data.papers.map(p => p.session))].sort(), 'Toate sesiunile');

    function topicCount(topicId) {{
      return (tagsByTopic.get(String(topicId)) || []).length;
    }}

    function renderTopics() {{
      const q = topicSearch.value.trim().toLowerCase();
      topicList.innerHTML = data.topics
        .filter(t => !q || t.display_title.toLowerCase().includes(q) || String(t.topic_id) === q)
        .map(t => `
          <button class="topic ${{String(t.topic_id) === activeTopic ? 'active' : ''}}" data-topic="${{t.topic_id}}">
            <span class="topic-title">${{t.topic_id}}. ${{t.display_title}}</span>
            <span class="topic-count">${{topicCount(t.topic_id)}} itemi propusi</span>
          </button>
        `).join('');
      for (const button of topicList.querySelectorAll('button.topic')) {{
        button.addEventListener('click', () => {{
          activeTopic = button.dataset.topic;
          renderTopics();
          renderQuestions();
        }});
      }}
    }}

    function link(label, href) {{
      return href ? `<a href="${{href}}" target="_blank" rel="noreferrer">${{label}}</a>` : '';
    }}

    function renderQuestions() {{
      const topic = topicsById.get(activeTopic);
      const topicTags = tagsByTopic.get(activeTopic) || [];
      const questionIds = new Set(topicTags.map(t => t.question_id));
      const q = questionSearch.value.trim().toLowerCase();
      const year = yearFilter.value;
      const session = sessionFilter.value;
      document.getElementById('activeTitle').textContent = `${{topic.topic_id}}. ${{topic.display_title}}`;
      document.getElementById('activeMeta').textContent = `${{topicTags.length}} itemi propusi pentru revizuire`;
      document.getElementById('topicLinks').innerHTML = [
        link('Test grila', topic.quiz_link),
        link('NotebookLM', topic.notebook_link),
        link('Document', topic.doc_link)
      ].filter(Boolean).join('');

      const rows = data.questions
        .filter(item => questionIds.has(item.question_id))
        .filter(item => !q || item.question_text.toLowerCase().includes(q))
        .filter(item => !year || String(item.year) === year)
        .filter(item => !session || item.session === session)
        .sort((a, b) => b.year - a.year || a.session.localeCompare(b.session) || a.item_ref.localeCompare(b.item_ref));

      if (!rows.length) {{
        questionList.innerHTML = '<div class="empty">Nu exista itemi pentru filtrul curent.</div>';
        return;
      }}
      questionList.innerHTML = rows.map(item => {{
        const itemTags = (tagsByQuestion.get(item.question_id) || [])
          .sort((a, b) => b.score - a.score)
          .map(tag => {{
            const t = topicsById.get(String(tag.topic_id));
            return `<span class="tag">${{tag.confidence}} · ${{tag.topic_id}}. ${{t ? t.display_title : ''}}</span>`;
          }}).join('');
        const variant = item.variant ? ` · ${{item.variant}}` : '';
        return `
          <article class="question">
            <div class="question-head">
              <div>
                <strong>${{item.year}} · ${{item.session}}${{variant}}</strong>
                <div class="meta">Subiectul ${{item.subject}} · Item ${{item.item}} · pagina ${{item.page}}</div>
              </div>
              <span class="badge">${{item.item_ref}}</span>
            </div>
            <div class="text">${{item.question_text}}</div>
            <div class="tagline">${{itemTags}}</div>
            <div class="links">
              <a href="${{item.test_url}}" target="_blank" rel="noreferrer">Test PDF</a>
              ${{item.barem_url ? `<a href="${{item.barem_url}}" target="_blank" rel="noreferrer">Barem PDF</a>` : ''}}
            </div>
          </article>
        `;
      }}).join('');
    }}

    topicSearch.addEventListener('input', renderTopics);
    questionSearch.addEventListener('input', renderQuestions);
    yearFilter.addEventListener('change', renderQuestions);
    sessionFilter.addEventListener('change', renderQuestions);
    renderTopics();
    renderQuestions();
  </script>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    papers = discover_papers()
    questions = extract_questions(papers)
    ensure_manual_tags_template()
    tags = apply_manual_tags(generate_tags(questions))

    write_csv(
        DATA_DIR / "topics.csv",
        TOPICS,
        ["topic_id", "display_title", "quiz_link", "notebook_link", "doc_link"],
    )
    write_csv(
        DATA_DIR / "papers.csv",
        [
            {
                "paper_id": p.paper_id,
                "year": p.year,
                "session": p.session,
                "variant": p.variant,
                "test_path": rel_path(p.test_path),
                "barem_path": rel_path(p.barem_path) if p.barem_path else "",
                "page_count": p.page_count,
            }
            for p in papers
        ],
        ["paper_id", "year", "session", "variant", "test_path", "barem_path", "page_count"],
    )
    write_csv(
        DATA_DIR / "questions.csv",
        questions,
        [
            "question_id",
            "paper_id",
            "year",
            "session",
            "variant",
            "subject",
            "item",
            "item_ref",
            "page",
            "question_text",
            "test_path",
            "test_url",
            "barem_path",
            "barem_url",
        ],
    )
    write_csv(
        DATA_DIR / "question_topics.csv",
        tags,
        ["question_id", "topic_id", "confidence", "score", "review_status", "matched_keywords", "note"],
    )
    build_html(TOPICS, papers, questions, tags)
    print(f"papers={len(papers)} questions={len(questions)} tags={len(tags)}")
    print(f"wrote {DATA_DIR / 'topics.csv'}")
    print(f"wrote {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
