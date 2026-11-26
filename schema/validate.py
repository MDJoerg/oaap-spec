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
case("unbekannte Version 0.99 wird beim Schreiben abgelehnt", app("0.99"), False)
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

print("\n=== 0.5: destinations (oaap.net.destinations 0.1, RFC-0033 Stufe 1) ===")
HTTP_NEED = {"name": "erp", "kind": "http", "purpose": "Auftraege nachschlagen"}
TCP_NEED = {"name": "mail", "kind": "tcp",
            "env": {"host": "SMTP_HOST", "port": "SMTP_PORT",
                    "user": "SMTP_USER", "password": "SMTP_PASSWORD"}}
case("0.5 mit einem http- und einem tcp-Bedarf", app("0.5", destinations=[HTTP_NEED, TCP_NEED]), True)
case("0.4 darf destinations nicht nutzen", app("0.4", destinations=[HTTP_NEED]), False)
case("tcp ohne env wird abgelehnt -- nur die Erklaerung nennt die Felder",
     app("0.5", destinations=[{"name": "mail", "kind": "tcp"}]), False)
case("http mit env wird abgelehnt -- dort gibt es nichts zu uebergeben",
     app("0.5", destinations=[dict(HTTP_NEED, env={"host": "X"})]), False)
case("unbekannte Art wird abgelehnt", app("0.5", destinations=[{"name": "x1", "kind": "smb"}]), False)

print("\n=== 0.6: authorization (oaap.core.authorization 0.1, RFC-0045) ===")
AUTHZ = {
    "objects": [{"key": "team", "title": "Mannschaft",
                 "activities": ["read", "edit_lineup"],
                 "fields": [{"key": "team", "context": "Mannschaft"},
                            {"key": "area", "values": ["news", "sponsoring"]}]}],
    "role_templates": [{"key": "trainer", "title": "Trainer/in",
                        "grants": [{"object": "team", "activities": ["read"],
                                    "team": "$context"}],
                        "may_grant": ["trainer"]}],
}
case("0.6 mit Objekten und Rollenvorlagen", app("0.6", authorization=AUTHZ), True)
case("0.5 darf authorization nicht nutzen", app("0.5", authorization=AUTHZ), False)
case("0.3 darf authorization nicht nutzen", app("0.3", authorization=AUTHZ), False)
case("0.7 gibt es nicht, 0.6 genuegt aber", app("0.6", authorization={}), True)
case("ein Objekt ohne Aktivitaeten wird abgelehnt",
     app("0.6", authorization={"objects": [{"key": "team", "title": "T"}]}), False)
case("ein Objekt ohne Titel wird abgelehnt",
     app("0.6", authorization={"objects": [{"key": "team", "activities": ["read"]}]}), False)
case("ein Schluessel mit Grossbuchstaben wird abgelehnt",
     app("0.6", authorization={"objects": [{"key": "Team", "title": "T", "activities": ["read"]}]}), False)
case("ein unbekannter Schluessel im Objekt wird abgelehnt",
     app("0.6", authorization={"objects": [{"key": "team", "title": "T", "activities": ["read"], "x": 1}]}), False)
case("eine Vorlage ohne Rechte wird abgelehnt",
     app("0.6", authorization={"role_templates": [{"key": "a", "title": "A", "grants": []}]}), False)
case("ein unbekannter Schluessel im Abschnitt wird abgelehnt",
     app("0.6", authorization={"rules": []}), False)
case("administer: true ohne eigene Deklaration (0.3)",
     app("0.6", authorization={"administer": True}), True)
case("administer ist ein Wahrheitswert",
     app("0.6", authorization={"administer": "ja"}), False)
case("administer braucht Manifest 0.6",
     app("0.5", authorization={"administer": True}), False)
def _tpl(**kw):
    t = {"key": "trainer", "title": "Trainer/in",
         "grants": [{"object": "team", "activities": ["read"]}]}
    t.update(kw)
    return {"objects": [{"key": "team", "title": "Mannschaft",
                         "activities": ["read"]}],
            "role_templates": [t]}


case("suggested_group: ein Gruppenpfad (0.4, Spec 2.11)",
     app("0.6", authorization=_tpl(suggested_group="Verein/Trainer")), True)
case("suggested_group: ein einzelnes Segment",
     app("0.6", authorization=_tpl(suggested_group="Trainer")), True)
