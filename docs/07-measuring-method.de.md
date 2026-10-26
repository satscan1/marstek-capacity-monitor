# 07 – Wie der Monitor misst

*[English](07-measuring-method.md) · [Nederlands](07-measuring-method.nl.md)*

## Kann man die Kapazität auch messen, wenn die Batterie zwischendurch lädt?

Der Monitor misst nur bei einer vollständigen Entladung (von 95 % oder mehr auf 15 % oder weniger). Geht das nicht schlauer, indem man Laden und Entladen zwischendurch auseinanderhält? Um das herauszufinden, wurden fast ein Jahr lang Daten von zwei Venus E ausgewertet (Dezember 2025 – Oktober 2026). Fazit: Technisch geht es, aber du misst damit die Kapazität nicht zuverlässig. Die Grenze liegt im Ladezustandsmesser (SOC) der Batterie selbst.

### AC oder DC spielt hier keine Rolle
Der Monitor misst auf der Batterieseite (DC). Zur Kontrolle: Bei jeder vollständigen Entladung lag AC heraus geteilt durch DC heraus immer bei 0,84–0,87. Die DC-Messung stimmt also.

### Was die Daten zeigen
- **Laden und Entladen netto zusammenzählen ist ungenau.** Im mittleren Bereich kostet Laden etwa 54 Wh pro Prozent, Entladen liefert etwa 50 Wh. Mischt man beides, ist der Fehler so groß wie der Verschleiß, den man sucht (bei den Testbatterien etwa 3 % in anderthalb Jahren).
- **Nur die Entladeabschnitte zu zählen ist zu unruhig.** Selbst in ruhigen Monaten schwankt der mittlere Bereich von Woche zu Woche zwischen 46 und 53 Wh pro Prozent. Das sind ± 5 %, während der Verschleiß 1,5–2 % pro Jahr beträgt.
- **Die Batterie meldet immer 5,12 kWh als Gesamtkapazität**, auch ein Exemplar, das über zwei Jahre alt ist. Ein Prozent ist also das, was die Batterie selbst ein Prozent nennt, keine feste Energiemenge aus den Zellen.
- **Der SOC-Messer kann sich wochenlang verschieben.** Von Ende März bis Ende April lieferte eine Batterie pro Prozent 15–30 % weniger Energie. Das galt im mittleren Bereich und über eine vollständige Entladung (3,1–3,9 kWh statt etwa 4,2). Die AC-Messung bestätigte es. Danach war es wieder normal.

### Warum es (noch) keine gute Lösung gibt
Für eine saubere Messung braucht man zwei echte Bezugspunkte: wirklich voll und wirklich leer. Voll klappt, denn dort stellt die Batterie ihren Zähler selbst richtig. Leer klappt nicht: Die Batterie stoppt an der Entladegrenze aus der App, also bei einem SOC-Prozentsatz und nicht bei einer Spannung. Und im mittleren Bereich ist die Spannung von LiFePO4 zu flach, um als Bezugspunkt zu dienen.

### Was der Monitor deshalb tut
Er misst nur bei vollständigen Entladungen und zeigt den Median der letzten drei. Eine Messung bekommt einen offenen Punkt (weniger zuverlässig), wenn es keinen aktuellen Bezugspunkt gab, die Zellen kalt waren oder die Ränder auffällig sind. Er bleibt ein Hilfsmittel und kein Beweis, aber das Beste, was mit dem SOC der Batterie möglich ist.

## Warum eine Batterie über 100 % liegen kann

Marstek rechnet die Kapazität auf dem Typenschild mit 3,2 V pro Zelle: 16 Zellen × 3,2 V × 100 Ah = 5,12 kWh. In Wirklichkeit liegt die Spannung beim Entladen um 52–53 V. Pro Prozent kommt deshalb etwa 2 % mehr Energie heraus, als das Typenschild sagt. Das ist eine Rechenkonvention, keine versteckte Reserve: diese Energie bekommst du schon jetzt. Das ist bei allen so und bleibt gleich, für den Rückgang über die Zeit spielt es also keine Rolle. Deshalb korrigiert der Monitor bewusst nicht dafür. Außerdem liefern neue Zellen oft etwas mehr als das Typenschild.

Die echte Reserve ist die Entladetiefe: die Batterie nutzt etwa 90 % ihrer Zellen (manche Exemplare 88 %). Der unterste Teil bleibt ungenutzt.

## Wie sicher ist der Wert auf der Karte?

- **Über 100 %:** grau mit „vorläufig", bis **5 Messungen hintereinander** über 100 % liegen, höchstens 3 Punkte auseinander. Danach grün mit „über neu".
- **Plötzlich mehr als 5 Punkte tiefer:** grau mit „noch nicht bestätigt". Echter Verschleiß geht langsam; so ein Sprung ist fast immer eine vorübergehend verschobene SOC-Anzeige (siehe oben). Bleibt der tiefere Wert 5 Messungen hintereinander, gilt er als echt. Erholt er sich, verschwindet der Hinweis von selbst.
- **Seit Beginn der Messung:** die Veränderung gegenüber dem Mittelwert der ersten 3 Messungen dieses Monitors. So spielt es keine Rolle, ob eine Batterie bei 96 % oder bei 105 % begann.
