"""
polycontroller — Gamepad → keyboard converter
Specialized for PolyTrack (polytrack.io), usable for any WASD browser game.

PolyTrack steering is binary: a key is either full-lock or off. The analog feel
comes purely from *how fast you tap*. polycontroller turns analog stick / trigger
input into rapid key pulses (PWM). Every timing, curve and key is user-tunable —
per action, with named profiles you can switch, export and import.
"""

import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import threading, json, os, copy, time, math
import pygame
from pynput.keyboard import Controller as KbController, Key

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

# ─── Actions & defaults ───────────────────────────────────────────────────────
# Logical actions. `steer` is bipolar (drives two keys); the rest are unipolar.
ACTIONS = ['steer', 'throttle', 'brake', 'reset']

# Default output keys per action. `steer` has neg/pos slots, others a single main.
# Every action also has an optional `second` key (a combo key pressed alongside).
DEFAULT_KEYS = {
    'steer':    {'neg': 'a', 'pos': 'd', 'second': ''},
    'throttle': {'main': 'w', 'second': ''},
    'brake':    {'main': 's', 'second': ''},
    'reset':    {'main': 'r', 'second': ''},
}

DEFAULT_BINDINGS = {
    'steer':    {'type': 'axis',   'index': 0},
    'throttle': {'type': 'button', 'index': 7},
    'brake':    {'type': 'button', 'index': 6},
    'reset':    {'type': 'button', 'index': 3},
}

CURVE_TYPES = ['twozone', 'linear', 'power', 'expo', 'scurve']
MODES       = ['pulse', 'hold', 'toggle']     # PWM tapping | digital hold | latch
DZMODES     = ['scaled', 'hard']              # rescale past deadzone | raw cut

# Per-action tunable parameters. Every action — and the global default block —
# carries the full set; an action only overrides global when its "override" flag
# is on. This is the heart of the customization: ~28 knobs × (1 global + 4 actions).
GLOBAL_DEFAULTS = {
    # ── on/off & direction ──
    'enabled':         True,       # action active at all
    'invert':          False,      # flip input sign
    'mode':            'pulse',    # pulse (PWM) | hold (digital) | toggle (latch)
    # ── input shaping ──
    'center_offset':   0.0,        # neutral trim for a drifting stick (−0.25..0.25)
    'deadzone':        0.10,       # ignore input below this magnitude
    'deadzone_mode':   'scaled',   # scaled = rescale past dz, hard = raw cut
    'saturation':      1.0,        # input reaching this counts as 100% (shorter throw)
    'smoothing':       0.0,        # low-pass on input to kill jitter (0..0.95)
    'upper_threshold': 0.85,       # at/above this → key held continuously
    # ── strength / curve ──
    'curve_type':      'twozone',  # twozone | linear | power | expo | scurve
    'sensitivity':     1.0,        # overall output gain
    'gamma':           1.0,        # final response gamma on duty (<1 stronger)
    'min_duty':        0.0,        # anti-deadzone: min tap-rate once engaged
    'max_duty':        1.0,        # ceiling on tap-rate (strength cap)
    'boost_point':     1.0,        # above this input % apply boost_gain (1.0 = off)
    'boost_gain':      1.0,        # "...this much stronger" multiplier above boost_point
    'balance':         0.0,        # steer L/R strength bias (−0.5..0.5)
    # ── twozone curve shape ──
    'mid_point':       0.50,       # twozone: where fine zone ends
    'mid_duty':        0.45,       # twozone: duty reached at mid_point
    'fine_exp':        0.70,       # twozone: shape below mid_point
    'power_exp':       0.70,       # twozone: shape above mid_point
    'expo':            0.60,       # power/expo curve steepness
    # ── timing ──
    'tap_ms':          16,         # hold time per tap (16 = 1 frame @60fps)
    'release_min_ms':  0,          # floor on gap between taps (0 = off) → freq cap
    'release_max_ms':  0,          # ceiling on gap between taps (0 = off)
    'turbo_hz':        0,          # >0: rapid-fire at this rate instead of continuous
    'hold_delay_ms':   0,          # input must persist this long before engaging
    'release_delay_ms': 0,         # keep driving this long after input drops (sticky)
}
PARAM_KEYS = list(GLOBAL_DEFAULTS.keys())
INT_KEYS  = {'tap_ms', 'release_min_ms', 'release_max_ms',
             'turbo_hz', 'hold_delay_ms', 'release_delay_ms'}
BOOL_KEYS = {'enabled', 'invert'}
STR_KEYS  = {'curve_type', 'mode', 'deadzone_mode'}
CHOICE_OPTIONS = {'curve_type': CURVE_TYPES, 'mode': MODES, 'deadzone_mode': DZMODES}

# App-wide (non per-action) settings.
APP_DEFAULTS = {
    'poll_hz':        200,    # controller polling / update rate
    'always_on_top':  False,  # pin window above the browser
    'autosave':       False,  # write config on every change
    'autostart':      False,  # begin converting immediately on launch
}

# UI spec: (key, label_key, kind, lo, hi, fmt). kind ∈ float|int|bool|choice.
PARAM_SPEC = [
    ('enabled',          'p_enabled',   'bool',   None, None, None),
    ('invert',           'p_invert',    'bool',   None, None, None),
    ('mode',             'p_mode',      'choice', None, None, None),
    ('center_offset',    'p_center',    'float',  -0.25, 0.25, '{:.2f}'),
    ('deadzone',         'deadzone',    'float',  0.0,  0.5,  '{:.2f}'),
    ('deadzone_mode',    'p_dzmode',    'choice', None, None, None),
    ('saturation',       'p_sat',       'float',  0.5,  1.0,  '{:.2f}'),
    ('smoothing',        'p_smooth',    'float',  0.0,  0.95, '{:.2f}'),
    ('upper_threshold',  'full_press',  'float',  0.5,  1.0,  '{:.2f}'),
    ('curve_type',       'p_curve',     'choice', None, None, None),
    ('sensitivity',      'p_sens',      'float',  0.1,  3.0,  '{:.2f}'),
    ('gamma',            'p_gamma',     'float',  0.2,  3.0,  '{:.2f}'),
    ('min_duty',         'p_minduty',   'float',  0.0,  0.5,  '{:.2f}'),
    ('max_duty',         'p_maxduty',   'float',  0.1,  1.0,  '{:.2f}'),
    ('boost_point',      'p_boostpt',   'float',  0.0,  1.0,  '{:.2f}'),
    ('boost_gain',       'p_boostgn',   'float',  1.0,  3.0,  '{:.2f}'),
    ('balance',          'p_balance',   'float',  -0.5, 0.5,  '{:.2f}'),
    ('mid_point',        'mid_point',   'float',  0.05, 0.95, '{:.2f}'),
    ('mid_duty',         'mid_duty',    'float',  0.05, 0.95, '{:.2f}'),
    ('fine_exp',         'fine_zone',   'float',  0.2,  2.0,  '{:.2f}'),
    ('power_exp',        'power_zone',  'float',  0.2,  2.0,  '{:.2f}'),
    ('expo',             'expo',        'float',  0.2,  3.0,  '{:.2f}'),
    ('tap_ms',           'tap_ms',      'int',    1,    200,  '{:.0f}'),
    ('release_min_ms',   'rel_min',     'int',    0,    500,  '{:.0f}'),
    ('release_max_ms',   'rel_max',     'int',    0,    2000, '{:.0f}'),
    ('turbo_hz',         'p_turbo',     'int',    0,    30,   '{:.0f}'),
    ('hold_delay_ms',    'p_holddelay', 'int',    0,    1000, '{:.0f}'),
    ('release_delay_ms', 'p_reldelay',  'int',    0,    1000, '{:.0f}'),
]