case("suggested_group: vier Segmente sind zu viel",
     app("0.6", authorization=_tpl(suggested_group="a/b/c/d")), False)
case("suggested_group: ein fuehrender Schraegstrich wird abgelehnt",
     app("0.6", authorization=_tpl(suggested_group="/Verein/Trainer")), False)
case("suggested_group: ein leeres Segment wird abgelehnt",
     app("0.6", authorization=_tpl(suggested_group="Verein//Trainer")), False)
case("suggested_group ist Text",
     app("0.6", authorization=_tpl(suggested_group=["Verein"])), False)

case("cases.submit: true (Manifest 0.9, RFC-0061 §3.2)",
     app("0.9", cases={"submit": True}), True)
case("cases.submit ist ein Wahrheitswert",
     app("0.9", cases={"submit": "ja"}), False)
case("cases braucht Manifest 0.9",
     app("0.8", cases={"submit": True}), False)
case("ein unbekannter Schluessel in cases wird abgelehnt",
     app("0.9", cases={"templates": []}), False)

case("care.rebuild: self (Manifest 0.10, RFC-0071 §15)",
     app("0.10", care={"rebuild": "self"}), True)
case("care.rebuild: release",
     app("0.10", care={"rebuild": "release"}), True)
case("care.rebuild kennt nur zwei Woerter",
     app("0.10", care={"rebuild": "yes"}), False)
case("care braucht Manifest 0.10",
     app("0.9", care={"rebuild": "self"}), False)
case("ein unbekannter Schluessel in care wird abgelehnt",
     app("0.10", care={"window": "night"}), False)

print("\n=== 0.11: mcp / mcp_sources (oaap.apps.runtime 2.32, RFC-0073) ===")
case("0.11 mit einer MCP-Tuer", app("0.11", mcp={"path": "/mcp"}), True)
case("0.11 mit mcp_sources.read", app("0.11", mcp_sources={"read": True}), True)
case("mcp braucht Manifest 0.11", app("0.10", mcp={"path": "/mcp"}), False)
case("mcp_sources braucht Manifest 0.11", app("0.10", mcp_sources={"read": True}), False)
case("mcp ohne path wird abgelehnt", app("0.11", mcp={}), False)
case("mcp.path ohne fuehrenden Schraegstrich wird abgelehnt", app("0.11", mcp={"path": "mcp"}), False)
case("mcp.path mit Abfrage wird abgelehnt", app("0.11", mcp={"path": "/mcp?x=1"}), False)
case("zweite Tuer / fremder Schluessel in mcp wird abgelehnt",
     app("0.11", mcp={"path": "/mcp", "extra": "/b"}), False)
case("mcp_sources.read 'yes' wird abgelehnt", app("0.11", mcp_sources={"read": "yes"}), False)
case("openapi ist reserviert und wird abgelehnt", app("0.11", openapi={"path": "/openapi.json"}), False)

print("\n=== 0.12: mcp_client (oaap.apps.runtime 2.32.3, RFC-0074) ===")
case("0.12 mit mcp_client.use", app("0.12", mcp_client={"use": True}), True)
case("mcp_client braucht Manifest 0.12", app("0.11", mcp_client={"use": True}), False)
case("mcp_client.use 'yes' wird abgelehnt", app("0.12", mcp_client={"use": "yes"}), False)
case("ein unbekannter Schluessel in mcp_client wird abgelehnt",
     app("0.12", mcp_client={"use": True, "act": True}), False)

print("\n=== 0.18: setup / ai_client / ai_gateway (oaap.apps.runtime 2.39, RFC-0104) ===")
case("0.18 mit einer Einrichtungstuer", app("0.18", setup={"path": "/oaap/setup"}), True)
case("0.18 mit ai_client.use und ai_gateway.serve",
     app("0.18", ai_client={"use": True}, ai_gateway={"serve": True}), True)
case("setup braucht Manifest 0.18", app("0.17", setup={"path": "/oaap/setup"}), False)
case("ai_client braucht Manifest 0.18", app("0.17", ai_client={"use": True}), False)
case("ai_gateway braucht Manifest 0.18", app("0.17", ai_gateway={"serve": True}), False)
case("setup ohne path wird abgelehnt", app("0.18", setup={}), False)
case("setup.path / wird abgelehnt", app("0.18", setup={"path": "/"}), False)
case("ein unbekannter Schluessel in setup wird abgelehnt",
     app("0.18", setup={"path": "/oaap/setup", "key": "x"}), False)
