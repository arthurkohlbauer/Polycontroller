"""
Diagnostic tool — shows all controller axes and button values live.
Move sticks, press triggers and buttons and watch which index changes.
Ctrl+C to quit.
"""

import time
import sys
import pygame

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No controller found. Connect a controller and restart.")
    sys.exit(1)

joy = pygame.joystick.Joystick(0)
joy.init()

print(f"Controller : {joy.get_name()}")
print(f"Axes       : {joy.get_numaxes()}")
print(f"Buttons    : {joy.get_numbuttons()}")
print(f"Hats       : {joy.get_numhats()}")
print("\nMove sticks, press triggers and buttons — watch which values change.")
print("Ctrl+C to quit.\n")

try:
    while True:
        pygame.event.pump()

        axes = [f"[{i}]={joy.get_axis(i):+.2f}" for i in range(joy.get_numaxes())]
        btns = [f"[{i}]={'1' if joy.get_button(i) else '0'}" for i in range(joy.get_numbuttons())]
        hats = [f"[{i}]={joy.get_hat(i)}" for i in range(joy.get_numhats())]

        print(f"\rAxes: {'  '.join(axes)}   Btns: {'  '.join(btns)}   Hats: {'  '.join(hats)}   ", end='', flush=True)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nDone.")
    pygame.quit()