# ─── Controller presets ────────────────────────────────────────────────────────
CONTROLLER_PRESETS = [
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
        'throttle': {'type': 'button', 'index': 5},
        'brake':    {'type': 'button', 'index': 4},
        'reset':    {'type': 'button', 'index': 3},
    }),
]


def match_preset(controller_name: str) -> dict | None:
    name = controller_name.lower()
    for fragments, bindings in CONTROLLER_PRESETS:
        if any(frag in name for frag in fragments):
            return copy.deepcopy(bindings)
    return None


# ─── Output-key resolution ──────────────────────────────────────────────────────
KEYMAP = {
    'space': Key.space, 'enter': Key.enter, 'return': Key.enter, 'tab': Key.tab,
    'shift': Key.shift, 'ctrl': Key.ctrl, 'control': Key.ctrl, 'alt': Key.alt,
    'esc': Key.esc, 'escape': Key.esc, 'up': Key.up, 'down': Key.down,
    'left': Key.left, 'right': Key.right, 'backspace': Key.backspace,
    'delete': Key.delete, 'del': Key.delete,
}


def resolve_key(name: str):
    """Map a textual key name to something pynput can press, or None if blank."""
    if not name:
        return None
    low = name.strip().lower()
    if low in KEYMAP:
        return KEYMAP[low]
    return name.strip()[0]  # first character for plain keys


# ─── Translations ─────────────────────────────────────────────────────────────
STRINGS = {
    'en': {
        'section_global':   'GLOBAL DEFAULTS',
        'section_keys':      'OUTPUT KEYS',
        'section_status':    'LIVE STATUS',
        'section_profiles':  'PROFILE',
        'throttle': 'Throttle', 'brake': 'Brake', 'steer': 'Steer', 'reset': 'Reset',
        'binding':  'Input', 'output_key': 'Key', 'key_neg': 'Left key', 'key_pos': 'Right key',
        'deadzone': 'Deadzone', 'full_press': 'Full press at', 'tap_ms': 'Tap time (ms)',
        'rel_min': 'Min gap (ms)', 'rel_max': 'Max gap (ms)', 'fine_zone': 'Fine zone',
        'power_zone': 'Power zone', 'mid_point': 'Mid point', 'mid_duty': 'Mid duty',
        'expo': 'Expo', 'p_enabled': 'Enabled', 'p_invert': 'Invert', 'p_curve': 'Curve',
        'p_override': 'Override defaults', 'key_second': 'Key 2 / combo',
        'p_mode': 'Mode', 'p_dzmode': 'Deadzone type', 'p_center': 'Center trim',
        'p_sat': 'Max input at', 'p_smooth': 'Smoothing', 'p_sens': 'Sensitivity',
        'p_gamma': 'Gamma', 'p_minduty': 'Min strength', 'p_maxduty': 'Max strength',
        'p_boostpt': 'Boost above', 'p_boostgn': 'Boost ×', 'p_balance': 'L/R balance',
        'p_turbo': 'Turbo (Hz)', 'p_holddelay': 'Engage delay (ms)', 'p_reldelay': 'Release delay (ms)',
        'section_app': 'APP', 'app_poll': 'Poll rate (Hz)', 'app_topmost': 'Always on top',
        'app_autosave': 'Autosave', 'app_autostart': 'Autostart',
        'bar_left': 'Left', 'bar_right': 'Right', 'bar_throttle': 'Throttle', 'bar_brake': 'Brake',
        'assign': 'Assign', 'press_input': 'Press button or axis...', 'waiting': 'Wait...',
        'save': 'Save', 'reset_btn': 'Reset', 'start': '▶  Start', 'stop': '■  Stop',
        'searching': 'Searching for controller...', 'no_controller': 'No controller found',
        'axis_steer': 'Axis {}  (± steer)', 'axis_pos': 'Axis {}  (+)',
        'axis_neg': 'Axis {}  (−)', 'button': 'Button {}', 'lang_btn': 'DE',
        'prof_new': 'New', 'prof_dup': 'Copy', 'prof_ren': 'Rename', 'prof_del': 'Delete',
        'prof_exp': 'Export', 'prof_imp': 'Import',
        'ask_new': 'Name for the new profile:', 'ask_ren': 'New profile name:',
        'del_confirm': 'Delete profile "{}"?', 'del_last': 'Cannot delete the last profile.',
        'imp_ok': 'Imported profile "{}".', 'imp_err': 'Could not import this file.',
    },
    'de': {
        'section_global':   'GLOBALE STANDARDS',
        'section_keys':      'AUSGABE-TASTEN',
        'section_status':    'LIVE STATUS',
        'section_profiles':  'PROFIL',
        'throttle': 'Gas', 'brake': 'Bremse', 'steer': 'Lenken', 'reset': 'Neustart',
        'binding':  'Eingabe', 'output_key': 'Taste', 'key_neg': 'Taste links', 'key_pos': 'Taste rechts',
        'deadzone': 'Deadzone', 'full_press': 'Vollgas ab', 'tap_ms': 'Tap-Dauer (ms)',
        'rel_min': 'Min. Pause (ms)', 'rel_max': 'Max. Pause (ms)', 'fine_zone': 'Fein-Zone',
        'power_zone': 'Power-Zone', 'mid_point': 'Mittelpunkt', 'mid_duty': 'Mittel-Duty',
        'expo': 'Expo', 'p_enabled': 'Aktiv', 'p_invert': 'Invertieren', 'p_curve': 'Kurve',
        'p_override': 'Eigene Werte', 'key_second': 'Taste 2 / Combo',
        'p_mode': 'Modus', 'p_dzmode': 'Deadzone-Typ', 'p_center': 'Mitten-Trim',
        'p_sat': 'Max. Eingabe ab', 'p_smooth': 'Glättung', 'p_sens': 'Sensitivität',
        'p_gamma': 'Gamma', 'p_minduty': 'Min. Stärke', 'p_maxduty': 'Max. Stärke',
        'p_boostpt': 'Boost ab', 'p_boostgn': 'Boost ×', 'p_balance': 'L/R-Balance',
        'p_turbo': 'Turbo (Hz)', 'p_holddelay': 'Aktiv-Verzög. (ms)', 'p_reldelay': 'Loslass-Verzög. (ms)',
        'section_app': 'APP', 'app_poll': 'Polling-Rate (Hz)', 'app_topmost': 'Immer im Vordergrund',
        'app_autosave': 'Autospeichern', 'app_autostart': 'Autostart',
        'bar_left': 'Links', 'bar_right': 'Rechts', 'bar_throttle': 'Gas', 'bar_brake': 'Bremse',
        'assign': 'Belegen', 'press_input': 'Taste oder Achse drücken...', 'waiting': 'Warte...',
        'save': 'Speichern', 'reset_btn': 'Zurücksetzen', 'start': '▶  Start', 'stop': '■  Stop',
        'searching': 'Suche Controller...', 'no_controller': 'Kein Controller gefunden',
        'axis_steer': 'Achse {}  (± Lenken)', 'axis_pos': 'Achse {}  (+)',
        'axis_neg': 'Achse {}  (−)', 'button': 'Button {}', 'lang_btn': 'EN',
        'prof_new': 'Neu', 'prof_dup': 'Kopie', 'prof_ren': 'Umbenennen', 'prof_del': 'Löschen',
        'prof_exp': 'Export', 'prof_imp': 'Import',
        'ask_new': 'Name für das neue Profil:', 'ask_ren': 'Neuer Profilname:',
        'del_confirm': 'Profil „{}" löschen?', 'del_last': 'Das letzte Profil kann nicht gelöscht werden.',
        'imp_ok': 'Profil „{}" importiert.', 'imp_err': 'Datei konnte nicht importiert werden.',
    },
}

