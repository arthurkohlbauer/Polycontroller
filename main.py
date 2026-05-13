"""
polycontroller — Gamepad → WASD Converter
Specialized for PolyTrack (polytrack.io)
"""

import tkinter as tk
import threading, json, os, copy, time
import pygame
from pynput.keyboard import Controller as KbController

# ─── Paths & Defaults ────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

DEFAULTS = {
    'bindings': {
        'steer':    {'type': 'axis',   'index': 0},
        'throttle': {'type': 'button', 'index': 7},
        'brake':    {'type': 'button', 'index': 6},
        'reset':    {'type': 'button', 'index': 3},
    },
    'deadzone':        0.10,
    'upper_threshold': 0.85,
    'tap_ms':          16,
    'curve_exponent':  0.70,
    'lang':            'en',
}

WASD = {'left': 'a', 'right': 'd', 'forward': 'w', 'back': 's', 'reset': 'r'}

# ─── Controller presets ───────────────────────────────────────────────────────
# Auto-applied on first launch based on detected controller name.
# Users can always override with the Assign buttons in the GUI.
# Trigger axes rest at -1.0 (not pressed) and reach +1.0 when fully pressed.
CONTROLLER_PRESETS = [
    # (name fragments to match — lowercase, bindings)
    (['xbox', 'xinput'], {
        'steer':    {'type': 'axis',     'index': 0},
        'throttle': {'type': 'axis_pos', 'index': 5, 'rest': -1.0},  # RT
        'brake':    {'type': 'axis_pos', 'index': 4, 'rest': -1.0},  # LT
        'reset':    {'type': 'button',   'index': 3},                 # Y
    }),
    (['dualshock', 'dualsense', 'wireless controller', 'ps4', 'ps5'], {
        'steer':    {'type': 'axis',     'index': 0},
        'throttle': {'type': 'axis_pos', 'index': 5, 'rest': -1.0},  # R2
        'brake':    {'type': 'axis_pos', 'index': 4, 'rest': -1.0},  # L2
        'reset':    {'type': 'button',   'index': 3},                 # Triangle
    }),
    (['pro controller', 'nintendo switch pro', 'switch pro'], {
        'steer':    {'type': 'axis',   'index': 0},
        'throttle': {'type': 'button', 'index': 7},  # ZR
        'brake':    {'type': 'button', 'index': 6},  # ZL
        'reset':    {'type': 'button', 'index': 3},  # X
    }),
    (['joy-con', 'joycon'], {
        'steer':    {'type': 'axis',   'index': 0},
        'throttle': {'type': 'button', 'index': 5},  # R / ZR
        'brake':    {'type': 'button', 'index': 4},  # L / ZL
        'reset':    {'type': 'button', 'index': 3},
    }),
]


def match_preset(controller_name: str) -> dict | None:
    """Return bindings for the first matching preset, or None for generic defaults."""
    name = controller_name.lower()
    for fragments, bindings in CONTROLLER_PRESETS:
        if any(frag in name for frag in fragments):
            return copy.deepcopy(bindings)
    return None


