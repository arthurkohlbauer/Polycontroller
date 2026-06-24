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
| **Python** | 3.10 or newer (3.13 recommended) — [python.org](https://www.python.org/downloads/) |
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

PolyTrack steering is **binary** — a key is either full-lock or off. Analog feel comes purely from *how fast you tap*. polycontroller is built to be tuned to the smallest detail: **every parameter exists once as a global default and again, independently, for each action** (Steer / Throttle / Brake / Reset). That's **28 knobs per action × 5 scopes** plus app-wide options — well over a hundred settings, organised into collapsible sections so the window stays manageable.

#### How it's organised

- **App** — window/runtime options (see below).
- **Global defaults** — the baseline values every action inherits.
- **Per action** (Steer, Throttle, Brake, Reset) — each has its own collapsible panel. Tick **Override defaults** to give that action its own values; leave it off and it follows the globals.
- **Profiles** — save complete setups by name, switch between them instantly, and **Export / Import** them as `.json` to share or back up. Great for different cars, tracks, or controllers.

#### Per-action parameters

| Setting | What it does | Default |
|---|---|---|
| **Enabled** | Turns the action on/off entirely. | on |
| **Invert** | Flips the input direction. | off |
| **Mode** | `pulse` = PWM tapping, `hold` = digital on/off, `toggle` = press latches on/off. | pulse |
| **Center trim** | Shifts the neutral point — fixes a stick that drifts off-center. | 0.00 |
| **Deadzone** | Ignores tiny stick movements near center. Raise if the car drifts without input. | 0.10 |
| **Deadzone type** | `scaled` rescales input past the deadzone smoothly; `hard` cuts it raw. | scaled |
| **Max input at** | Input reaching this counts as 100% (a shorter, snappier stick throw). | 1.00 |
| **Smoothing** | Low-pass filter on the input to kill jitter. Higher = smoother but laggier. | 0.00 |
| **Full press at** | Input level above which the key is held continuously (no pulsing). | 0.85 |
| **Curve** | Stick → tap-rate shape: `twozone` (PolyTrack-tuned), `linear`, `power`, `expo`, `scurve`. | twozone |
| **Sensitivity** | Overall output gain. >1 = stronger everywhere, <1 = gentler. | 1.00 |
| **Gamma** | Final response curve on the output. <1 = stronger, >1 = gentler. | 1.00 |
| **Min strength** | Anti-deadzone: minimum tap-rate the instant the action engages. | 0.00 |
| **Max strength** | Ceiling on tap-rate — caps how hard the action can ever push. | 1.00 |
| **Boost above** | Input % above which a boost kicks in (1.0 = off). | 1.00 |
| **Boost ×** | *"From X% it's this much stronger"* — multiplier applied above **Boost above**. | 1.00 |
| **L/R balance** | *(steer)* Strength bias between left and right. | 0.00 |
| **Mid point** | *(twozone)* Input where the "fine zone" ends and the "power zone" begins. | 0.50 |
| **Mid duty** | *(twozone)* Tap rate reached exactly at the mid point. | 0.45 |
| **Fine zone** | *(twozone)* Curve shape *below* the mid point. Lower = gentler at small inputs. | 0.70 |
| **Power zone** | *(twozone)* Curve shape *above* the mid point. Lower = snappier. | 0.70 |
| **Expo** | *(power / expo / scurve)* Steepness of the curve. | 0.60 |
| **Tap time (ms)** | How long each key press lasts. 16 ms = one browser frame at 60 fps. | 16 |
| **Min gap (ms)** | Floor on the pause between taps → caps *maximum* tap frequency. 0 = off. | 0 |
| **Max gap (ms)** | Ceiling on the pause between taps → forces a *minimum* tap rate. 0 = off. | 0 |
| **Turbo (Hz)** | When held, rapid-fire at this rate instead of a continuous press. 0 = off. | 0 |
| **Engage delay (ms)** | Input must persist this long before the key fires (debounce). | 0 |
| **Release delay (ms)** | Keeps the key driven this long after input drops (sticky / linger). | 0 |

#### Output keys

Each action has editable **key** fields — type any letter, or a name like `space`, `enter`, `shift`, `up`, `left`. Steer has separate **Left key** / **Right key**, and every action has an optional **Key 2 / combo** that fires alongside the main key (e.g. `shift` for a boost combo). This is how you adapt polycontroller to any WASD or arrow-key browser game.

#### App options

| Setting | What it does | Default |
|---|---|---|
| **Poll rate (Hz)** | How often the controller is read and keys updated. Higher = crisper, more CPU. | 200 |
| **Always on top** | Pins the window above the browser. | off |
| **Autosave** | Writes `config.json` automatically on every change. | off |
| **Autostart** | Begins converting immediately on launch (if a controller is present). | off |

**Click on any value number** to type in an exact value instead of using the slider.

**Save** stores everything (all profiles) to `config.json`, loaded automatically next time.  
**↺** resets the *active profile* to defaults (other profiles are untouched).

> Old `config.json` files are upgraded automatically on first launch — your existing settings become the "Default" profile.

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
| **Python** | 3.10 oder neuer (3.13 empfohlen) — [python.org](https://www.python.org/downloads/) |
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

PolyTrack-Lenkung ist **binär** — eine Taste ist entweder voll eingeschlagen oder aus. Das analoge Gefühl entsteht allein durch *wie schnell du tippst*. polycontroller ist auf maximale Feinjustierung ausgelegt: **jeder Parameter existiert einmal als globaler Standard und nochmal, unabhängig, pro Aktion** (Lenken / Gas / Bremse / Neustart). Das sind **28 Regler pro Aktion × 5 Ebenen** plus App-weite Optionen — weit über hundert Einstellungen, in ausklappbaren Sektionen organisiert.

#### Aufbau

- **App** — Fenster-/Laufzeit-Optionen (siehe unten).
- **Globale Standards** — die Basiswerte, die jede Aktion erbt.
- **Pro Aktion** (Lenken, Gas, Bremse, Neustart) — jede mit eigenem ausklappbarem Panel. **Eigene Werte** anhaken, um der Aktion eigene Werte zu geben; sonst folgt sie den globalen.
- **Profile** — komplette Setups unter Namen speichern, blitzschnell wechseln und als `.json` **exportieren / importieren**. Ideal für verschiedene Autos, Strecken oder Controller.

#### Parameter pro Aktion

| Einstellung | Funktion | Standard |
|---|---|---|
| **Aktiv** | Schaltet die Aktion komplett an/aus. | an |
| **Invertieren** | Kehrt die Eingaberichtung um. | aus |
| **Modus** | `pulse` = PWM-Tippen, `hold` = digital an/aus, `toggle` = Druck schaltet um. | pulse |
| **Mitten-Trim** | Verschiebt den Nullpunkt — gegen einen driftenden Stick. | 0.00 |
| **Deadzone** | Kleine Stick-Bewegungen in der Mitte ignorieren. Erhöhen wenn das Auto driftet. | 0.10 |
| **Deadzone-Typ** | `scaled` skaliert nach der Deadzone weich; `hard` schneidet hart ab. | scaled |
| **Max. Eingabe ab** | Eingabe ab diesem Wert zählt als 100% (kürzerer, direkterer Stick-Weg). | 1.00 |
| **Glättung** | Tiefpass auf die Eingabe gegen Jitter. Höher = ruhiger, aber träger. | 0.00 |
| **Vollgas ab** | Ab welchem Eingabewert die Taste dauerhaft gehalten wird. | 0.85 |
| **Kurve** | Stick→Tipprate-Form: `twozone` (PolyTrack-getunt), `linear`, `power`, `expo`, `scurve`. | twozone |
| **Sensitivität** | Gesamt-Gain. >1 = überall stärker, <1 = sanfter. | 1.00 |
| **Gamma** | Finale Kennlinie auf die Ausgabe. <1 = stärker, >1 = sanfter. | 1.00 |
| **Min. Stärke** | Anti-Deadzone: minimale Tipprate, sobald die Aktion greift. | 0.00 |
| **Max. Stärke** | Deckel der Tipprate — begrenzt wie hart die Aktion je drückt. | 1.00 |
| **Boost ab** | Eingabe-% ab dem ein Boost greift (1.0 = aus). | 1.00 |
| **Boost ×** | *„Ab X% wirkt es so viel stärker"* — Multiplikator oberhalb von **Boost ab**. | 1.00 |
| **L/R-Balance** | *(Lenken)* Stärke-Verschiebung zwischen links und rechts. | 0.00 |
| **Mittelpunkt** | *(twozone)* Eingabe, an der die „Fein-Zone" endet und die „Power-Zone" beginnt. | 0.50 |
| **Mittel-Duty** | *(twozone)* Tipprate genau am Mittelpunkt. | 0.45 |
| **Fein-Zone** | *(twozone)* Kurvenform *unterhalb* des Mittelpunkts. Niedriger = sanfter. | 0.70 |
| **Power-Zone** | *(twozone)* Kurvenform *oberhalb* des Mittelpunkts. Niedriger = direkter. | 0.70 |
| **Expo** | *(power / expo / scurve)* Steilheit der Kurve. | 0.60 |
| **Tap-Dauer (ms)** | Wie lange jeder Tastendruck dauert. 16 ms = ein Browser-Frame bei 60 fps. | 16 |
| **Min. Pause (ms)** | Untergrenze der Pause zwischen Taps → begrenzt die *maximale* Tipprate. 0 = aus. | 0 |
| **Max. Pause (ms)** | Obergrenze der Pause zwischen Taps → erzwingt eine *minimale* Tipprate. 0 = aus. | 0 |
| **Turbo (Hz)** | Beim Halten Dauerfeuer mit dieser Rate statt Dauerdruck. 0 = aus. | 0 |
| **Aktiv-Verzög. (ms)** | Eingabe muss so lange anliegen, bevor die Taste auslöst (Entprellung). | 0 |
| **Loslass-Verzög. (ms)** | Hält die Taste so lange nach, nachdem die Eingabe wegfällt (klebrig). | 0 |

#### Ausgabe-Tasten

Jede Aktion hat editierbare **Tasten**-Felder — beliebiger Buchstabe oder ein Name wie `space`, `enter`, `shift`, `up`, `left`. Lenken hat getrennte **Taste links** / **Taste rechts**, und jede Aktion hat eine optionale **Taste 2 / Combo**, die zusammen mit der Haupttaste auslöst (z. B. `shift` für eine Boost-Combo). So passt du polycontroller an jedes WASD- oder Pfeiltasten-Spiel an.

#### App-Optionen

| Einstellung | Funktion | Standard |
|---|---|---|
| **Polling-Rate (Hz)** | Wie oft der Controller gelesen und Tasten aktualisiert werden. Höher = direkter, mehr CPU. | 200 |
| **Immer im Vordergrund** | Heftet das Fenster über den Browser. | aus |
| **Autospeichern** | Schreibt `config.json` automatisch bei jeder Änderung. | aus |
| **Autostart** | Startet die Umwandlung sofort beim Programmstart (wenn ein Controller da ist). | aus |

**Auf die Zahl klicken** um einen genauen Wert einzutippen statt den Slider zu nutzen.

**Speichern** schreibt alles (alle Profile) in `config.json`, wird beim nächsten Start automatisch geladen.  
**↺** setzt das *aktive Profil* auf Standard zurück (andere Profile bleiben unberührt).

> Alte `config.json`-Dateien werden beim ersten Start automatisch migriert — deine bisherigen Einstellungen werden zum „Default"-Profil.

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
