# 06 – Dashboard: Aufteilung, Karte und Galerie

*[English](06-dashboard-gallery.md) · [Nederlands](06-dashboard-gallery.nl.md)*

Auf dieser Seite siehst du, wie die Karten bei 1 bis 6 Batterien aussehen, was jeder Teil der Batteriekarte bedeutet und wie du die Karten anordnest.

> Alle Bilder auf dieser Seite verwenden **Demodaten**: sechs erfundene Batterien mit unterschiedlichem Alter und Zustand. Sie zeigen, wie die Karten aussehen, nicht wie eine echte Batterie altert. Die Karten erscheinen auf Deutsch, wenn Home Assistant auf Deutsch eingestellt ist.

## Aufteilung

Die Batteriekarte ist für **ein Drittel der Breite** gemacht: drei Batterien nebeneinander.

| Anzahl Batterien | Aufteilung |
|---|---|
| 1 oder 2 | Die Batterien, rechts daneben die Übersicht (eine Reihe mit drei Karten) |
| 3 | Übersicht zwei Drittel breit, darunter 3 Batterien |
| 4 | Übersicht zwei Drittel breit, darunter 2 × 2 |
| 5 | Übersicht zwei Drittel breit, darunter 3 + 2 |
| 6 | Übersicht zwei Drittel breit, darunter 3 + 3 |

Ab 3 Batterien ist neben der Übersicht ein Drittel frei für eine eigene Karte. Lässt du den Platz leer, schiebt Home Assistant die erste Batterie nach oben neben die Übersicht; sollen die Batterien in einer neuen Reihe beginnen, setze dort eine Karte hin (das Dashboard mit einem Klick und die fertigen Dashboards verwenden eine Textkarte „Freier Platz“).