# ─── Translations ─────────────────────────────────────────────────────────────
STRINGS = {
    'en': {
        'section_bindings': 'BINDINGS',
        'section_settings': 'SETTINGS',
        'section_status':   'LIVE STATUS',
        'throttle':         'Throttle',
        'brake':            'Brake',
        'steer':            'Steer',
        'reset':            'Reset',
        'deadzone':         'Deadzone',
        'full_press':       'Full press at',
        'tap_ms':           'Tap time (ms)',
        'fine_zone':        'Fine zone',
        'bar_left':         'Left',
        'bar_right':        'Right',
        'bar_throttle':     'Throttle',
        'bar_brake':        'Brake',
        'assign':           'Assign',
        'press_input':      'Press button or axis...',
        'waiting':          'Wait...',
        'save':             'Save',
        'start':            '▶  Start',
        'stop':             '■  Stop',
        'searching':        'Searching for controller...',
        'no_controller':    'No controller found',
        'axis_steer':       'Axis {}  (± steer)',
        'axis_pos':         'Axis {}  (+)',
        'axis_neg':         'Axis {}  (−)',
        'button':           'Button {}',
        'lang_btn':         'DE',
    },
    'de': {
        'section_bindings': 'TASTENBELEGUNG',
        'section_settings': 'EINSTELLUNGEN',
        'section_status':   'LIVE STATUS',
        'throttle':         'Gas',
        'brake':            'Bremse',
        'steer':            'Lenken',
        'reset':            'Neustart',
        'deadzone':         'Deadzone',
        'full_press':       'Vollgas ab',
        'tap_ms':           'Tap-Dauer (ms)',
        'fine_zone':        'Fein-Zone',
        'bar_left':         'Links',
        'bar_right':        'Rechts',
        'bar_throttle':     'Gas',
        'bar_brake':        'Bremse',
        'assign':           'Belegen',
        'press_input':      'Taste oder Achse drücken...',
        'waiting':          'Warte...',
        'save':             'Speichern',
        'start':            '▶  Start',
        'stop':             '■  Stop',
        'searching':        'Suche Controller...',
        'no_controller':    'Kein Controller gefunden',
        'axis_steer':       'Achse {}  (± Lenken)',
        'axis_pos':         'Achse {}  (+)',
        'axis_neg':         'Achse {}  (−)',
        'button':           'Button {}',
        'lang_btn':         'EN',
    },
}

# ─── Colors ───────────────────────────────────────────────────────────────────
T = {
    'bg':      '#1e1e2e',
    'surface': '#2a2a3d',
    'overlay': '#36364e',
    'accent':  '#7b68ee',
    'green':   '#50fa7b',
    'red':     '#ff5555',
    'yellow':  '#f1fa8c',
    'text':    '#f8f8f2',
    'dim':     '#6272a4',
}

# ─── Input helpers ────────────────────────────────────────────────────────────
def read_binding(joy: pygame.joystick.Joystick, b: dict) -> float:
    t, idx = b['type'], b['index']
    if t == 'button':
        return float(joy.get_button(idx))
    raw = joy.get_axis(idx)
    if t == 'axis':
        return raw
    rest = b.get('rest', -1.0 if t == 'axis_pos' else 1.0)
    if t == 'axis_pos':
        span = 1.0 - rest
        return max(0.0, (raw - rest) / span) if span else 0.0
    span = rest + 1.0
    return max(0.0, (rest - raw) / span) if span else 0.0


def deadzone(v: float, dz: float) -> float:
    if abs(v) < dz:
        return 0.0
    s = 1.0 if v >= 0 else -1.0
    return s * (abs(v) - dz) / (1.0 - dz)


def duty_curve(v: float, fine_exp: float) -> float:
    """
    Two-zone curve optimized for PolyTrack (derived from world-record analysis).

    Zone 1 (0–50% stick): fine control — gentle ramp.
      fine_exp controls shape: 0.5 = very soft, 1.0 = linear.
    Zone 2 (50–85% stick): power zone — steep ramp toward full press.
      Fixed exponent 0.70 for consistent response.
    Above upper_threshold: key held continuously.

    MID_DUTY 0.45 → at 50% stick: ~45% duty → ~29 taps/s.
    """
    MIDPOINT = 0.50
    MID_DUTY = 0.45

    v = abs(v)
    if v <= MIDPOINT:
        t = v / MIDPOINT
        return MID_DUTY * (t ** fine_exp)
    else:
        t = (v - MIDPOINT) / (1.0 - MIDPOINT)
        return MID_DUTY + (1.0 - MID_DUTY) * (t ** 0.70)


def binding_label(b: dict, S: dict) -> str:
    t, i = b.get('type', '?'), b.get('index', '?')
    if t == 'button':   return S['button'].format(i)
    if t == 'axis':     return S['axis_steer'].format(i)
    if t == 'axis_pos': return S['axis_pos'].format(i)
    if t == 'axis_neg': return S['axis_neg'].format(i)
    return '—'


