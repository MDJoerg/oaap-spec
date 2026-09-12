#!/usr/bin/env python3
"""Check oaap-app.schema.json against fixed cases and real manifests.

The schema is an authoring tool (see its own $comment). It fell behind
the runtime once: from manifest 0.3 (RFC-0031 Schritt 2) until
2026-09-12, appctl.py accepted data_model/contributes/consumes while this
schema refused every manifest that used them — and nothing noticed,
because nothing ever ran the schema. This script is that run.

    python schema/validate.py                       # built-in cases only
    python schema/validate.py path/to/oaap-app.yaml ...

Built-in cases state the rules as the specs make them (oaap.apps.runtime
2.2/2.10/2.16, oaap.data.model 0.1 §2.2/§2.8); each named file must
validate. Needs 'jsonschema' and 'pyyaml'. Exit code 0 = all good.
"""
import copy
import json
import os
import sys

import jsonschema
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "oaap-app.schema.json"), encoding="utf-8") as f:
    SCHEMA = json.load(f)
jsonschema.Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

fails = 0


def errors(doc):
    return sorted(e.message for e in VALIDATOR.iter_errors(doc))


def case(label, doc, valid):
    global fails
    errs = errors(doc)
    good = (not errs) if valid else bool(errs)
    fails += not good
    print(f"{'PASS' if good else 'FAIL'}  {label}")
    if not good:
        print("      " + ("; ".join(errs)[:400] if errs else "accepted, but should be refused"))


APP = {
    "oaap_manifest": "0.1",
    "app": {"id": "demo-app", "name": "Demo", "version": "1.0.0", "type": "native"},
    "services": {"web": {"build": ".", "port": 8000}},
    "routes": [{"path": "/", "roles": ["user"]}],
    "health": {"path": "/healthz"},
}


def app(version, **extra):
    d = copy.deepcopy(APP)
    d["oaap_manifest"] = version
    d.update(extra)
    return d


DATA_MODEL = {
    "object_types": [{"key": "Customer", "title": "Kunde", "title_plural": "Kunden",
                      "identifying": ["VatId"]}],
    "attribute_types": [{"key": "VatId", "title": "VAT-ID", "value_type": "text"}],
    "group_types": [{"key": "crm.core", "on": "Customer", "attributes": ["VatId"],
                     "relations": ["isContactOf"], "activities": ["PhoneCall"]}],
    "relation_types": [{"key": "isContactOf", "title": "is contact of",
                        "title_inverse": "has contact", "from": "Person",
                        "to": "Customer", "valid": True}],
    "activity_types": [{"key": "PhoneCall", "title": "Phone call", "is_task": False}],
}
ARTEFACT = {
    "oaap_manifest": "0.3",
    "app": {"id": "kundenzufriedenheit", "name": "Kundenzufriedenheit", "version": "0.1.0"},
    "data_model": {"group_types": [{"key": "crm.satisfaction", "on": "Firma"}]},
}

print("=== Versionen und Grundform ===")
case("0.1-App ohne Zusaetze", app("0.1"), True)
case("0.2-App mit app.class", app("0.2", app=dict(APP["app"], **{"class": "service"})), True)
case("0.1 darf app.class nicht nutzen", app("0.1", app=dict(APP["app"], **{"class": "service"})), False)
case("unbekannte Version 0.5 wird beim Schreiben abgelehnt", app("0.5"), False)
case("eine App ohne app.type wird abgelehnt", app("0.2", app={k: v for k, v in APP["app"].items() if k != "type"}), False)
case("eine App ohne routes wird abgelehnt", {k: v for k, v in app("0.2").items() if k != "routes"}, False)

print("\n=== 0.3: data_model / contributes / consumes (oaap.data.model 0.1 §2.2) ===")
case("0.3-App mit allen drei Abschnitten (Spec-Beispiel)",
     app("0.3", data_model=DATA_MODEL,
         contributes=[{"type": "Customer", "role": "owner", "group": "crm.core"}],
         consumes=[{"type": "Person", "as": "Mitarbeiter", "fields": ["reference", "Email"]}]),
     True)
