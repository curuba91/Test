# Gemba-Frühwarnsystem

Konzeptentwurf für ein standortweites Dokumentations- und Frühwarnsystem für
Gembas und Begehungen in der pharmazeutischen Produktion.

Das System verbindet drei Funktionen, die einzeln wenig Wert haben:

1. **Dokumentation** — jede Begehung, jeder geprüfte Punkt und jeder Befund
   wird als unveränderlicher, kodierter Datensatz festgehalten.
2. **Frühwarnung** — aus den Datensätzen werden Raten gebildet, gegen eine
   rollierende Basislinie gestellt und regelbasiert auf Abweichung geprüft.
3. **Spiegelung** — ein bestätigtes Signal wird mit konkreter Prüfaufgabe und
   Rückmeldepflicht in alle anderen Bereiche getragen.

Bewusste Abgrenzung: Vorfeldsystem, nicht validierungspflichtig. Bei
GMP-Relevanz wird in das validierte QMS eskaliert und die Vorgangsnummer
verlinkt — keine Schattendokumentation.

## Inhalt

- [`docs/gemba-fruehwarnsystem.html`](docs/gemba-fruehwarnsystem.html) —
  vollständiges Konzeptpapier: Zielbild, Datenmodell, Taxonomie, Erfassung,
  Analytik, Signalklassen, Spiegelungs-Regelkreis, Rollen und Taktung,
  Dokumentationskonzept, Technik, KI-Einsatz, Kennzahlen, Fallstricke,
  Einführung in vier Phasen.

## Offene Punkte für die Entscheidungsrunde

- Signalbudget pro Monat (Kalibriergrundlage der Schwellen)
- Aufbewahrungsfrist (Vorschlag: 7 Jahre)
- Kaufen oder bauen für die Erfassungskomponente
- Besetzung der Rolle Taxonomie-Pflege