# ─── PulseKey ─────────────────────────────────────────────────────────────────
class PulseKey:
    """
    Fixed hold, variable release pulse model.
    hold  = constant tap duration (default 16 ms = 1 browser frame at 60 fps).
    release = hold × (1 − duty) / duty  →  low input = rare taps, high = rapid.

    Examples at hold=16 ms:
      duty 0.05 → release 304 ms  ( 3 Hz)
      duty 0.20 → release  64 ms  (12 Hz)
      duty 0.45 → release  20 ms  (28 Hz)
      duty 0.50 → release  16 ms  (31 Hz)  ← max frequency
      duty 1.00 → key held continuously
    """
    def __init__(self, kb: KbController, key: str):
        self._kb, self._key = kb, key
        self.pressed = False
        self._t, self._on = time.monotonic(), False

    def update(self, duty: float, now: float, hold: float):
        if duty == 0.0:
            self._emit(False); self._t = now; self._on = False; return
        if duty >= 1.0:
            self._emit(True);  self._t = now; self._on = True;  return
        release = max(0.001, hold * (1.0 - duty) / duty)
        elapsed = now - self._t
        if self._on:
            if elapsed >= hold:
                self._emit(False); self._t = now; self._on = False
        else:
            if elapsed >= release:
                self._emit(True);  self._t = now; self._on = True

    def _emit(self, press: bool):
        if press == self.pressed: return
        (self._kb.press if press else self._kb.release)(self._key)
        self.pressed = press

    def release(self):
        self._emit(False)


# ─── Worker thread ────────────────────────────────────────────────────────────
class Worker(threading.Thread):
    def __init__(self, joy, config: dict, out: dict, lock: threading.Lock):
        super().__init__(daemon=True)
        self._joy, self._cfg, self._out, self._lock = joy, config, out, lock
        self._stop = threading.Event()
        kb = KbController()
        self._keys = {n: PulseKey(kb, k) for n, k in WASD.items()}

    def stop(self):
        self._stop.set()
        for k in self._keys.values():
            k.release()

    def run(self):
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                pygame.event.pump()
                c     = self._cfg
                hold  = c['tap_ms'] / 1000.0
                dz    = c['deadzone']
                upper = c['upper_threshold']
                exp   = c['curve_exponent']
                b     = c['bindings']

                raw_st  = read_binding(self._joy, b['steer'])
                raw_thr = read_binding(self._joy, b['throttle'])
                raw_brk = read_binding(self._joy, b['brake'])
                raw_rst = read_binding(self._joy, b['reset'])

                st  = deadzone(raw_st,  dz)
                thr = deadzone(raw_thr, dz)
                brk = deadzone(raw_brk, dz)

                def dc(v, e=exp, u=upper):
                    return 1.0 if abs(v) >= u else duty_curve(v, e)

                dc_l   = dc(-st) if st < 0 else 0.0
                dc_r   = dc( st) if st > 0 else 0.0
                dc_w   = dc(thr)
                dc_s   = dc(brk)
                dc_rst = float(raw_rst >= upper)

                now = time.monotonic()
                self._keys['left'].update(dc_l,   now, hold)
                self._keys['right'].update(dc_r,   now, hold)
                self._keys['forward'].update(dc_w,   now, hold)
                self._keys['back'].update(dc_s,   now, hold)
                self._keys['reset'].update(dc_rst, now, hold)

                with self._lock:
                    self._out.update(
                        l=dc_l, r=dc_r, w=dc_w, s=dc_s,
                        ka=self._keys['left'].pressed,
                        kd=self._keys['right'].pressed,
                        kw=self._keys['forward'].pressed,
                        ks=self._keys['back'].pressed,
                        kr=self._keys['reset'].pressed,
                    )
            except Exception:
                pass
            rem = 0.005 - (time.monotonic() - t0)
            if rem > 0:
                time.sleep(rem)


