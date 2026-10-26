[English](README.md) | **Deutsch**

# Profitabilitätstreiber analysieren: Preis, Menge und Mix

**Die Veränderungen hinter einem Margenergebnis erklären, damit das Management gezielt nachfragen kann.**

Summen im Vergleich von Ist und Erwartung können grosse, gegenläufige Veränderungen über Länder und Produktsegmente hinweg verdecken. Finance muss die wesentlichen Beiträge erkennen, bevor die Vertriebsteams nach einer geschäftlichen Erklärung gefragt werden.

**Mein Beitrag:** Ich entwickelte den wiederkehrenden Analyse- und Reporting-Ablauf weiter: von Excel und Power Query zu Python-Berechnungen, einer hierarchiebasierten Auswahl der Ergebnistreiber und Datenübergaben für das Reporting. Ich definierte, wann eine tiefere Analyse nötig ist, welche gegenläufigen Effekte erhalten bleiben und wie sich jede Aussage auf ihre Eingaben zurückführen lässt.

**Ergebnis und Status:** wiederholbare Analysen und ein erster Entwurf für Management-Kommentare. Dieses Repository enthält die öffentliche Kommentierungslogik und ein ausführbares fiktives Beispiel. Es verarbeitet vorberechnete Effekte, bildet jedoch weder die vollständige Berechnungspipeline nach noch ermittelt es geschäftliche Ursachen. Umfang und Interpretation der als «Mix» bezeichneten Restgrösse werden unten erläutert.

