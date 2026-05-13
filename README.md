# polycontroller

**[English](#english) · [Deutsch](#deutsch)**

---

<a name="english"></a>
## English

A gamepad-to-keyboard converter specialized for **[PolyTrack](https://polytrack.io)**.  
It translates analog stick and trigger input into precise, rapid WASD key pulses — giving you finer control than a standard keyboard while keeping full compatibility with any browser game.

> **How it works:** Instead of holding a key the whole time, polycontroller rapidly taps and releases it. The faster the taps, the harder the turn. At full deflection the key is held continuously — just like a keyboard player would.

---

### Requirements

| | |
|---|---|
| **OS** | Windows 10 / 11 |
| **Python** | 3.10 or newer (3.12 recommended) — [python.org](https://www.python.org/downloads/) |
| **Controller** | Any pygame-compatible gamepad (Xbox, PlayStation, Switch Pro, generic USB) |

> During Python installation, check **"Add Python to PATH"**.

---

### Installation

1. Download or clone this repository
2. Double-click **`install.bat`**
3. Wait for the dependencies to finish installing

That's it. You only need to do this once.

---

### Usage

1. Connect your controller
2. Double-click **`start.bat`**
3. Click **▶ Start** in the app
4. Switch to your browser and open PolyTrack — your controller is now active

> The app runs in the background. Switch back to it at any time to change settings or stop.

---

### Bindings

polycontroller needs to know which button/axis on your controller corresponds to each action.

**On first launch**, the app auto-detects common controllers and applies a preset:

| Controller | Throttle | Brake | Steer | Reset |
|---|---|---|---|---|
| Xbox (One / Series) | RT (axis 5) | LT (axis 4) | Left stick | Y |
| PlayStation (DS4 / DualSense) | R2 (axis 5) | L2 (axis 4) | Left stick | △ |
| Switch Pro Controller | ZR (button 7) | ZL (button 6) | Left stick | X |
| Generic / unknown | Button 7 | Button 6 | Axis 0 | Button 3 |

**To change a binding manually:**
1. Click **Assign** next to the action you want to change
2. Press the button or move the axis on your controller
3. The binding is saved automatically

> **Not sure which index your button has?**  
> Use the **diagnose tool** (see below).

---

### Settings

| Setting | What it does | Default |
|---|---|---|
| **Deadzone** | Ignores tiny stick movements near center. Increase if your car drifts without input. | 0.10 |
| **Full press at** | Stick percentage above which the key is held continuously (no pulsing). | 0.85 |
| **Tap time (ms)** | How long each key press lasts. 16 ms = one browser frame at 60 fps — the minimum the game reliably detects. | 16 |
| **Fine zone** | Shape of the control curve at low stick deflection. Lower = more gentle, higher = more linear. | 0.70 |

**Click on any value number** to type in an exact value instead of using the slider.

**Save** stores your settings to `config.json`. They are loaded automatically next time.  
**↺** resets all settings to defaults (bindings stay).

---

### Live Status

The **bars** show the current duty cycle (how hard the key is pressed, 0–100%) for each direction.  
The **key indicators** (A D W S R) light up green when that keyboard key is actively being pressed.

---

### Diagnose Tool

If your controller is not auto-detected or a binding feels wrong, run **`diagnose.bat`**.

It shows all axes and buttons live in the terminal as you press them:

```
Axes: [0]=+0.00  [1]=-0.02  [2]=+0.00  ...   Btns: [0]=0  [1]=0  [2]=0  ...
```

Move the stick you want to assign → watch which **Axis index** changes.  
Press the button you want → watch which **Button index** flips from `0` to `1`.  
Then enter those numbers via **Assign** in the main app.

---

### Language

Click the **`DE`** / **`EN`** button in the top-right corner of the app to switch between English and German. The preference is saved automatically.

---

### Notes from the developer

- **The curve matters more than you think.** The two-zone curve (fine at 0–50%, aggressive at 50–85%) was tuned by analyzing a world-record PolyTrack run frame by frame. The shape gives you slow, precise corrections at light stick input and immediate full response when you push hard.

- **16 ms is the magic number.** Browser games process input at ~60 fps (one frame = 16.7 ms). A tap shorter than one frame might be missed entirely. Don't go below 16 ms.

- **You don't need to hold the stick at 100%.** The upper threshold (default 85%) means even 85% deflection gives you a continuous keypress. The remaining 15% of stick travel is "wasted" — use that for analog comfort, not game input.

- **If your car drifts on straights:** increase the deadzone slightly (try 0.12–0.15). If steering feels sluggish: lower it.

- **The diagnose tool is your friend.** Every controller reports different axis and button indices. When in doubt, always run `diagnose.bat` first.

- **This tool works for any WASD browser game,** not just PolyTrack. The key mapping is fixed (W/A/S/D/R) but you can adapt it for other games by changing which controller input drives which key in the Bindings section.

---

### License

Free to use and modify. No warranty.  
If you improve it — share it.

---
---

<a name="deutsch"></a>
## Deutsch

Ein Gamepad-zu-Tastatur-Konverter, spezialisiert für **[PolyTrack](https://polytrack.io)**.  
Er übersetzt Analog-Stick- und Trigger-Eingaben in präzise, schnelle WASD-Tastenimpulse — bessere Kontrolle als eine normale Tastatur, aber vollständig kompatibel mit jedem Browser-Spiel.

> **So funktioniert es:** Statt eine Taste dauerhaft zu halten, tippt und lässt polycontroller sie blitzschnell los. Je schneller die Taps, desto stärker die Lenkung. Bei vollem Ausschlag wird die Taste dauerhaft gehalten — genau wie ein Keyboard-Spieler.

---

### Voraussetzungen

| | |
|---|---|
| **Betriebssystem** | Windows 10 / 11 |
| **Python** | 3.10 oder neuer (3.12 empfohlen) — [python.org](https://www.python.org/downloads/) |
| **Controller** | Jedes pygame-kompatibles Gamepad (Xbox, PlayStation, Switch Pro, generisches USB) |

> Bei der Python-Installation **„Add Python to PATH"** anhaken.

---

### Installation

1. Repository herunterladen oder klonen
2. **`install.bat`** doppelklicken
3. Warten bis die Abhängigkeiten installiert sind

Nur einmal nötig.

---

### Verwendung

1. Controller anschließen
2. **`start.bat`** doppelklicken
3. Im Programm auf **▶ Start** klicken
4. Browser öffnen und PolyTrack laden — der Controller ist jetzt aktiv

> Das Programm läuft im Hintergrund. Jederzeit zurückwechseln zum Ändern von Einstellungen oder Stoppen.

---

### Tastenbelegung

polycontroller muss wissen, welche Taste / Achse am Controller welcher Aktion entspricht.

**Beim ersten Start** erkennt das Programm bekannte Controller automatisch:

| Controller | Gas | Bremse | Lenken | Neustart |
|---|---|---|---|---|
| Xbox (One / Series) | RT (Achse 5) | LT (Achse 4) | Linker Stick | Y |
| PlayStation (DS4 / DualSense) | R2 (Achse 5) | L2 (Achse 4) | Linker Stick | △ |
| Switch Pro Controller | ZR (Button 7) | ZL (Button 6) | Linker Stick | X |
| Generisch / unbekannt | Button 7 | Button 6 | Achse 0 | Button 3 |

**Belegung manuell ändern:**
1. Neben der gewünschten Aktion auf **Belegen** klicken
2. Die Taste drücken oder die Achse bewegen
3. Die Belegung wird automatisch gespeichert

> **Unsicher welcher Index die Taste hat?**  
> Das **Diagnose-Tool** hilft (siehe unten).

---

### Einstellungen

| Einstellung | Funktion | Standard |
|---|---|---|
| **Deadzone** | Kleine Stick-Bewegungen in der Mitte ignorieren. Erhöhen wenn das Auto ohne Eingabe driftet. | 0.10 |
| **Vollgas ab** | Ab welchem Stick-Prozentsatz die Taste dauerhaft gehalten wird (kein Pulsieren mehr). | 0.85 |
| **Tap-Dauer (ms)** | Wie lange jeder Tastendruck dauert. 16 ms = ein Browser-Frame bei 60 fps — das Minimum, das das Spiel zuverlässig erkennt. | 16 |
| **Fein-Zone** | Form der Steuerkurve bei kleinem Stick-Ausschlag. Niedriger = sanfter, höher = linearer. | 0.70 |

**Auf die Zahl klicken** um einen genauen Wert einzutippen statt den Slider zu nutzen.

**Speichern** schreibt die Einstellungen in `config.json`. Werden beim nächsten Start automatisch geladen.  
**↺** setzt alle Einstellungen zurück (Tastenbelegung bleibt).

---

### Live Status

Die **Balken** zeigen den aktuellen Duty-Cycle (wie stark die Taste gedrückt wird, 0–100%) für jede Richtung.  
Die **Tasten-Anzeigen** (A D W S R) leuchten grün wenn diese Tastaturtaste gerade aktiv gedrückt wird.

---

### Diagnose-Tool

Wenn der Controller nicht erkannt wird oder eine Belegung falsch wirkt, **`diagnose.bat`** ausführen.

Es zeigt alle Achsen und Buttons live im Terminal:

```
Axes: [0]=+0.00  [1]=-0.02  [2]=+0.00  ...   Btns: [0]=0  [1]=0  [2]=0  ...
```

Den gewünschten Stick bewegen → beobachten welcher **Achsen-Index** sich ändert.  
Die gewünschte Taste drücken → beobachten welcher **Button-Index** von `0` auf `1` springt.  
Diese Nummern dann über **Belegen** in der Hauptanwendung eintragen.

---

### Sprache

Den **`DE`** / **`EN`** Knopf oben rechts anklicken um zwischen Englisch und Deutsch zu wechseln. Die Einstellung wird automatisch gespeichert.

---

### Hinweise vom Entwickler

- **Die Kurve ist entscheidender als man denkt.** Die Zweizonen-Kurve (fein bei 0–50%, aggressiv bei 50–85%) wurde durch Frame-für-Frame-Analyse eines Weltrekord-Runs in PolyTrack abgestimmt. Sie gibt präzise, langsame Korrekturen bei leichtem Stick-Ausschlag und sofortige volle Reaktion beim Durchdrücken.

- **16 ms ist die magische Zahl.** Browser-Spiele verarbeiten Eingaben mit ~60 fps (ein Frame = 16,7 ms). Ein Tap kürzer als ein Frame wird möglicherweise komplett ignoriert. Nicht unter 16 ms gehen.

- **Den Stick nicht auf 100% drücken müssen.** Der obere Schwellenwert (Standard 85%) bedeutet: bereits bei 85% Ausschlag wird die Taste dauerhaft gehalten. Die restlichen 15% Weg sind „verschenkt" — für analogen Komfort nutzen, nicht für Spieleingabe.

- **Wenn das Auto auf Geraden driftet:** Deadzone leicht erhöhen (0.12–0.15 ausprobieren). Wenn die Lenkung träge wirkt: senken.

- **Das Diagnose-Tool ist dein Freund.** Jeder Controller meldet andere Achsen- und Button-Indizes. Im Zweifel immer zuerst `diagnose.bat` starten.

- **Funktioniert für jedes WASD-Browser-Spiel,** nicht nur PolyTrack. Die Tastenbelegung ist fest (W/A/S/D/R), aber du kannst anpassen welche Controller-Eingabe welche Taste steuert.

---

### Lizenz

Frei verwendbar und veränderbar. Keine Gewährleistung.  
Wenn du es verbesserst — teile es.