case("ai_client.use 'yes' wird abgelehnt", app("0.18", ai_client={"use": "yes"}), False)
case("ai_gateway kennt nur serve", app("0.18", ai_gateway={"serve": True, "use": True}), False)

print("\n=== 0.19: mcp_content (oaap.apps.runtime 2.32.6, RFC-0116) ===")
case("0.19 mit mcp_content.untrusted",
     app("0.19", mcp={"path": "/mcp"}, mcp_content={"untrusted": True}), True)
case("mcp_content braucht Manifest 0.19",
     app("0.18", mcp={"path": "/mcp"}, mcp_content={"untrusted": True}), False)
case("mcp_content.untrusted 'ja' wird abgelehnt",
     app("0.19", mcp={"path": "/mcp"}, mcp_content={"untrusted": "ja"}), False)
case("mcp_content ohne MCP-Tür wird abgelehnt",
     app("0.19", mcp_content={"untrusted": True}), False)

# Bis 2026-11-26 endete das Schema bei 0.19: zwölf echte Manifeste (0.20-0.23)
# fielen durch, und niemand merkte es, weil validate.py nur ohne Dateien lief.
print("\n=== 0.20: assistant_templates (oaap.apps.runtime 2.41, RFC-0119) ===")
case("0.20 mit assistant_templates.path",
     app("0.20", mcp={"path": "/mcp"}, assistant_templates={"path": "assistants/"}), True)
case("assistant_templates braucht Manifest 0.20",
     app("0.19", mcp={"path": "/mcp"}, assistant_templates={"path": "assistants/"}), False)
case("assistant_templates ohne MCP-Tür wird abgelehnt",
     app("0.20", assistant_templates={"path": "assistants/"}), False)
case("assistant_templates.path mit .. wird abgelehnt",
     app("0.20", mcp={"path": "/mcp"}, assistant_templates={"path": "../x"}), False)

print("\n=== 0.21: events (oaap.apps.runtime 2.42, oaap.events.bus, RFC-0127) ===")
EV = {"publishes": [{"type": "app.demo.order.created.v1", "title": "Auftrag angelegt",
                     "schema": "events/order-created.json", "audience": "tenant"}],
      "subscribes": [{"type": "app.cases.case.closed.v1", "why": "Auftrag abschließen"}],
      "endpoint": "/oaap/events"}
case("0.21 mit events", app("0.21", events=EV), True)
case("events braucht Manifest 0.21", app("0.20", events=EV), False)
case("events.publishes ohne schema wird abgelehnt",
     app("0.21", events={"publishes": [{"type": "app.demo.order.created.v1", "title": "x"}]}), False)
case("events.subscribes ohne why wird abgelehnt",
     app("0.21", events={"subscribes": [{"type": "app.cases.case.closed.v1"}]}), False)
case("events-Typ mit zu wenigen Teilen wird abgelehnt",
     app("0.21", events={"subscribes": [{"type": "app.demo.v1", "why": "x"}]}), False)
case("events.audience unbekannt wird abgelehnt",
     app("0.21", events={"publishes": [dict(EV["publishes"][0], audience="alle")]}), False)

print("\n=== 0.22: people (oaap.apps.runtime 2.43, RFC-0126) ===")
case("0.22 mit people.invite", app("0.22", people={"invite": True}), True)
case("people braucht Manifest 0.22", app("0.21", people={"invite": True}), False)
case("people.invite 'ja' wird abgelehnt", app("0.22", people={"invite": "ja"}), False)

print("\n=== 0.23: mcp_store (oaap.apps.runtime 2.32.7, RFC-0121) ===")
case("0.23 mit mcp_store.kind",
     app("0.23", mcp={"path": "/oaap/mcp"}, mcp_store={"kind": "bookstack"}), True)
case("mcp_store braucht Manifest 0.23",
     app("0.22", mcp={"path": "/oaap/mcp"}, mcp_store={"kind": "bookstack"}), False)
case("mcp_store ohne MCP-Tür wird abgelehnt",
     app("0.23", mcp_store={"kind": "bookstack"}), False)
case("mcp_store.kind in Großbuchstaben wird abgelehnt",
     app("0.23", mcp={"path": "/oaap/mcp"}, mcp_store={"kind": "BookStack"}), False)

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
