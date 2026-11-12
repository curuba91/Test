"""Vorabcheck und Prompt-Generator auf Basis von validation_rules.json (Kapitel 10).

Der Check ersetzt keine Freigabe. Logik, Risikomatrix, Kontrollen und alle
Texte stehen in ``validation_rules.json``; hier steht nur die Auswertung.

Prüfung des Regelwerks ohne Hub-Start::

    python -B -m hub.validation
"""

import json
import sys
from pathlib import Path

RULES_FILE = "validation_rules.json"
PLACEHOLDER = "PLATZHALTER"
PARTS = {"decision": "Entscheidungslogik", "risk_matrix": "Risikomatrix", "controls": "Kontrollen"}


def load_rules(program_dir):
    """Rückgabe: (Regelwerk oder {}, Liste der Fehler)."""
    path = Path(program_dir) / RULES_FILE
    try:
        with open(path, encoding="utf-8-sig") as handle:
            rules = json.load(handle)
    except FileNotFoundError:
        return {}, [f"{RULES_FILE} fehlt im Programmordner."]
    except json.JSONDecodeError as exc:
        return {}, [f"{RULES_FILE} ist kein gültiges JSON (Zeile {exc.lineno}, Spalte {exc.colno}): {exc.msg}"]
    except OSError as exc:
        return {}, [f"{RULES_FILE} ist nicht lesbar: {exc}"]
    errors = check_rules(rules)
    return (rules if not errors else {}), errors


def check_rules(rules) -> list:
    errors = []
    if not isinstance(rules, dict):
        return ["Die Datei muss ein JSON-Objekt enthalten."]
    if not isinstance(rules.get("rules_version"), str) or not rules["rules_version"].strip():
        errors.append("rules_version fehlt.")
    questions = rules.get("questions")
    if not isinstance(questions, list) or not questions:
        return errors + ["questions fehlt oder ist leer."]
    options = {}
    for index, question in enumerate(questions):
        if not isinstance(question, dict) or not question.get("key") or not question.get("text"):
            errors.append(f"questions[{index}]: key oder text fehlt.")
            continue
        keys = [o.get("key") for o in question.get("options", []) if isinstance(o, dict)]
        if not keys or len(set(keys)) != len(keys):
            errors.append(f"questions[{index}] ({question['key']}): options fehlen oder sind doppelt.")
        if question["key"] in options:
            errors.append(f"questions[{index}]: key '{question['key']}' kommt mehrfach vor.")
        options[question["key"]] = set(keys)
    results = rules.get("results")
    if not isinstance(results, dict) or not results:
        return errors + ["results fehlt oder ist leer."]
    for key, entry in results.items():
        if not isinstance(entry, dict) or not entry.get("label") or not entry.get("text"):
            errors.append(f"results.{key}: label oder text fehlt.")

    def check_conditions(where, conditions):
        for name, values in (conditions or {}).items():
            if name not in options:
                errors.append(f"{where}: unbekannte Frage '{name}'.")
            elif not isinstance(values, list) or not set(values) <= options[name]:
                errors.append(f"{where}: unbekannte Antwort bei '{name}'.")

    for question in questions:
        if isinstance(question, dict) and question.get("key"):
            check_conditions(f"questions.{question['key']}.hide_if", question.get("hide_if"))
    decision = rules.get("decision")
    entries = decision.get("rules") if isinstance(decision, dict) else None
    if not isinstance(entries, list) or not entries:
        errors.append("decision.rules fehlt oder ist leer.")
    else:
        for index, entry in enumerate(entries):
            where = f"decision.rules[{index}]"
            if not isinstance(entry, dict) or entry.get("result") not in results:
                errors.append(f"{where}: result fehlt oder ist kein Schlüssel aus results.")
                continue
            check_conditions(where, entry.get("if"))
            for name in entry.get("if_unclear", []):
                if name not in options:
                    errors.append(f"{where}: unbekannte Frage '{name}' in if_unclear.")
        if isinstance(entries[-1], dict) and (entries[-1].get("if") or entries[-1].get("if_unclear")):
            errors.append("decision.rules: Die letzte Regel muss ohne Bedingung sein, damit immer ein Ergebnis entsteht.")
    matrix = rules.get("risk_matrix")
    if not isinstance(matrix, dict) or not isinstance(matrix.get("values"), dict):
        errors.append("risk_matrix.values fehlt.")
    controls = rules.get("controls")
    if not isinstance(controls, dict) or not isinstance(controls.get("by_capability"), dict):
        errors.append("controls.by_capability fehlt.")
    prompt = rules.get("prompt")
    if not isinstance(prompt, dict) or not prompt.get("de") or not prompt.get("en"):
        errors.append("prompt.de oder prompt.en fehlt.")
    for part in PARTS:
        if isinstance(rules.get(part), dict) and rules[part].get("status") not in (PLACEHOLDER, "FEST", "VORSCHLAG"):
            errors.append(f"{part}.status muss PLATZHALTER, VORSCHLAG oder FEST sein.")
    return errors