Das [Dashboard mit einem Klick](01-installation.de.md#am-schnellsten-dashboard-mit-einem-klick) verwendet diese Aufteilung von selbst. Für button-card gibt es [fertige Dashboards](01-installation.de.md#fertiges-dashboard-mit-button-card), eines für jede Batterieanzahl.

Selbst anordnen? Verwende den Ansichtstyp **Abschnitte** (Sections) von Home Assistant. Ein Beispiel steht in [`dashboard/button-card/layout-sections.yaml`](../dashboard/button-card/layout-sections.yaml). Jede Karte bekommt ihre Breite über `grid_options`: in einem Abschnitt mit drei Spalten ist `columns: 12` ein Drittel und `columns: 24` zwei Drittel. Bei 4 Batterien nimm `columns: 18` pro Batterie.

## Die Batteriekarte

![Batteriekarte mit Nummern](../screenshots/gallery/de/card-numbered-de.png)

1. **Status**: *Gut*, *Unter Herstellerangabe*, *An Marstek melden (App)* oder *Sammelt Daten*. Die Farbe folgt der letzten Messung.
2. **Diagramm**: Drücke auf diese kleine Schaltfläche, um das Diagramm zu öffnen, und noch einmal, um es zu schließen. Der Rest der Karte reagiert nicht auf Klicks.
3. **Zeitraum**: *jüngste 3 Jahre der Garantiezeit*: Das Diagramm zeigt die jüngsten 3 Jahre seit der Inbetriebnahme.
4. **Diagramm**: Jeder Punkt ist ein Monat, mit dem Prozentsatz der nutzbaren Kapazität, der damals noch vorhanden war. Die graue gestrichelte Linie zeigt, was der Hersteller in diesem Alter erwartet, die rote Linie liegt bei 75 %. Fährst du mit der Maus über einen Punkt, siehst du den genauen Wert und die Zelltemperatur in diesem Monat (wenn du Temperatursensoren verknüpft hast).
5. **Wie liest man das?** Eine kurze Erklärung unter dem Diagramm: Achte darauf, dass die Punkte nahe an oder über der grauen Linie bleiben. Ein langsamer Rückgang ist normal; sinken sie in Richtung der roten Linie, melde es an Marstek.
6. **Läuft die Messung?** Grün: Die Messung läuft, mit der Zahl der gemessenen vollständigen Entladungen. Blau: sammelt noch Daten. Orange oder rot: keine neuen Daten oder ein Sensor fehlt. Die Zeile darunter nennt den nächsten Schritt (zum Beispiel *auf 95 % voll laden*).
7. **Drei Kapazitäten**: *Nennwert* (auf dem Typenschild), *Nutzbar* (Nennwert abzüglich der Reserve, die die Batterie selbst behält) und *Gemessen* (was jetzt wirklich herauskommt, und wie viel Prozent der nutzbaren Kapazität das sind).
8. **Balken**: die gemessene Kapazität, mit einem weißen Strich für die Herstellerangabe und einem roten Strich bei 75 %.
9. **Herstellerangabe** bei der aktuellen Zyklenzahl und dem Alter, und der Abstand: wie weit du darüber (+) oder darunter (−) liegst.
10. **Trend pro Monat**: zuerst die Richtung (▲ ▬ ▼), dann die Monate von neu nach alt. Große Zahl = gemessen, kleine Zahl = Herstellerangabe für diesen Monat, dazu die Zelltemperatur, falls vorhanden.
11. **Letzte vollständige Entladung und Ladung**, und die Anzahl der Messungen.

Hast du Sensoren für die höchste und niedrigste Zellspannung verknüpft, erscheint unter dem Trend die **Zellspannungsdifferenz nach Vollladung** (siehe Demo 2 in der Galerie).

## Die Übersicht

Die Übersicht zeigt alle Batterien (bis 6) untereinander:

- **Batterie**: mit ✓ (Messung läuft), ⏳ (sammelt Daten) oder ⚠ (Verbindung prüfen).
- **Trend**: ▲ steigend, ▬ stabil, ▼ fallend über die gezeigten Monate.
- **Jetzt**: die letzte Messung.
- **Monate**, von neu nach alt: große Zahl = gemessen, kleine Zahl = Herstellerangabe für diesen Monat.
- **Herstellerangabe**: was der Hersteller jetzt erwartet.

Grün: höchstens 5 Punkte unter der Herstellerangabe. Orange: darunter. Rot: 75 % oder weniger, über die Marstek-App melden.

## Galerie

Jede der sechs Demobatterien zeigt eine andere Situation:

| Batterie | Situation |
|---|---|
| Demo 1 | 4 Jahre alt, gut |
| Demo 2 | 1,6 Jahre alt, gut, mit Zellspannungsdifferenz |
| Demo 3 | Gerade in Betrieb genommen: sammelt Daten für die erste Messung |
| Demo 4 | 6,5 Jahre alt, unter Herstellerangabe (orange) |
| Demo 5 | 9 Jahre alt, knapp unter 75 %: an Marstek melden (rot) |
| Demo 6 | 2,8 Jahre alt, gut, aber seit einer Weile keine neuen Daten (⚠) |

### 1 Batterie

![1 Batterie](../screenshots/gallery/de/1-batterie.png)
![1 Batterie mit Diagramm](../screenshots/gallery/de/1-batterie-diagramm.png)

### 2 Batterien

![2 Batterien](../screenshots/gallery/de/2-batterien.png)
![2 Batterien mit Diagrammen](../screenshots/gallery/de/2-batterien-diagramm.png)

### 3 Batterien

![3 Batterien](../screenshots/gallery/de/3-batterien.png)
![3 Batterien mit Diagrammen](../screenshots/gallery/de/3-batterien-diagramm.png)

### 4 Batterien

![4 Batterien](../screenshots/gallery/de/4-batterien.png)
![4 Batterien mit Diagrammen](../screenshots/gallery/de/4-batterien-diagramm.png)

### 5 Batterien

![5 Batterien](../screenshots/gallery/de/5-batterien.png)
![5 Batterien mit Diagrammen](../screenshots/gallery/de/5-batterien-diagramm.png)

### 6 Batterien

![6 Batterien](../screenshots/gallery/de/6-batterien.png)
![6 Batterien mit Diagrammen](../screenshots/gallery/de/6-batterien-diagramm.png)

## Demo selbst ausprobieren

Die Karten akzeptieren über die Option `demo` erfundene Daten (bei button-card: die Variable `demo`); die Galerie oben wurde damit erstellt. Diese Daten stehen nur in der Dashboard-Konfiguration: Es werden keine Sensoren angelegt und nichts landet in deinem Verlauf. Für die normale Nutzung brauchst du das nicht.
