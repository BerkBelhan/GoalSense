Place digit template images here.

One greyscale PNG per digit, named:
  0.png  1.png  2.png  …  9.png

The easiest way to create them is to run the calibration tool:
  python calibrate.py

Manual alternative
------------------
1. Take a screenshot of the game while the scoreboard shows each digit (0–9).
2. Crop tightly around each digit and save as a greyscale PNG.
3. Keep each template at the native game resolution – the detector will try
   small scale variations automatically (see TEMPLATE_SCALES in config.py).