case("0.2 darf data_model nicht nutzen", app("0.2", data_model=DATA_MODEL), False)
case("0.2 darf contributes nicht nutzen", app("0.2", contributes=[{"type": "Customer"}]), False)
case("0.2 darf consumes nicht nutzen", app("0.2", consumes=[{"type": "Person"}]), False)
case("0.4 darf die 0.3-Abschnitte nutzen", app("0.4", consumes=[{"type": "Person"}]), True)
case("contributor ohne group wird abgelehnt",
     app("0.3", contributes=[{"type": "Customer", "role": "contributor"}]), False)
case("contributor mit group ist gueltig",
     app("0.3", contributes=[{"type": "Customer", "role": "contributor", "group": "raci.assignments"}]), True)
case("owner ohne role-Angabe ist gueltig (Voreinstellung owner)",
     app("0.3", contributes=[{"type": "Customer"}]), True)
case("unbekannte role wird abgelehnt",
     app("0.3", contributes=[{"type": "Customer", "role": "reader"}]), False)
case("Gruppenschluessel ohne Punkt wird abgelehnt",
     app("0.3", data_model={"group_types": [{"key": "crmcore", "on": "Customer"}]}), False)
case("Typschluessel mit Punkt wird abgelehnt",
     app("0.3", data_model={"object_types": [{"key": "crm.Customer"}]}), False)
case("unbekannter value_type wird abgelehnt",
     app("0.3", data_model={"attribute_types": [{"key": "Score", "value_type": "float"}]}), False)
case("group_type ohne 'on' wird abgelehnt",
     app("0.3", data_model={"group_types": [{"key": "crm.core"}]}), False)
case("relation_type ohne 'to' wird abgelehnt",
     app("0.3", data_model={"relation_types": [{"key": "isContactOf", "from": "Person"}]}), False)
case("Tippfehler in data_model wird abgelehnt (strenges Autorenschema)",
     app("0.3", data_model={"object_type": [{"key": "Customer"}]}), False)
case("'on' unquotiert (YAML macht daraus true) faellt auf",
     app("0.3", data_model=yaml.safe_load("group_types:\n  - key: crm.core\n    on: Customer\n")),
     False)

print("\n=== 0.3: das data_models-Artefakt (oaap.data.model 0.1 §2.8) ===")
case("Artefakt: app + data_model, sonst nichts", ARTEFACT, True)
case("Artefakt mit app.type wird abgelehnt",
     dict(ARTEFACT, app=dict(ARTEFACT["app"], type="native")), False)
case("Artefakt mit routes wird abgelehnt",
     dict(ARTEFACT, routes=[{"path": "/", "roles": ["user"]}]), False)
case("Artefakt mit storage wird abgelehnt",
     dict(ARTEFACT, storage=[{"name": "data", "mount": "/data"}]), False)
case("Artefakt mit health wird abgelehnt", dict(ARTEFACT, health={"path": "/"}), False)
case("Artefakt mit contributes wird abgelehnt (es wird nie eine Instanz)",
     dict(ARTEFACT, contributes=[{"type": "Firma"}]), False)
case("ohne data_model UND ohne services ist es keine gueltige Form",
     {"oaap_manifest": "0.3", "app": ARTEFACT["app"]}, False)
case("0.2 kann kein Artefakt sein (data_model erst ab 0.3)",
     dict(ARTEFACT, oaap_manifest="0.2"), False)

print("\n=== 0.4: launchpad (RFC-0036) ===")
case("0.4 mit launchpad", app("0.4", launchpad={"group": "Werkzeuge", "embeddable": False}), True)
case("0.3 darf launchpad nicht nutzen", app("0.3", launchpad={"group": "Werkzeuge"}), False)

files = sys.argv[1:]
if files:
    print("\n=== echte Manifeste ===")
for path in files:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    case(path, doc, True)

print()
print("ALLE PRUEFUNGEN BESTANDEN" if not fails else f"{fails} PRUEFUNG(EN) FEHLGESCHLAGEN")
sys.exit(1 if fails else 0)
