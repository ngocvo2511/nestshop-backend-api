# E-commerce Backend API — Project Overview

English LaTeX project based on SRS v0.9 and the MVP policies approved on 29 October 2026.

## Contents

1. Project overview, P0/P1/P2 scope and actors.
2. Functional Requirements: 39 individually numbered FR items and their acceptance criteria.
3. Architecture: System Context → Container → Backend Components.
4. Data design using the requested database image.
5. Business workflows, order/payment lifecycles and independent expiration deadlines.
6. Quality, acceptance, testing and remaining integration obligations.
7. All 32 PlantUML sequence diagrams with requirement traceability.

## Build

Open this whole folder in a LaTeX editor, or upload its contents to Overleaf and select `main.tex`. Both **pdfLaTeX** and **XeLaTeX** are supported. All images are included; Java, PlantUML, shell-escape and online rendering are unnecessary when compiling with a complete TeX installation.

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Alternatively use `latexmk -pdf main.tex` or `xelatex main.tex` with reruns. Required packages include iftex, English Babel, geometry, graphicx, booktabs, tabularx, longtable, enumitem, caption, float, fancyhdr and hyperref. XeLaTeX/LuaLaTeX uses fontspec and TeX Gyre fonts. The supplied PDF is built with Tectonic (XeTeX).

## Refresh diagrams

With Python, Java and PlantUML **1.2026.9**, run from this folder:

```powershell
python scripts/render-diagrams.py --plantuml-jar C:/path/to/plantuml-1.2026.9.jar
```

The script validates all 32 repository sources, copies them into `plantuml/sequence`, renders 200-dpi PNGs into `images/sequence`, refreshes the two repository SVGs whose policy labels changed (SEQ-22/25), copies the three original architecture images and `database.png`, and writes the appendix and SHA-256 manifest. Refreshing requires the repository layout; the prepared project compiles independently when copied to Overleaf.

## Evidence limits

The submitted PDF is self-contained and omits repository paths, source citations and build notes. The 60-minute reservation, 20-minute attempt target, safe-URL-reuse/otherwise-conflict policy, shared Staff permissions and email deferral are expressed within the relevant requirements and workflows. VNPay finality and URL validity still require Sandbox integration verification.

See `build-manifest.json` for source/image provenance and `verification.json` for document checks.