def incomplete_parts(rules) -> list:
    return [label for part, label in PARTS.items()
            if isinstance(rules.get(part), dict) and rules[part].get("status") == PLACEHOLDER]


def _answer(answers, key):
    value = answers.get(key)
    return value if value not in (None, "", []) else None


def evaluate(rules, answers) -> dict:
    """Wertet die Antworten aus. Ausgeblendete Fragen zählen nicht."""
    unclear = (rules.get("unclear") or {}).get("key", "unklar")
    answers = dict(answers or {})
    visible = []
    for question in rules["questions"]:
        hidden = any(_answer(answers, name) in values for name, values in (question.get("hide_if") or {}).items())
        if hidden:
            answers.pop(question["key"], None)
        else:
            visible.append(question["key"])

    def is_unclear(key):
        return key in visible and _answer(answers, key) in (None, unclear)

    result = None
    for entry in rules["decision"]["rules"]:
        if all(_answer(answers, name) in values for name, values in (entry.get("if") or {}).items()) \
                and ("if_unclear" not in entry or any(is_unclear(name) for name in entry["if_unclear"])):
            result = entry["result"]
            break

    missing = incomplete_parts(rules)
    risk = None
    consequence, influence = _answer(answers, "entscheidungsfolge"), _answer(answers, "modelleinfluss")
    if consequence and influence and unclear not in (consequence, influence):
        value = rules["risk_matrix"]["values"].get(consequence, {}).get(influence)
        risk = value if value and value != PLACEHOLDER else None
    controls = []
    capabilities = answers.get("faehigkeiten") if isinstance(answers.get("faehigkeiten"), list) else []
    for capability in capabilities:
        for control in rules["controls"]["by_capability"].get(capability, []):
            if control != PLACEHOLDER and control not in controls:
                controls.append(control)
    entry = rules["results"][result]
    return {
        "result": result, "label": entry["label"], "text": entry["text"], "risk": risk, "controls": controls,
        "incomplete": bool(missing), "incomplete_parts": missing, "visible": visible, "answers": answers,
        "rules_version": rules["rules_version"],
    }


def _answer_lines(rules, answers, lang) -> str:
    suffix = "_en" if lang == "en" else ""
    unclear = rules.get("unclear") or {}
    lines = []
    for question in rules["questions"]:
        if question["key"] not in answers:
            continue
        labels = {o["key"]: o.get(f"label{suffix}") or o["label"] for o in question["options"]}
        labels[unclear.get("key", "unklar")] = unclear.get(f"label{suffix}") or unclear.get("label", "unklar")
        value = answers[question["key"]]
        shown = ", ".join(labels.get(v, v) for v in value) if isinstance(value, list) else labels.get(value, value)
        lines.append(f"{question.get('nr', '')}. {question.get(f'text{suffix}') or question['text']} – {shown or '–'}")
    return "\n".join(lines)


def build_prompt(rules, usecase, evaluation, lang="de") -> str:
    """Prompt zum Kopieren. Er wird manuell im freigegebenen GenAI-Tool ausgeführt (X15: kein API-Aufruf)."""
    lang = "en" if lang == "en" else "de"
    result = rules["results"][evaluation["result"]]
    empty = "(not provided)" if lang == "en" else "(nicht angegeben)"
    values = {
        "id": usecase.get("id", ""), "title": usecase.get("title") or empty,
        "description": usecase.get("description") or empty, "benefit": usecase.get("benefit") or empty,
        "answers": _answer_lines(rules, evaluation["answers"], lang),
        "result": (result.get("label_en") if lang == "en" else None) or result["label"],
        "notice": rules.get("notice", {}).get(lang, ""),
    }
    text = rules["prompt"][lang]
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    program_dir = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    rules, errors = load_rules(program_dir)
    print(f"Prüfung von {program_dir / RULES_FILE}")
    for text in errors:
        print(f"  FEHLER  {text}")
    if errors:
        print(f"Ergebnis: {len(errors)} Fehler – der Vorabcheck ist damit nicht nutzbar.")
        return 1
    for label in incomplete_parts(rules):
        print(f"  OFFEN   {label}: Status PLATZHALTER")
    print(f"Ergebnis: gültig, Version {rules['rules_version']}, {len(incomplete_parts(rules))} offene Teile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
