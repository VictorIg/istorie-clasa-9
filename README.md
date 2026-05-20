# Navigator istorie clasa a 9-a

Proiect static pentru navigarea testelor de istorie dupa temele din programa.

Versiunea curenta:

- ignora complet baremurile;
- ignora demo-ul generat anterior;
- foloseste doar maparile verificate din `data/reviewed_task_topics.csv`;
- copiaza automat PDF-urile necesare in `site/pdfs/`, ca site-ul sa poata fi publicat pe server.

## Fisiere principale

- `site/index.html` - interfata finala pentru elevi si profesor.
- `site/pdfs/` - PDF-urile folosite de interfata finala, copiate cu nume stabile.
- `data/reviewed_task_topics.csv` - maparile manuale aprobate.
- `data/topics.csv` - lista temelor si linkurile auxiliare.
- `data/papers.csv` - indexul testelor pastrate.
- `data/tasks.csv` - sarcinile extrase din testele pastrate.
- `data/extraction_issues.csv` - probleme de extragere, daca exista.
- `tools/build_history_browser_v3.py` - scriptul care regenereaza `site/index.html` si `site/pdfs/`.
- `!Teste examene 2016 - 2024/` - sursa PDF-urilor de test pastrate pentru regenerare.

## Regenerare

Ruleaza:

```powershell
C:\Users\vic\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\build_history_browser_v3.py
```

Scriptul reconstruieste pagina, CSV-urile generate si copiaza in `site/pdfs/` doar PDF-urile folosite de maparile revizuite.

## Publicare pe Coolify

Cel mai simplu este sa publici doar folderul `site/` ca static site.

Setari recomandate in Coolify:

- Build Pack: `Static`
- Base Directory: `/site`
- Web Server: `Nginx`
- Build Command: gol / empty
- Publish Directory: gol / default, daca Coolify foloseste deja Base Directory

Dupa deploy, testeaza:

- pagina principala se incarca;
- cand apesi pe un rand de test, PDF-ul se deschide in panoul din dreapta;
- linkul `Deschide separat` duce la un URL de forma `/pdfs/nume-test.pdf#page=...`.

## Setup GitHub rapid

1. Creeaza un repository nou pe GitHub, de exemplu `istorie-clasa-9`.
2. In folderul local ruleaza:

```powershell
git init
git add .
git commit -m "Initial history navigator"
git branch -M main
git remote add origin https://github.com/USERNAME/istorie-clasa-9.git
git push -u origin main
```

Inlocuieste `USERNAME` cu userul tau GitHub.

Pentru urmatoarele modificari:

```powershell
git add .
git commit -m "Update history navigator"
git push
```

## Coolify + GitHub

In Coolify:

1. Create New Resource.
2. Alege GitHub / Public Repository sau GitHub App pentru repo privat.
3. Selecteaza repository-ul.
4. Alege build pack `Static`.
5. Seteaza Base Directory la `/site`.
6. Adauga domeniul.
7. Deploy.

Conform documentatiei Coolify, Static Build Pack serveste fisiere HTML/CSS/JS deja construite prin Nginx, iar pentru repo-uri GitHub poti folosi repo public, GitHub App sau deploy key.