# ─── GUI ──────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('polycontroller · PolyTrack')
        self.resizable(False, False)
        self.configure(bg=T['bg'])
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        pygame.init()
        pygame.joystick.init()

        self.joy     = None
        self.worker  = None
        self.running = False
        self.status  = {}
        self.s_lock  = threading.Lock()
        self.binding = None
        self.b_tick  = 0
        self.config  = self._load_cfg()
        self._lang   = self.config.get('lang', 'en')

        self._build_header()
        self._content = tk.Frame(self, bg=T['bg'])
        self._content.pack(fill='both', expand=True)
        self._build_content()
        self._refresh_ctrl()
        self.after(60, self._tick)

    @property
    def S(self) -> dict:
        return STRINGS[self._lang]

    # ── Config ────────────────────────────────────────────────────────────────
    def _load_cfg(self) -> dict:
        self._fresh_install = not os.path.exists(CONFIG_PATH)
        try:
            with open(CONFIG_PATH, encoding='utf-8') as f:
                d = json.load(f)
            for k, v in DEFAULTS.items():
                d.setdefault(k, v)
            for k, v in DEFAULTS['bindings'].items():
                d['bindings'].setdefault(k, v)
            if 'pulse_period_ms' in d and 'tap_ms' not in d:
                d['tap_ms'] = DEFAULTS['tap_ms']
            return d
        except Exception:
            return copy.deepcopy(DEFAULTS)

    def _save_cfg(self):
        self._sync_cfg()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)

    def _reset_cfg(self):
        lang = self._lang
        self.config = copy.deepcopy(DEFAULTS)
        self.config['lang'] = lang
        self._dz.set(self.config['deadzone'])
        self._ut.set(self.config['upper_threshold'])
        self._pp.set(self.config['tap_ms'])
        self._cv.set(self.config['curve_exponent'])
        for key in ('throttle', 'brake', 'steer', 'reset'):
            val, _ = self._bw[key]
            val.config(text=binding_label(self.config['bindings'][key], self.S))

    def _sync_cfg(self):
        self.config['deadzone']        = round(self._dz.get(), 3)
        self.config['upper_threshold'] = round(self._ut.get(), 3)
        self.config['tap_ms']          = int(self._pp.get())
        self.config['curve_exponent']  = round(self._cv.get(), 3)
        self.config['lang']            = self._lang

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=T['accent'])
        hdr.pack(fill='x')
        tk.Label(hdr, text='polycontroller  ·  PolyTrack',
                 font=('Segoe UI', 15, 'bold'),
                 bg=T['accent'], fg='white', pady=9).pack(side='left', expand=True)
        self._lang_btn = tk.Button(
            hdr, text=self.S['lang_btn'],
            font=('Segoe UI', 8, 'bold'),
            bg='#6a58d6', fg='white',
            activebackground=T['accent'], activeforeground='white',
            relief='flat', padx=8, pady=4,
            cursor='hand2', command=self._toggle_lang)
        self._lang_btn.pack(side='right', padx=8, pady=7)

    def _build_content(self):
        S = self.S
        p = self._content

        # Controller info
        ci = tk.Frame(p, bg=T['surface'], padx=14, pady=7)
        ci.pack(fill='x', padx=8, pady=(7, 0))
        self._dot = tk.Label(ci, text='●', fg=T['dim'], bg=T['surface'],
                             font=('Segoe UI', 11))
        self._dot.pack(side='left')
        self._ctrl_lbl = tk.Label(ci, text=S['searching'],
                                  bg=T['surface'], fg=T['text'],
                                  font=('Segoe UI', 9), padx=6)
        self._ctrl_lbl.pack(side='left')

        # Bindings
        self._bw = {}
        bf = self._section(p, S['section_bindings'])
        for key, lbl_key, hint in [
            ('throttle', 'throttle', 'W'),
            ('brake',    'brake',    'S'),
            ('steer',    'steer',    'A / D'),
            ('reset',    'reset',    'R'),
        ]:
            self._bind_row(bf, key, S[lbl_key], hint)

        # Settings
        sf = self._section(p, S['section_settings'])
        self._dz = tk.DoubleVar(value=self.config['deadzone'])
        self._ut = tk.DoubleVar(value=self.config['upper_threshold'])
        self._pp = tk.IntVar(value=self.config['tap_ms'])
        self._cv = tk.DoubleVar(value=self.config['curve_exponent'])
        self._slider(sf, S['deadzone'],   self._dz, 0.0, 0.4,  '{:.2f}')
        self._slider(sf, S['full_press'], self._ut, 0.5, 1.0,  '{:.2f}')
        self._slider(sf, S['tap_ms'],     self._pp,   1,  100, '{:.0f}')
        self._slider(sf, S['fine_zone'],  self._cv, 0.3, 1.5,  '{:.2f}')

        # Live status
        lf = self._section(p, S['section_status'])
        self._bars = {}
        for k, lk in [
            ('l', 'bar_left'), ('r', 'bar_right'),
            ('w', 'bar_throttle'), ('s', 'bar_brake'),
        ]:
            self._bars[k] = self._bar_row(lf, S[lk])

        led_row = tk.Frame(lf, bg=T['surface'])
        led_row.pack(pady=(7, 3))
        self._leds = {}
        for letter, w in (('A', 3), ('D', 3), ('W', 3), ('S', 3), ('R', 3)):
            lbl = tk.Label(led_row, text=letter, width=w,
                           font=('Segoe UI', 13, 'bold'),
                           bg=T['overlay'], fg=T['dim'],
                           padx=5, pady=3, relief='flat')
            lbl.pack(side='left', padx=4)
            self._leds[letter] = lbl

        # Bottom buttons
        bot = tk.Frame(p, bg=T['bg'], pady=9)
        bot.pack(fill='x', padx=8, pady=(6, 8))
        self._start_btn = tk.Button(
            bot, text=S['stop'] if self.running else S['start'],
            font=('Segoe UI', 11, 'bold'),
            bg=T['red'] if self.running else T['accent'], fg='white',
            activebackground='#6a58d6',
            relief='flat', padx=14, pady=7,
            cursor='hand2', command=self._toggle)
        self._start_btn.pack(side='left', expand=True, fill='x', padx=(0, 4))

        self._save_btn = tk.Button(
            bot, text=S['save'],
            font=('Segoe UI', 11),
            bg=T['overlay'], fg=T['text'],
            activebackground=T['dim'],
            relief='flat', padx=14, pady=7,
            cursor='hand2', command=self._save_cfg)
        self._save_btn.pack(side='left', expand=True, fill='x', padx=(4, 4))

        tk.Button(bot, text='↺',
                  font=('Segoe UI', 11, 'bold'),
                  bg=T['overlay'], fg=T['dim'],
                  activebackground=T['red'], activeforeground='white',
                  relief='flat', padx=10, pady=7,
                  cursor='hand2', command=self._reset_cfg
                  ).pack(side='left')

    # ── Widget helpers ────────────────────────────────────────────────────────
    def _section(self, parent: tk.Frame, title: str) -> tk.Frame:
        f = tk.Frame(parent, bg=T['surface'], padx=12, pady=9)
        f.pack(fill='x', padx=8, pady=(5, 0))
        tk.Label(f, text=title, font=('Segoe UI', 7, 'bold'),
                 bg=T['surface'], fg=T['dim']).pack(anchor='w')
        return f

    def _bind_row(self, parent: tk.Frame, key: str, label: str, hint: str):
        S = self.S
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=3)
        tk.Label(row, text=label, width=8, anchor='w',
                 bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 10)).pack(side='left')
        tk.Label(row, text=f'[{hint}]', width=6, anchor='w',
                 bg=T['surface'], fg=T['accent'],
                 font=('Segoe UI', 9, 'bold')).pack(side='left')
        val = tk.Label(row, text=binding_label(self.config['bindings'][key], S),
                       width=22, anchor='w',
                       bg=T['overlay'], fg=T['text'],
                       font=('Consolas', 8), padx=6)
        val.pack(side='left', padx=6)
        btn = tk.Button(row, text=S['assign'],
                        font=('Segoe UI', 9),
                        bg=T['overlay'], fg=T['text'],
                        activebackground=T['accent'],
                        relief='flat', padx=7, pady=1,
                        cursor='hand2',
                        command=lambda k=key: self._start_bind(k))
        btn.pack(side='left')
        self._bw[key] = (val, btn)

    def _slider(self, parent: tk.Frame, label: str, var, lo, hi, fmt: str):
        res = 1 if isinstance(var, tk.IntVar) else 0.01
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=2)
        tk.Label(row, text=label, width=14, anchor='w',
                 bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 10)).pack(side='left')

        val_box = tk.Frame(row, bg=T['surface'])
        val_box.pack(side='right')

        val_lbl = tk.Label(val_box, text=fmt.format(var.get()), width=7, anchor='e',
                           bg=T['surface'], fg=T['accent'],
                           font=('Consolas', 9), cursor='xterm')
        val_lbl.pack()

        val_entry = tk.Entry(val_box, width=7,
                             bg=T['overlay'], fg=T['text'],
                             insertbackground=T['text'],
                             font=('Consolas', 9), bd=0,
                             highlightthickness=1,
                             highlightcolor=T['accent'],
                             highlightbackground=T['dim'])

        def show_entry(_=None):
            val_lbl.pack_forget()
            val_entry.delete(0, 'end')
            val_entry.insert(0, fmt.format(var.get()).strip())
            val_entry.pack()
            val_entry.focus_set()
            val_entry.select_range(0, 'end')

        def commit(_=None):
            try:
                v = float(val_entry.get())
                v = max(lo, min(hi, v))
                var.set(v)
                val_lbl.config(text=fmt.format(v))
            except ValueError:
                pass
            val_entry.pack_forget()
            val_lbl.pack()
            self._sync_cfg()

        def cancel(_=None):
            val_entry.pack_forget()
            val_lbl.pack()

        val_lbl.bind('<Button-1>', show_entry)
        val_entry.bind('<Return>',   commit)
        val_entry.bind('<FocusOut>', commit)
        val_entry.bind('<Escape>',   cancel)

        def on_change(v, l=val_lbl, f=fmt):
            l.config(text=f.format(float(v)))
            self._sync_cfg()

        tk.Scale(row, from_=lo, to=hi, variable=var, orient='horizontal',
                 resolution=res,
                 bg=T['overlay'], fg=T['text'], troughcolor=T['surface'],
                 activebackground=T['accent'], highlightthickness=0,
                 bd=0, showvalue=False, command=on_change
                 ).pack(side='left', fill='x', expand=True, padx=6)

    def _bar_row(self, parent: tk.Frame, label: str) -> tuple:
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=2)
        tk.Label(row, text=label, width=7, anchor='w',
                 bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')
        c = tk.Canvas(row, height=12, bg=T['overlay'], highlightthickness=0)
        c.pack(side='left', fill='x', expand=True, padx=6)
        rect = c.create_rectangle(0, 0, 0, 12, fill=T['accent'], outline='')
        return (c, rect)

    # ── Language ──────────────────────────────────────────────────────────────
    def _toggle_lang(self):
        self._cancel_bind()
        self._lang = 'de' if self._lang == 'en' else 'en'
        self.config['lang'] = self._lang
        self._lang_btn.config(text=self.S['lang_btn'])
        self._content.destroy()
        self._content = tk.Frame(self, bg=T['bg'])
        self._content.pack(fill='both', expand=True)
        self._build_content()
        self._refresh_ctrl()

    # ── Controller ────────────────────────────────────────────────────────────
    def _refresh_ctrl(self):
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count():
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
            name = self.joy.get_name()
            self._ctrl_lbl.config(text=name)
            self._dot.config(fg=T['green'])
            # On first launch (no saved config), auto-apply matching preset
            if self._fresh_install:
                preset = match_preset(name)
                if preset:
                    self.config['bindings'] = preset
                    for key, (val, _) in self._bw.items():
                        val.config(text=binding_label(self.config['bindings'][key], self.S))
                self._fresh_install = False
        else:
            self.joy = None
            self._ctrl_lbl.config(text=self.S['no_controller'])
            self._dot.config(fg=T['red'])

    # ── Binding flow ──────────────────────────────────────────────────────────
    def _start_bind(self, key: str):
        if not self.joy or self.binding:
            return
        pygame.event.pump()
        self._base_axes = [self.joy.get_axis(i)   for i in range(self.joy.get_numaxes())]
        self._base_btns = [self.joy.get_button(i) for i in range(self.joy.get_numbuttons())]
        self.binding, self.b_tick = key, 0
        val, btn = self._bw[key]
        val.config(text=self.S['press_input'])
        btn.config(text=self.S['waiting'], bg=T['yellow'], fg=T['bg'])
        self.after(50, self._poll_bind)

    def _poll_bind(self):
        if not self.binding:
            return
        key = self.binding
        pygame.event.pump()

        for i in range(self.joy.get_numbuttons()):
            if self.joy.get_button(i) and not self._base_btns[i]:
                self._finish_bind(key, {'type': 'button', 'index': i})
                return

        for i in range(self.joy.get_numaxes()):
            curr  = self.joy.get_axis(i)
            base  = self._base_axes[i]
            delta = curr - base
            if abs(delta) > 0.5:
                if key == 'steer':
                    b = {'type': 'axis', 'index': i}
                else:
                    direction = 'axis_pos' if delta > 0 else 'axis_neg'
                    b = {'type': direction, 'index': i, 'rest': round(base, 3)}
                self._finish_bind(key, b)
                return

        self.b_tick += 1
        if self.b_tick >= 100:
            self._cancel_bind()
            return
        self.after(50, self._poll_bind)

    def _finish_bind(self, key: str, binding: dict):
        self.config['bindings'][key] = binding
        val, btn = self._bw[key]
        val.config(text=binding_label(binding, self.S))
        btn.config(text=self.S['assign'], bg=T['overlay'], fg=T['text'])
        self.binding = None

    def _cancel_bind(self):
        if self.binding:
            key = self.binding
            val, btn = self._bw[key]
            val.config(text=binding_label(self.config['bindings'][key], self.S))
            btn.config(text=self.S['assign'], bg=T['overlay'], fg=T['text'])
            self.binding = None

    # ── Start / Stop ──────────────────────────────────────────────────────────
    def _toggle(self):
        S = self.S
        if self.running:
            self.worker.stop()
            self.worker  = None
            self.running = False
            self._start_btn.config(text=S['start'], bg=T['accent'])
        else:
            if not self.joy:
                self._refresh_ctrl()
            if not self.joy:
                return
            self._sync_cfg()
            self.worker  = Worker(self.joy, self.config, self.status, self.s_lock)
            self.worker.start()
            self.running = True
            self._start_btn.config(text=S['stop'], bg=T['red'])

    # ── Tick (GUI update) ─────────────────────────────────────────────────────
    def _tick(self):
        if self.running:
            with self.s_lock:
                s = dict(self.status)
            if s:
                for k in ('l', 'r', 'w', 's'):
                    self._set_bar(k, s.get(k, 0))
                for letter, key in (('A','ka'), ('D','kd'), ('W','kw'), ('S','ks'), ('R','kr')):
                    on = s.get(key, False)
                    self._leds[letter].config(
                        bg=T['green'] if on else T['overlay'],
                        fg=T['bg']    if on else T['dim'],
                    )
        else:
            for k in ('l', 'r', 'w', 's'):
                self._set_bar(k, 0.0)
            for letter in ('A', 'D', 'W', 'S', 'R'):
                self._leds[letter].config(bg=T['overlay'], fg=T['dim'])
        self.after(60, self._tick)

    def _set_bar(self, key: str, value: float):
        c, rect = self._bars[key]
        c.update_idletasks()
        w = c.winfo_width()
        c.coords(rect, 0, 0, int(value * w), 12)
        c.itemconfig(rect, fill=T['yellow'] if value > 0.8 else T['accent'])

    def _on_close(self):
        if self.worker:
            self.worker.stop()
        pygame.quit()
        self.destroy()


if __name__ == '__main__':
    app = App()
    app.mainloop()
