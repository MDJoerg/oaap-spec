#!/usr/bin/env python3
"""Sagt der Index dasselbe wie die Spezifikationen? (und rfcs/README.md)

Dieselbe Geschichte wie in `oaap-apps` einen Tag zuvor, an einer anderen
Stelle: Eine Angabe steht an ZWEI Orten -- in der Datei und in der
Liste, die auf sie zeigt -- und nur einer wird beim Aendern angefasst.
Am 22.09.2026 lagen acht von vierzehn Fassungsnummern im Spec-Index
falsch, eine davon fuenf Nebenfassungen zurueck.

Das faellt niemandem auf, weil der Index niemanden bricht. Er belehrt
nur falsch -- und zwar genau denjenigen, der sich einen Ueberblick
verschaffen will, statt die Datei zu oeffnen.

Geprueft wird nur, was **ableitbar** ist:

    spec/README.md   Fassungsnummer je Eintrag gegen die Datei
    rfcs/README.md   jedes RFC steht im Index, und keiner zu viel

Nicht geprueft wird der beschreibende Text: Er ist eine Zusammenfassung,
keine Kopie, und eine Pruefung, die ihn erzwingt, wuerde nur erzwingen,
dass niemand mehr zusammenfasst.

Aufruf:
    python3 check-specs.py           # nur berichten, Rueckgabe != 0 bei Abweichung
    python3 check-specs.py --fix     # die Fassungsnummern im Index nachziehen
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_INDEX = os.path.join(HERE, "spec", "README.md")
RFC_INDEX = os.path.join(HERE, "rfcs", "README.md")

# `- [id](datei.md) — text (draft, v0.2)` -- die Klammer am Zeilenende
ROW = re.compile(r"^(- \[([\w.]+)\]\((\S+\.md)\)\s+—\s+.*?\()([^)]*)(\)\s*)$")
VER = re.compile(r"\bv([0-9]+(?:\.[0-9]+)*)\b")
FILE_VER = re.compile(r"^- \*\*Version:\*\*\s*([0-9]+(?:\.[0-9]+)*)", re.M)


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def file_version(fn):
    p = os.path.join(HERE, "spec", fn)
    if not os.path.exists(p):
        return None
    m = FILE_VER.search(read(p))
    return m.group(1) if m else None


def check_specs(fix):
    """Fassungsnummern im Index gegen die Dateien.

    Gibt (reparierbar, nicht_reparierbar, anzahl_repariert) zurueck --
    und die Trennung ist keine Formsache. Der erste Entwurf warf alles
    in eine Liste, meldete unter `--fix` auch fuer eine fehlende Zeile
    "nachgezogen" und gab dann 0 zurueck. Also genau das, was
    `check-store.py` einen Tag zuvor beigebracht hat: Eine Pruefung,
    die eine Reparatur behauptet, die sie nicht ausgefuehrt hat, ist
    schlimmer als keine -- sie schliesst den Punkt, statt ihn zu
    zeigen. Was hier niemand automatisch schreiben kann, bleibt offen.
    """
    lines = read(SPEC_INDEX).split("\n")
    problems, unfixable, fixed, seen = [], [], 0, set()
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if not m:
            continue
        head, sid, fn, meta, tail = m.groups()
        seen.add(fn)
        real = file_version(fn)
        if real is None:
            unfixable.append(f"{sid}: {fn} gibt es nicht oder nennt keine "
                             f"Fassung")
            continue
        mv = VER.search(meta)
        if mv is None:
            # Ein Eintrag ohne Fassungsnummer (z.B. "outline") ist keine
            # Abweichung, sondern eine Aussage. Er bekommt aber eine,
            # sobald die Datei eine nennt -- sonst waere "outline" die
            # Stelle, an der der Index still veraltet.
            problems.append(f"{sid}: Index nennt keine Fassung, die Datei "
                            f"sagt v{real}")
            if fix:
                lines[i] = f"{head}{meta}, v{real}{tail}"
                fixed += 1
            continue
        if mv.group(1) != real:
            problems.append(f"{sid}: Index sagt v{mv.group(1)}, "
                            f"die Datei sagt v{real}")
            if fix:
                lines[i] = head + meta[:mv.start(1)] + real \
                    + meta[mv.end(1):] + tail
                fixed += 1
    # Eine Spec, auf die niemand zeigt, ist die andere Haelfte derselben
    # Frage -- und die, die man ohne Zaehlen nie findet.
    for fn in sorted(os.listdir(os.path.join(HERE, "spec"))):
        if fn.endswith(".md") and fn != "README.md" and fn not in seen:
            unfixable.append(f"{fn}: steht in keinem Index-Eintrag -- die "
                             f"Zeile muss ein Mensch schreiben, sie traegt "
                             f"eine Beschreibung")
    if fix and fixed:
        write(SPEC_INDEX, "\n".join(lines))
    return problems, unfixable, fixed


def check_rfcs():
    """Steht jedes RFC im Index, und keines zu viel?"""
    idx = read(RFC_INDEX)
    listed = set(re.findall(r"^- \[RFC-(\d{4})\]", idx, re.M))
    on_disk = {m.group(1) for f in os.listdir(os.path.join(HERE, "rfcs"))
               if (m := re.match(r"RFC-(\d{4})-", f))}
    problems = [f"RFC-{n}: liegt im Ordner, steht nicht im Index"
                for n in sorted(on_disk - listed)]
    problems += [f"RFC-{n}: steht im Index, liegt nicht im Ordner"
                 for n in sorted(listed - on_disk)]
    return problems


def main():
    fix = "--fix" in sys.argv[1:]
    spec_problems, unfixable, fixed = check_specs(fix)
    rfc_problems = check_rfcs()

    print("Fassungsnummern im Spec-Index")
    if not spec_problems and not unfixable:
        print("  alles gleich")
    for p in spec_problems:
        print(f"  {'nachgezogen' if fix else 'ABWEICHUNG'}: {p}")
    for p in unfixable:
        # Auch unter --fix: offen. Siehe check_specs.
        print(f"  OFFEN: {p}")

    print("")
    print("Vollstaendigkeit des RFC-Index")
    if not rfc_problems:
        print("  alles da")
    for p in rfc_problems:
        # Der RFC-Index traegt je Eintrag einen Status in Prosa; den
        # kann nur ein Mensch schreiben. Deshalb hier kein --fix.
        print(f"  ABWEICHUNG: {p}")

    print("")
    if fix and fixed:
        print(f"{fixed} Fassungsnummer(n) im Index nachgezogen.")
    open_left = ((0 if fix else len(spec_problems))
                 + len(unfixable) + len(rfc_problems))
    print("Alles gleich." if not open_left
          else f"{open_left} Stelle(n) offen.")
    return 1 if open_left else 0


if __name__ == "__main__":
    sys.exit(main())