[Geschäftliche Fallstudie lesen](https://matthew-bangle-data-portfolio.mattbangle.chatgpt.site/de/work/profitability-driver-analysis) · [Öffentliches Beispiel ausführen](#öffentliches-beispiel-ausführen)

## Eine kleine Nettoveränderung kann die wesentlichen Bewegungen verdecken

Im fiktiven Beispiel liegt Land B nur **€20'000 über der Erwartung**. Dahinter verbessert sich Segment C um **€400'000**, während Segment D um **€380'000 zurückgeht**. Ein Bericht allein auf Länderebene würde beide Bewegungen verdecken.

Die Logik erkennt die gegenläufigen Effekte und ihre Position in der Hierarchie. Das Management kann anschliessend untersuchen, warum sich die Segmente unterschiedlich entwickeln, Länder vergleichen und sein Verständnis von Markttrends hinterfragen. Die Ausgabe liefert einen analytischen Ausgangspunkt. Sie erfindet keine geschäftlichen Ursachen.

## Mein Beitrag und die analytischen Entscheidungen

Ich entwickelte den übergreifenden Ablauf von Power Query und Excel zu Python-Berechnungen, einer hierarchiebasierten Auswahl der Ergebnistreiber und Datenübergaben für das Reporting weiter. Excel-Ausgaben speisten verknüpfte Texte und Diagramme in PowerPoint. Dieses Repository stellt die **Kommentierungslogik**, ihre Regeln und ein ausführbares fiktives Beispiel bereit.

Die wiederkehrende Herausforderung war die Wahl der richtigen Erklärungstiefe: wann eine Produktgruppe genauer zu untersuchen ist, wann die Segmentebene genügt und wann ein Nettoergebnis wichtige gegenläufige Effekte verdeckt.

| Reporting-Bedarf | Gestaltungsentscheidung | Nutzen für Finance und Management |
| --- | --- | --- |
| Ist und Erwartung verstehen | Preis-, Mengen- und Resteffekte trennen | Den Beitrag zur Margenveränderung sichtbar machen |
| Die passende Erklärungstiefe finden | Wesentlichkeits- und Konzentrationsregeln entlang der Hierarchie anwenden | Ein Produkt, Segment oder Land nur dann erläutern, wenn die Daten dies stützen |
| In Nettosummen verdeckte Belastungen erkennen | Wesentliche Verbesserungen und Rückgänge getrennt identifizieren | Gegenläufige Probleme sichtbar halten |
| Wiederkehrende Management-Präsentationen vorbereiten | Einen konsistenten ersten Entwurf und eine Reporting-Datengrundlage erzeugen | Die Prüfzeit für geschäftlichen Kontext und Folgefragen nutzen |
| Eine Aussage hinterfragen | Ausgewählte Hierarchiepfade, Beträge und Regeleinstellungen erhalten | Den Kommentar auf seine Datengrundlage zurückführen |

## Was der Ablauf ermöglichte

Wiederholbare Vorbereitung und ein erster Kommentarentwurf gaben Finance mehr Zeit für die geschäftliche Einordnung und Folgefragen. Eine frühere historische Schätzung bezifferte die Vorbereitung auf etwa 2,5 Stunden, gegenüber rund 30 Sekunden Verarbeitung nach der Aktualisierung der Quellen. Diese Schätzung schliesst Datenaktualisierung und Prüfung aus und ist kein Leistungsbenchmark dieser öffentlichen Demo.

**Die Interpretation ist entscheidend:** Die öffentliche Logik verarbeitet bereits berechnete Effekte. Im untersuchten übergreifenden Ablauf ist «Mix» eine Restgrösse, die auch Kosten- oder Abstimmungseffekte enthalten kann. Sie kann für sich allein keine Verschiebung zu weniger profitablen Produkten nachweisen. Die geschäftliche Erklärung bleibt Aufgabe von Finance.

«CM1» ist die ursprüngliche interne Bezeichnung für den Deckungsbeitrag und bleibt in den Repository- und Codenamen erhalten. Der öffentliche Titel beschreibt die geschäftliche Fragestellung.

## Öffentliches Beispiel ausführen

Python · Excel / Power Query · Management-Reporting

[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-586171?style=flat)](LICENSE)
[![Öffentliche Tests](https://github.com/mattbang/cm1-insight-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/mattbang/cm1-insight-engine/actions/workflows/tests.yml)

Python 3.11 oder 3.12, entsprechend dem öffentlichen Test-Workflow:

```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python demo.py
python -m pytest
```

Die Demo erzeugt Kommentare, eine CSV-Datengrundlage für das Reporting und einen Nachweisdatensatz aus fiktiven Ländern und Produkten. Das [Excel-Beispiel](examples/generated/reporting-feed.xlsx) veranschaulicht die Anordnung der Reporting-Zellen. Es wird separat bereitgestellt und von der Demo nicht neu erzeugt.

## Die Umsetzung nachvollziehen

[Erzeugte Kommentare lesen](examples/generated/management-commentary.md) · [Präsentation mit fünf Folien](assets/CM1_Insight_Engine_Showcase.pdf)

![Synthetischer Management-Bericht mit Wasserfalldiagrammen zur Profitabilität, Ranglisten und Kommentaren](assets/slides/slide-05.png)

*Fiktive Daten. Diese frühere Reporting-Präsentation veranschaulicht den Darstellungsansatz. Die verlinkten erzeugten Kommentare zeigen die Ausgabe der aktuellen öffentlichen Logik.*

[Auswahllogik](docs/logic.md) · [Code](src/cm1_narratives.py) · [Ein- und Ausgaben](docs/demo.md) · [Validierungsumfang](docs/validation.md) · [Einseitiges Handout](assets/CM1_Insight_Engine_Handout.pdf)

Die vertiefende technische Dokumentation ist auf Englisch.

Die Übernahme von Quelldaten, die vollständige Berechnungspipeline aus dem Produktivbetrieb und aktive PowerPoint-Verknüpfungen gehören nicht zu diesem Paket. Der aktuelle öffentliche Code, die historische Erfahrung und die erhaltenen Präsentationsmaterialien haben jeweils einen anderen Umfang. Alle öffentlichen Beispieldaten sind synthetisch.

[Matthew Bangle](https://www.linkedin.com/in/matthew-bangle/) · [Vollständiges Portfolio](https://matthew-bangle-data-portfolio.mattbangle.chatgpt.site/de/work) · [MIT-Lizenz](LICENSE)