# ─── Colors ───────────────────────────────────────────────────────────────────
T = {
    'bg': '#1e1e2e', 'surface': '#2a2a3d', 'overlay': '#36364e', 'accent': '#7b68ee',
    'green': '#50fa7b', 'red': '#ff5555', 'yellow': '#f1fa8c', 'text': '#f8f8f2', 'dim': '#6272a4',
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


def duty_for(v: float, p: dict) -> float:
    """
    Map stick deflection |v| (0..1) → tap duty cycle (0..1), per the action's
    selected curve type. Duty 0 = no taps, 1 = key held continuously.

    twozone : PolyTrack-tuned two-segment curve (fine zone + power zone).
    linear  : duty = v.
    power   : duty = v ** expo   (expo<1 aggressive, >1 gentle).
    expo    : exponential ramp, steepness from `expo`.
    """
    v = min(1.0, abs(v))
    ct = p.get('curve_type', 'twozone')

    if ct == 'linear':
        return v
    if ct == 'power':
        return v ** p['expo']
    if ct == 'expo':
        k = p['expo'] * 4.0
        if abs(k) < 1e-6:
            return v
        return (math.exp(k * v) - 1.0) / (math.exp(k) - 1.0)
    if ct == 'scurve':
        # smoothstep raised to expo for adjustable steepness
        s = v * v * (3.0 - 2.0 * v)
        return s ** p['expo'] if p['expo'] != 1.0 else s

    # twozone (default)
    mp, md = p['mid_point'], p['mid_duty']
    if v <= mp:
        t = v / mp if mp > 0 else 1.0
        return md * (t ** p['fine_exp'])
    span = 1.0 - mp
    t = (v - mp) / span if span > 0 else 1.0
    return md + (1.0 - md) * (t ** p['power_exp'])


def shape_input(raw: float, p: dict) -> float:
    """
    Turn the raw axis/button reading into a signed effective input in [-1, 1],
    applying (in order): invert → center trim → deadzone → saturation.
    """
    if p.get('invert'):
        raw = -raw
    raw = max(-1.0, min(1.0, raw + p.get('center_offset', 0.0)))
    dz = p.get('deadzone', 0.0)
    if p.get('deadzone_mode', 'scaled') == 'hard':
        v = 0.0 if abs(raw) < dz else raw
    else:
        v = deadzone(raw, dz)
    sat = p.get('saturation', 1.0)
    if 0.0 < sat < 1.0:
        v = max(-1.0, min(1.0, v / sat))
    return v


def map_duty(m: float, p: dict) -> float:
    """
    Map an engaged input magnitude m (0..1) → tap duty cycle (0..1), applying the
    curve, then boost zone, gamma, sensitivity, and the min/max-duty clamps.
    """
    if m <= 0.0:
        return 0.0
    duty = 1.0 if m >= p['upper_threshold'] else duty_for(m, p)
    if m > p.get('boost_point', 1.0):
        duty *= p.get('boost_gain', 1.0)
    g = p.get('gamma', 1.0)
    if g != 1.0:
        duty = max(0.0, duty) ** g
    duty *= p.get('sensitivity', 1.0)
    md = p.get('min_duty', 0.0)
    if duty < md:
        duty = md
    duty = min(duty, p.get('max_duty', 1.0))
    return max(0.0, min(1.0, duty))


def binding_label(b: dict, S: dict) -> str:
    t, i = b.get('type', '?'), b.get('index', '?')
    if t == 'button':   return S['button'].format(i)
    if t == 'axis':     return S['axis_steer'].format(i)
    if t == 'axis_pos': return S['axis_pos'].format(i)
    if t == 'axis_neg': return S['axis_neg'].format(i)
    return '—'


# ─── Config model (profiles) ────────────────────────────────────────────────────
def default_profile() -> dict:
    return {
        'global': copy.deepcopy(GLOBAL_DEFAULTS),
        'actions': {
            a: {
                '_override': False,
                'params': copy.deepcopy(GLOBAL_DEFAULTS),
                'keys': copy.deepcopy(DEFAULT_KEYS[a]),
            } for a in ACTIONS
        },
        'bindings': copy.deepcopy(DEFAULT_BINDINGS),
    }


def _fill_profile(prof: dict) -> dict:
    """Backfill any missing keys so a profile is always complete."""
    prof.setdefault('global', {})
    for k, v in GLOBAL_DEFAULTS.items():
        prof['global'].setdefault(k, v)
    prof.setdefault('actions', {})
    for a in ACTIONS:
        ad = prof['actions'].setdefault(a, {})
        ad.setdefault('_override', False)
        ad.setdefault('params', {})
        for k, v in GLOBAL_DEFAULTS.items():
            ad['params'].setdefault(k, prof['global'][k])
        ad.setdefault('keys', copy.deepcopy(DEFAULT_KEYS[a]))
        for slot, kv in DEFAULT_KEYS[a].items():
            ad['keys'].setdefault(slot, kv)
    prof.setdefault('bindings', {})
    for k, v in DEFAULT_BINDINGS.items():
        prof['bindings'].setdefault(k, copy.deepcopy(v))
    return prof


def default_config() -> dict:
    return {'lang': 'en', 'active': 'Default', 'app': copy.deepcopy(APP_DEFAULTS),
            'profiles': {'Default': default_profile()}}


def migrate_config(raw: dict) -> dict:
    """Accept any historical config shape and return a complete v2 config."""
    if not isinstance(raw, dict):
        return default_config()

    # Already v2
    if 'profiles' in raw and isinstance(raw['profiles'], dict) and raw['profiles']:
        for name, prof in raw['profiles'].items():
            _fill_profile(prof)
        raw.setdefault('lang', 'en')
        raw.setdefault('app', {})
        for k, v in APP_DEFAULTS.items():
            raw['app'].setdefault(k, v)
        if raw.get('active') not in raw['profiles']:
            raw['active'] = next(iter(raw['profiles']))
        return raw

    # Legacy flat config (v1 / v1.5) → single "Default" profile
    prof = default_profile()
    g = prof['global']
    for k in GLOBAL_DEFAULTS:
        if k in raw:
            g[k] = raw[k]
    if 'curve_exponent' in raw:
        g['fine_exp'] = raw['curve_exponent']
    if 'power_exponent' in raw:
        g['power_exp'] = raw['power_exponent']
    if 'bindings' in raw and isinstance(raw['bindings'], dict):
        for k, v in raw['bindings'].items():
            prof['bindings'][k] = v
    # Re-baseline action params on migrated global
    for a in ACTIONS:
        prof['actions'][a]['params'] = copy.deepcopy(g)
    # Old separate drive-tap → override on throttle/brake/reset
    drive = raw.get('tap_drive_ms')
    if drive is not None and drive != g['tap_ms']:
        for a in ('throttle', 'brake', 'reset'):
            prof['actions'][a]['_override'] = True
            prof['actions'][a]['params']['tap_ms'] = drive
    return {'lang': raw.get('lang', 'en'), 'active': 'Default',
            'app': copy.deepcopy(APP_DEFAULTS), 'profiles': {'Default': prof}}


def resolve_runtime(profile: dict) -> dict:
    """Flatten a profile into the per-action effective parameters the Worker uses."""
    g = profile['global']
    acts = {}
    for a, info in profile['actions'].items():
        p = dict(g)
        if info.get('_override'):
            p.update(info.get('params', {}))
        acts[a] = {'params': p, 'keys': info.get('keys', {})}
    return {'actions': acts, 'bindings': profile['bindings']}


# ─── PulseKey ─────────────────────────────────────────────────────────────────
class PulseKey:
    """
    Fixed-hold, variable-release pulse model.
      hold    = constant tap duration.
      release = hold × (1 − duty) / duty, clamped to [rel_min, rel_max].
    Low duty → rare taps, high duty → rapid taps, duty ≥ 1 → held continuously.
    rel_min caps the max tap frequency; rel_max forces a minimum tap rate.
    """
    def __init__(self, kb: KbController, key_name: str):
        self._kb = kb
        self._key = resolve_key(key_name)
        self.pressed = False
        self._t, self._on = time.monotonic(), False

    def update(self, duty: float, now: float, hold: float,
               rel_min: float = 0.0, rel_max: float = 0.0):
        if self._key is None or duty <= 0.0:
            self._emit(False); self._t = now; self._on = False; return
        if duty >= 1.0:
            self._emit(True); self._t = now; self._on = True; return
        release = hold * (1.0 - duty) / duty
        if rel_max > 0:
            release = min(release, rel_max)
        release = max(release, rel_min, 0.001)
        elapsed = now - self._t
        if self._on:
            if elapsed >= hold:
                self._emit(False); self._t = now; self._on = False
        else:
            if elapsed >= release:
                self._emit(True); self._t = now; self._on = True

    def _emit(self, press: bool):
        if self._key is None or press == self.pressed:
            return
        (self._kb.press if press else self._kb.release)(self._key)
        self.pressed = press

    def release(self):
        self._emit(False)


# ─── Worker thread ────────────────────────────────────────────────────────────
class Worker(threading.Thread):
    def __init__(self, joy, get_runtime, out: dict, lock: threading.Lock):
        super().__init__(daemon=True)
        self._joy, self._rt, self._out, self._lock = joy, get_runtime, out, lock
        self._stop = threading.Event()
        self._kb = KbController()
        self._keys: dict[str, PulseKey] = {}
        self._state: dict[str, dict] = {}   # per-channel timing/smoothing memory

    def stop(self):
        self._stop.set()
        for k in self._keys.values():
            k.release()

    def _pk(self, name: str) -> PulseKey:
        pk = self._keys.get(name)
        if pk is None:
            pk = self._keys[name] = PulseKey(self._kb, name)
        return pk

    def _drive(self, name, duty, p, now, seen):
        if not name:
            return
        seen.add(name)
        self._pk(name).update(
            duty, now,
            p['tap_ms'] / 1000.0,
            p['release_min_ms'] / 1000.0,
            p['release_max_ms'] / 1000.0,
        )

    def _proc(self, ch, raw, p, now):
        """
        Full per-channel input→duty pipeline with state: shaping, smoothing,
        hold/release delays, mode (pulse/hold/toggle), turbo. Returns (duty, sign).
        """
        s = self._state.get(ch)
        if s is None:
            s = self._state[ch] = {'sm': 0.0, 'eng': False, 'te': 0.0, 'tr': 0.0, 'tog': False}

        v = shape_input(raw, p)
        m = abs(v)
        sm = p.get('smoothing', 0.0)
        if sm > 0:
            s['sm'] += (m - s['sm']) * (1.0 - sm)
            m = s['sm']
        else:
            s['sm'] = m
        sign = -1.0 if v < 0 else 1.0

        active = m > 1e-4
        hd = p.get('hold_delay_ms', 0) / 1000.0
        rd = p.get('release_delay_ms', 0) / 1000.0
        if active:
            s['tr'] = 0.0
            if not s['eng']:
                if s['te'] == 0.0:
                    s['te'] = now
                if now - s['te'] >= hd:
                    s['eng'] = True
                    if p.get('mode') == 'toggle':
                        s['tog'] = not s['tog']
        else:
            s['te'] = 0.0
            if s['eng']:
                if s['tr'] == 0.0:
                    s['tr'] = now
                if now - s['tr'] >= rd:
                    s['eng'] = False

        if not s['eng']:
            return 0.0, sign

        mode = p.get('mode', 'pulse')
        if mode == 'hold':
            duty = 1.0
        elif mode == 'toggle':
            duty = 1.0 if s['tog'] else 0.0
        else:
            duty = map_duty(m, p)

        th = p.get('turbo_hz', 0)
        if th > 0 and duty > 0:
            duty = max(0.0, min(1.0, (p['tap_ms'] / 1000.0) * th))
        return duty, sign

    def run(self):
        poll = 200
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                pygame.event.pump()
                rt = self._rt()
                acts, b = rt['actions'], rt['bindings']
                poll = rt.get('poll_hz', 200)
                now = time.monotonic()
                seen: set[str] = set()
                out = {'l': 0.0, 'r': 0.0, 'w': 0.0, 's': 0.0}

                # Steer (bipolar → two keys, with L/R balance)
                sp = acts['steer']['params']
                sk = acts['steer']['keys']
                dl = dr = 0.0
                if sp['enabled']:
                    duty, sign = self._proc('steer', read_binding(self._joy, b['steer']), sp, now)
                    bal = sp.get('balance', 0.0)
                    if sign < 0:
                        dl = max(0.0, min(1.0, duty * (1.0 - bal)))
                    else:
                        dr = max(0.0, min(1.0, duty * (1.0 + bal)))
                self._drive(sk.get('neg'), dl, sp, now, seen)
                self._drive(sk.get('pos'), dr, sp, now, seen)
                self._drive(sk.get('second'), max(dl, dr), sp, now, seen)
                out['l'], out['r'] = dl, dr

                # Throttle / Brake / Reset (unipolar magnitude)
                for role, ch in (('throttle', 'w'), ('brake', 's'), ('reset', None)):
                    ap = acts[role]
                    p = ap['params']
                    duty = 0.0
                    if p['enabled']:
                        duty, _ = self._proc(role, read_binding(self._joy, b[role]), p, now)
                    self._drive(ap['keys'].get('main'), duty, p, now, seen)
                    self._drive(ap['keys'].get('second'), duty, p, now, seen)
                    if ch:
                        out[ch] = duty

                # Release any key no longer driven (e.g. remapped / disabled)
                for name, pk in self._keys.items():
                    if name not in seen and pk.pressed:
                        pk.update(0.0, now, 0.016)

                with self._lock:
                    self._out.clear()
                    self._out.update(out)
                    self._out['keys'] = {n: pk.pressed for n, pk in self._keys.items()}
            except Exception:
                pass
            rem = (1.0 / max(1, poll)) - (time.monotonic() - t0)
            if rem > 0:
                time.sleep(rem)


# ─── GUI ──────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('polycontroller · PolyTrack')
        self.geometry('410x760')
        self.minsize(410, 480)
        self.configure(bg=T['bg'])
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        pygame.init()
        pygame.joystick.init()

        self.joy = None
        self.worker = None
        self.running = False
        self.status = {}
        self.s_lock = threading.Lock()
        self.binding = None
        self.b_tick = 0
        self._building = False
        self._autosave_job = None

        self.config_data = self._load_cfg()
        self._lang = self.config_data.get('lang', 'en')

        # widget registries (rebuilt with content)
        self._vars = {}      # scope -> {param_key: tk.Var}
        self._ovr = {}       # action -> BooleanVar
        self._kv = {}        # action -> {slot: StringVar}
        self._appvars = {}   # app-level setting vars
        self._bw = {}        # action -> (value_label, assign_btn)
        self._bars = {}
        self._leds = {}      # slot -> label

        self._rebuild_runtime()

        self._build_header()
        self._build_profilebar()
        self._build_scroll()
        self._build_bottom()
        self._build_content()
        self._refresh_ctrl()
        self._apply_app()
        if self.config_data.get('app', {}).get('autostart') and self.joy:
            self._toggle()
        self.after(60, self._tick)

    # ── Convenience ────────────────────────────────────────────────────────────
    @property
    def S(self) -> dict:
        return STRINGS[self._lang]

    def _prof(self) -> dict:
        return self.config_data['profiles'][self.config_data['active']]

    # ── Config load / save ───────────────────────────────────────────────────────
    def _load_cfg(self) -> dict:
        self._fresh_install = not os.path.exists(CONFIG_PATH)
        try:
            with open(CONFIG_PATH, encoding='utf-8') as f:
                return migrate_config(json.load(f))
        except Exception:
            return default_config()

    def _save_cfg(self):
        self._collect()
        self._write_cfg()

    def _write_cfg(self):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception:
            pass

    def _rebuild_runtime(self):
        rt = resolve_runtime(self._prof())
        rt['poll_hz'] = self.config_data.get('app', {}).get('poll_hz', 200)
        self._runtime = rt

    def _reset_cfg(self):
        """Reset the active profile to defaults (keeps other profiles & language)."""
        self.config_data['profiles'][self.config_data['active']] = default_profile()
        self._rebuild_runtime()
        self._build_content()

    # ── Collect widgets → config, then rebuild runtime ───────────────────────────
    def _collect(self):
        if self._building:
            return
        prof = self._prof()
        # Global defaults
        for k in PARAM_KEYS:
            prof['global'][k] = self._read_var('global', k)
        # Per-action params + override + keys
        for a in ACTIONS:
            ad = prof['actions'][a]
            ad['_override'] = bool(self._ovr[a].get())
            for k in PARAM_KEYS:
                ad['params'][k] = self._read_var(a, k)
            for slot, var in self._kv[a].items():
                ad['keys'][slot] = var.get().strip()
        # App-level settings
        app = self.config_data.setdefault('app', copy.deepcopy(APP_DEFAULTS))
        if self._appvars:
            app['poll_hz'] = int(self._appvars['poll_hz'].get())
            app['always_on_top'] = bool(self._appvars['always_on_top'].get())
            app['autosave'] = bool(self._appvars['autosave'].get())
            app['autostart'] = bool(self._appvars['autostart'].get())
        self.config_data['lang'] = self._lang
        rt = resolve_runtime(prof)
        rt['poll_hz'] = app['poll_hz']
        self._runtime = rt
        self._refresh_leds()
        self._apply_app()
        if app['autosave']:
            self._schedule_autosave()

    def _read_var(self, scope: str, key: str):
        val = self._vars[scope][key].get()
        if key in INT_KEYS:
            return int(val)
        if key in BOOL_KEYS:
            return bool(val)
        if key in STR_KEYS:
            return str(val)
        return round(float(val), 3)

    def _apply_app(self):
        try:
            self.attributes('-topmost', bool(self.config_data.get('app', {}).get('always_on_top')))
        except Exception:
            pass

    def _schedule_autosave(self):
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(600, self._do_autosave)

    def _do_autosave(self):
        self._autosave_job = None
        self._write_cfg()

    def _sync_cfg(self, *_):
        self._collect()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=T['accent'])
        hdr.pack(fill='x')
        tk.Label(hdr, text='polycontroller  ·  PolyTrack', font=('Segoe UI', 14, 'bold'),
                 bg=T['accent'], fg='white', pady=8).pack(side='left', expand=True)
        self._lang_btn = tk.Button(hdr, text=self.S['lang_btn'], font=('Segoe UI', 8, 'bold'),
                                   bg='#6a58d6', fg='white', activebackground=T['accent'],
                                   activeforeground='white', relief='flat', padx=8, pady=4,
                                   cursor='hand2', command=self._toggle_lang)
        self._lang_btn.pack(side='right', padx=8, pady=6)

    # ── Profile bar ──────────────────────────────────────────────────────────────
    def _build_profilebar(self):
        S = self.S
        bar = tk.Frame(self, bg=T['surface'], padx=8, pady=6)
        bar.pack(fill='x')
        tk.Label(bar, text=S['section_profiles'], font=('Segoe UI', 7, 'bold'),
                 bg=T['surface'], fg=T['dim']).pack(anchor='w')
        row = tk.Frame(bar, bg=T['surface'])
        row.pack(fill='x', pady=(3, 0))

        self._prof_var = tk.StringVar(value=self.config_data['active'])
        names = list(self.config_data['profiles'].keys())
        self._prof_menu = tk.OptionMenu(row, self._prof_var, *names, command=self._switch_profile)
        self._prof_menu.config(bg=T['overlay'], fg=T['text'], activebackground=T['accent'],
                               relief='flat', highlightthickness=0, font=('Segoe UI', 9), width=12)
        self._prof_menu['menu'].config(bg=T['overlay'], fg=T['text'])
        self._prof_menu.pack(side='left')

        for key, cmd in (('prof_new', self._profile_new), ('prof_dup', self._profile_dup),
                         ('prof_ren', self._profile_rename), ('prof_del', self._profile_delete),
                         ('prof_exp', self._profile_export), ('prof_imp', self._profile_import)):
            tk.Button(row, text=S[key], font=('Segoe UI', 8), bg=T['overlay'], fg=T['text'],
                      activebackground=T['accent'], relief='flat', padx=5, pady=2,
                      cursor='hand2', command=cmd).pack(side='left', padx=2)

    def _rebuild_profile_menu(self):
        menu = self._prof_menu['menu']
        menu.delete(0, 'end')
        for name in self.config_data['profiles']:
            menu.add_command(label=name,
                             command=lambda n=name: (self._prof_var.set(n), self._switch_profile(n)))

    # ── Scroll skeleton ──────────────────────────────────────────────────────────
    def _build_scroll(self):
        outer = tk.Frame(self, bg=T['bg'])
        outer.pack(fill='both', expand=True)
        self._canvas = tk.Canvas(outer, bg=T['bg'], highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)
        self._content = tk.Frame(self._canvas, bg=T['bg'])
        self._win = self._canvas.create_window((0, 0), window=self._content, anchor='nw')
        self._content.bind('<Configure>',
                           lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>',
                          lambda e: self._canvas.itemconfig(self._win, width=e.width))
        self._canvas.bind_all('<MouseWheel>',
                              lambda e: self._canvas.yview_scroll(int(-e.delta / 120), 'units'))

    # ── Bottom bar ───────────────────────────────────────────────────────────────
    def _build_bottom(self):
        S = self.S
        bot = tk.Frame(self, bg=T['bg'], pady=8)
        bot.pack(fill='x', padx=8, pady=(4, 8))
        self._start_btn = tk.Button(bot, text=S['stop'] if self.running else S['start'],
                                    font=('Segoe UI', 11, 'bold'),
                                    bg=T['red'] if self.running else T['accent'], fg='white',
                                    activebackground='#6a58d6', relief='flat', padx=12, pady=7,
                                    cursor='hand2', command=self._toggle)
        self._start_btn.pack(side='left', expand=True, fill='x', padx=(0, 4))
        self._save_btn = tk.Button(bot, text=S['save'], font=('Segoe UI', 11),
                                   bg=T['overlay'], fg=T['text'], activebackground=T['dim'],
                                   relief='flat', padx=12, pady=7, cursor='hand2',
                                   command=self._save_cfg)
        self._save_btn.pack(side='left', expand=True, fill='x', padx=4)
        self._reset_btn = tk.Button(bot, text='↺', font=('Segoe UI', 11, 'bold'),
                                    bg=T['overlay'], fg=T['dim'], activebackground=T['red'],
                                    activeforeground='white', relief='flat', padx=10, pady=7,
                                    cursor='hand2', command=self._reset_cfg)
        self._reset_btn.pack(side='left')

    # ── Content (rebuilt on profile/lang change) ───────────────────────────────────
    def _build_content(self):
        self._building = True
        for w in self._content.winfo_children():
            w.destroy()
        self._vars, self._ovr, self._kv = {}, {}, {}
        self._appvars, self._bw, self._bars, self._leds = {}, {}, {}, {}
        S = self.S
        p = self._content

        # Controller info
        ci = tk.Frame(p, bg=T['surface'], padx=14, pady=6)
        ci.pack(fill='x', padx=8, pady=(7, 0))
        self._dot = tk.Label(ci, text='●', fg=T['dim'], bg=T['surface'], font=('Segoe UI', 11))
        self._dot.pack(side='left')
        self._ctrl_lbl = tk.Label(ci, text=S['searching'], bg=T['surface'], fg=T['text'],
                                  font=('Segoe UI', 9), padx=6)
        self._ctrl_lbl.pack(side='left')

        # App-level settings
        self._build_app_section(p)

        # Global defaults
        self._vars['global'] = {}
        gbody = self._collapsible(p, S['section_global'], opened=False)
        for spec in PARAM_SPEC:
            self._param_control(gbody, 'global', spec)

        # Per-action panels
        for a in ACTIONS:
            self._action_panel(p, a)

        # Live status
        lf = self._collapsible(p, S['section_status'], opened=True)
        self._bars = {}
        for k, lk in (('l', 'bar_left'), ('r', 'bar_right'),
                      ('w', 'bar_throttle'), ('s', 'bar_brake')):
            self._bars[k] = self._bar_row(lf, S[lk])
        led_row = tk.Frame(lf, bg=T['surface'])
        led_row.pack(pady=(7, 3))
        self._led_row = led_row
        self._refresh_leds()

        self._building = False
        self._collect()

    def _build_app_section(self, parent):
        S = self.S
        app = self.config_data.setdefault('app', copy.deepcopy(APP_DEFAULTS))
        body = self._collapsible(parent, S['section_app'], opened=False)

        poll = tk.IntVar(value=app.get('poll_hz', 200))
        self._appvars['poll_hz'] = poll
        row = tk.Frame(body, bg=T['surface'])
        row.pack(fill='x', pady=1)
        tk.Label(row, text=S['app_poll'], width=14, anchor='w', bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')
        val = tk.Label(row, text=str(poll.get()), width=6, anchor='e', bg=T['surface'],
                       fg=T['accent'], font=('Consolas', 9))
        val.pack(side='right')
        tk.Scale(row, from_=100, to=1000, variable=poll, orient='horizontal', resolution=10,
                 bg=T['overlay'], fg=T['text'], troughcolor=T['surface'], activebackground=T['accent'],
                 highlightthickness=0, bd=0, showvalue=False, length=120,
                 command=lambda v: (val.config(text=str(int(float(v)))), self._sync_cfg())
                 ).pack(side='left', fill='x', expand=True, padx=6)

        for key, lbl in (('always_on_top', 'app_topmost'), ('autosave', 'app_autosave'),
                         ('autostart', 'app_autostart')):
            var = tk.BooleanVar(value=bool(app.get(key, False)))
            self._appvars[key] = var
            tk.Checkbutton(body, text=S[lbl], variable=var, bg=T['surface'], fg=T['text'],
                           selectcolor=T['overlay'], activebackground=T['surface'],
                           activeforeground=T['text'], font=('Segoe UI', 9), anchor='w',
                           command=self._sync_cfg).pack(fill='x', pady=1)

    def _action_panel(self, parent, action):
        S = self.S
        self._vars[action] = {}
        self._kv[action] = {}
        body = self._collapsible(parent, S[action], opened=(action == 'steer'))

        # Input binding row (assign axis/button)
        brow = tk.Frame(body, bg=T['surface'])
        brow.pack(fill='x', pady=2)
        tk.Label(brow, text=S['binding'], width=12, anchor='w', bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')
        val = tk.Label(brow, text=binding_label(self._prof()['bindings'][action], S),
                       width=16, anchor='w', bg=T['overlay'], fg=T['text'],
                       font=('Consolas', 8), padx=6)
        val.pack(side='left', padx=4)
        btn = tk.Button(brow, text=S['assign'], font=('Segoe UI', 8), bg=T['overlay'], fg=T['text'],
                        activebackground=T['accent'], relief='flat', padx=6, pady=1,
                        cursor='hand2', command=lambda k=action: self._start_bind(k))
        btn.pack(side='left')
        self._bw[action] = (val, btn)

        # Output key(s) + optional combo key
        slots = [('neg', 'key_neg'), ('pos', 'key_pos')] if action == 'steer' else [('main', 'output_key')]
        slots = slots + [('second', 'key_second')]
        for slot, lbl in slots:
            self._key_entry(body, action, slot, S[lbl])

        # Override toggle + parameter set
        self._ovr[action] = tk.BooleanVar(value=self._prof()['actions'][action]['_override'])
        tk.Checkbutton(body, text=S['p_override'], variable=self._ovr[action],
                       bg=T['surface'], fg=T['accent'], selectcolor=T['overlay'],
                       activebackground=T['surface'], activeforeground=T['accent'],
                       font=('Segoe UI', 9, 'bold'), anchor='w', command=self._sync_cfg
                       ).pack(fill='x', pady=(4, 0))
        for spec in PARAM_SPEC:
            self._param_control(body, action, spec, source=self._prof()['actions'][action]['params'])

    # ── Widget builders ──────────────────────────────────────────────────────────
    def _collapsible(self, parent, title, opened=True):
        wrap = tk.Frame(parent, bg=T['surface'])
        wrap.pack(fill='x', padx=8, pady=(5, 0))
        body = tk.Frame(wrap, bg=T['surface'], padx=10, pady=6)
        state = {'open': opened}

        def toggle():
            if state['open']:
                body.pack_forget()
            else:
                body.pack(fill='x')
            state['open'] = not state['open']
            hdr.config(text=('▾ ' if state['open'] else '▸ ') + title)

        hdr = tk.Button(wrap, text=('▾ ' if opened else '▸ ') + title, anchor='w',
                        font=('Segoe UI', 8, 'bold'), bg=T['surface'], fg=T['dim'],
                        activebackground=T['surface'], activeforeground=T['accent'],
                        relief='flat', padx=4, pady=3, cursor='hand2', command=toggle)
        hdr.pack(fill='x')
        if opened:
            body.pack(fill='x')
        return body

    def _key_entry(self, parent, action, slot, label):
        src = self._prof()['actions'][action]['keys'].get(slot, '')
        var = tk.StringVar(value=src)
        self._kv[action][slot] = var
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=2)
        tk.Label(row, text=label, width=12, anchor='w', bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')
        ent = tk.Entry(row, width=10, textvariable=var, bg=T['overlay'], fg=T['text'],
                       insertbackground=T['text'], font=('Consolas', 9), bd=0,
                       highlightthickness=1, highlightcolor=T['accent'], highlightbackground=T['dim'])
        ent.pack(side='left', padx=4)
        var.trace_add('write', lambda *a: self._sync_cfg())

    def _param_control(self, parent, scope, spec, source=None):
        key, lbl_key, kind, lo, hi, fmt = spec
        src = source if source is not None else self._prof()['global']
        S = self.S
        label = S.get(lbl_key, lbl_key)

        if kind == 'bool':
            var = tk.BooleanVar(value=bool(src.get(key, GLOBAL_DEFAULTS[key])))
            self._vars[scope][key] = var
            tk.Checkbutton(parent, text=label, variable=var, bg=T['surface'], fg=T['text'],
                           selectcolor=T['overlay'], activebackground=T['surface'],
                           activeforeground=T['text'], font=('Segoe UI', 9), anchor='w',
                           command=self._sync_cfg).pack(fill='x', pady=1)
            return

        if kind == 'choice':
            var = tk.StringVar(value=str(src.get(key, GLOBAL_DEFAULTS[key])))
            self._vars[scope][key] = var
            row = tk.Frame(parent, bg=T['surface'])
            row.pack(fill='x', pady=1)
            tk.Label(row, text=label, width=14, anchor='w', bg=T['surface'], fg=T['text'],
                     font=('Segoe UI', 9)).pack(side='left')
            opts = CHOICE_OPTIONS.get(key, CURVE_TYPES)
            om = tk.OptionMenu(row, var, *opts)
            om.config(bg=T['overlay'], fg=T['text'], activebackground=T['accent'], relief='flat',
                      highlightthickness=0, font=('Segoe UI', 8), width=8)
            om['menu'].config(bg=T['overlay'], fg=T['text'])
            om.pack(side='right')
            var.trace_add('write', lambda *a: self._sync_cfg())
            return

        # numeric slider with click-to-type value
        is_int = (kind == 'int')
        var = (tk.IntVar if is_int else tk.DoubleVar)(value=src.get(key, GLOBAL_DEFAULTS[key]))
        self._vars[scope][key] = var
        res = 1 if is_int else 0.01
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=1)
        tk.Label(row, text=label, width=14, anchor='w', bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')

        box = tk.Frame(row, bg=T['surface'])
        box.pack(side='right')
        val_lbl = tk.Label(box, text=fmt.format(var.get()), width=6, anchor='e', bg=T['surface'],
                           fg=T['accent'], font=('Consolas', 9), cursor='xterm')
        val_lbl.pack()
        val_entry = tk.Entry(box, width=6, bg=T['overlay'], fg=T['text'], insertbackground=T['text'],
                             font=('Consolas', 9), bd=0, highlightthickness=1,
                             highlightcolor=T['accent'], highlightbackground=T['dim'])

        def show_entry(_=None):
            val_lbl.pack_forget()
            val_entry.delete(0, 'end')
            val_entry.insert(0, fmt.format(var.get()).strip())
            val_entry.pack()
            val_entry.focus_set()
            val_entry.select_range(0, 'end')

        def commit(_=None):
            try:
                v = max(lo, min(hi, float(val_entry.get())))
                var.set(int(v) if is_int else v)
                val_lbl.config(text=fmt.format(var.get()))
            except ValueError:
                pass
            val_entry.pack_forget()
            val_lbl.pack()
            self._sync_cfg()

        def cancel(_=None):
            val_entry.pack_forget()
            val_lbl.pack()

        val_lbl.bind('<Button-1>', show_entry)
        val_entry.bind('<Return>', commit)
        val_entry.bind('<FocusOut>', commit)
        val_entry.bind('<Escape>', cancel)

        def on_change(v):
            val_lbl.config(text=fmt.format(float(v)))
            self._sync_cfg()

        tk.Scale(row, from_=lo, to=hi, variable=var, orient='horizontal', resolution=res,
                 bg=T['overlay'], fg=T['text'], troughcolor=T['surface'], activebackground=T['accent'],
                 highlightthickness=0, bd=0, showvalue=False, length=120,
                 command=on_change).pack(side='left', fill='x', expand=True, padx=6)

    def _bar_row(self, parent, label):
        row = tk.Frame(parent, bg=T['surface'])
        row.pack(fill='x', pady=2)
        tk.Label(row, text=label, width=8, anchor='w', bg=T['surface'], fg=T['text'],
                 font=('Segoe UI', 9)).pack(side='left')
        c = tk.Canvas(row, height=12, bg=T['overlay'], highlightthickness=0)
        c.pack(side='left', fill='x', expand=True, padx=6)
        rect = c.create_rectangle(0, 0, 0, 12, fill=T['accent'], outline='')
        return (c, rect)

    def _refresh_leds(self):
        """(Re)build the LED indicator row to reflect the current output keys."""
        if not getattr(self, '_led_row', None) or not self._led_row.winfo_exists():
            return
        for w in self._led_row.winfo_children():
            w.destroy()
        self._leds = {}
        prof = self._prof()
        slots = [
            ('steer', 'neg'), ('steer', 'pos'),
            ('throttle', 'main'), ('brake', 'main'), ('reset', 'main'),
        ]
        for action, slot in slots:
            name = prof['actions'][action]['keys'].get(slot, '')
            letter = (name[:1].upper() or '·')
            lbl = tk.Label(self._led_row, text=letter, width=3, font=('Segoe UI', 13, 'bold'),
                           bg=T['overlay'], fg=T['dim'], padx=4, pady=3)
            lbl.pack(side='left', padx=3)
            self._leds[name] = lbl

    # ── Language ─────────────────────────────────────────────────────────────────
    def _toggle_lang(self):
        self._cancel_bind()
        self._lang = 'de' if self._lang == 'en' else 'en'
        self.config_data['lang'] = self._lang
        S = self.S
        self._lang_btn.config(text=S['lang_btn'])
        self._start_btn.config(text=S['stop'] if self.running else S['start'])
        self._save_btn.config(text=S['save'])
        self._build_content()
        self._refresh_ctrl()

    # ── Profiles ───────────────────────────────────────────────────────────────────
    def _switch_profile(self, name):
        self._collect()
        if name in self.config_data['profiles']:
            self.config_data['active'] = name
            self._rebuild_runtime()
            self._build_content()
            self._refresh_ctrl()

    def _profile_new(self):
        name = simpledialog.askstring('polycontroller', self.S['ask_new'], parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name in self.config_data['profiles']:
            return
        self.config_data['profiles'][name] = default_profile()
        self._after_profile_change(name)

    def _profile_dup(self):
        self._collect()
        base = simpledialog.askstring('polycontroller', self.S['ask_new'],
                                      initialvalue=self.config_data['active'] + ' 2', parent=self)
        if not base:
            return
        base = base.strip()
        if not base or base in self.config_data['profiles']:
            return
        self.config_data['profiles'][base] = copy.deepcopy(self._prof())
        self._after_profile_change(base)

    def _profile_rename(self):
        old = self.config_data['active']
        name = simpledialog.askstring('polycontroller', self.S['ask_ren'],
                                      initialvalue=old, parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name in self.config_data['profiles']:
            return
        self._collect()
        profs = self.config_data['profiles']
        profs[name] = profs.pop(old)
        self._after_profile_change(name)

    def _profile_delete(self):
        if len(self.config_data['profiles']) <= 1:
            messagebox.showinfo('polycontroller', self.S['del_last'], parent=self)
            return
        name = self.config_data['active']
        if not messagebox.askyesno('polycontroller', self.S['del_confirm'].format(name), parent=self):
            return
        del self.config_data['profiles'][name]
        self._after_profile_change(next(iter(self.config_data['profiles'])))

    def _profile_export(self):
        self._collect()
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.json',
                                            initialfile=self.config_data['active'] + '.json',
                                            filetypes=[('JSON', '*.json')])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'name': self.config_data['active'], 'profile': self._prof()}, f, indent=2)

    def _profile_import(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            prof = data.get('profile', data)
            _fill_profile(prof)
            name = data.get('name') or os.path.splitext(os.path.basename(path))[0]
            while name in self.config_data['profiles']:
                name += '*'
            self.config_data['profiles'][name] = prof
            self._after_profile_change(name)
            messagebox.showinfo('polycontroller', self.S['imp_ok'].format(name), parent=self)
        except Exception:
            messagebox.showerror('polycontroller', self.S['imp_err'], parent=self)

    def _after_profile_change(self, active):
        self.config_data['active'] = active
        self._prof_var.set(active)
        self._rebuild_profile_menu()
        self._rebuild_runtime()
        self._build_content()
        self._refresh_ctrl()

    # ── Controller ─────────────────────────────────────────────────────────────────
    def _refresh_ctrl(self):
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count():
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
            name = self.joy.get_name()
            self._ctrl_lbl.config(text=name)
            self._dot.config(fg=T['green'])
            if self._fresh_install:
                preset = match_preset(name)
                if preset:
                    self._prof()['bindings'] = preset
                    for key, (val, _) in self._bw.items():
                        val.config(text=binding_label(self._prof()['bindings'][key], self.S))
                self._fresh_install = False
        else:
            self.joy = None
            self._ctrl_lbl.config(text=self.S['no_controller'])
            self._dot.config(fg=T['red'])

    # ── Binding flow ───────────────────────────────────────────────────────────────
    def _start_bind(self, key):
        if not self.joy or self.binding:
            return
        pygame.event.pump()
        self._base_axes = [self.joy.get_axis(i) for i in range(self.joy.get_numaxes())]
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
            delta = self.joy.get_axis(i) - self._base_axes[i]
            if abs(delta) > 0.5:
                if key == 'steer':
                    b = {'type': 'axis', 'index': i}
                else:
                    b = {'type': 'axis_pos' if delta > 0 else 'axis_neg', 'index': i,
                         'rest': round(self._base_axes[i], 3)}
                self._finish_bind(key, b)
                return
        self.b_tick += 1
        if self.b_tick >= 100:
            self._cancel_bind()
            return
        self.after(50, self._poll_bind)

    def _finish_bind(self, key, binding):
        self._prof()['bindings'][key] = binding
        self._rebuild_runtime()
        val, btn = self._bw[key]
        val.config(text=binding_label(binding, self.S))
        btn.config(text=self.S['assign'], bg=T['overlay'], fg=T['text'])
        self.binding = None

    def _cancel_bind(self):
        if self.binding:
            key = self.binding
            val, btn = self._bw[key]
            val.config(text=binding_label(self._prof()['bindings'][key], self.S))
            btn.config(text=self.S['assign'], bg=T['overlay'], fg=T['text'])
            self.binding = None

    # ── Start / Stop ─────────────────────────────────────────────────────────────
    def _toggle(self):
        S = self.S
        if self.running:
            self.worker.stop()
            self.worker = None
            self.running = False
            self._start_btn.config(text=S['start'], bg=T['accent'])
        else:
            if not self.joy:
                self._refresh_ctrl()
            if not self.joy:
                return
            self._collect()
            self.worker = Worker(self.joy, lambda: self._runtime, self.status, self.s_lock)
            self.worker.start()
            self.running = True
            self._start_btn.config(text=S['stop'], bg=T['red'])

    # ── Tick (GUI update) ──────────────────────────────────────────────────────────
    def _tick(self):
        if self.running:
            with self.s_lock:
                s = dict(self.status)
            if s:
                for k in ('l', 'r', 'w', 's'):
                    self._set_bar(k, s.get(k, 0))
                keys = s.get('keys', {})
                for name, lbl in self._leds.items():
                    on = keys.get(name, False)
                    lbl.config(bg=T['green'] if on else T['overlay'], fg=T['bg'] if on else T['dim'])
        else:
            for k in ('l', 'r', 'w', 's'):
                self._set_bar(k, 0.0)
            for lbl in self._leds.values():
                lbl.config(bg=T['overlay'], fg=T['dim'])
        self.after(60, self._tick)

    def _set_bar(self, key, value):
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
    App().mainloop()
