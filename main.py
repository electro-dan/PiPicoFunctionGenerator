import utime
from time import sleep
from machine import Pin
from machine import WDT
from machine import Timer
from mpy_decimal import *
from lcd import HD44780
from ad9833 import AD9833

#wdt = WDT(timeout=8000)
display = HD44780()
ad9833 = AD9833()

# based on https://electrocredible.com/matrix-keypad-raspberry-pi-pico-micropython/ 4×4
# I used numbers instead of strings to make the maths better
keyMatrixNum = [
    [ 1, 2, 3, 10 ],
    [ 4, 5, 6, 11 ],
    [ 7, 8, 9, 12 ],
    [ 14, 0, 15, 13 ]
]
# altered pins as I wired rows first
colPins = [7,6,5,4] 
rowPins = [3,2,1,0]
row = []
column = []

# 10 A - increase 1/4 octave
# 11 B - decrease 1/4 octave
# 12 C - cancel
# 13 D - apply - toggle on / off
# 15 # - toggle sine / triangle / square
# 14 * - decimal point

frequency = DecimalNumber(10000, 1) # default to 1kHz
new_frequency = DecimalNumber(0, 1)
max_freq = DecimalNumber(125000000, 1) # 12.5 MHz
min_freq = DecimalNumber(0, 1)
wave = 0  # 0 = sine, 1 = triangle, 2 = square
last_key = 0
timer_blink = Timer()
blink = True

# 1/3 octaves (multiplied by 10):
octaves_1_3 = [125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000, 25000, 31500, 40000, 50000, 63000, 80000, 100000, 125000, 160000, 200000]

# based on https://electrocredible.com/matrix-keypad-raspberry-pi-pico-micropython/
for item in rowPins:
    row.append(Pin(item, Pin.OUT))
for item in colPins:
    column.append(Pin(item, Pin.IN, Pin.PULL_DOWN))
key = 0

# based on https://electrocredible.com/matrix-keypad-raspberry-pi-pico-micropython/
def scanKeypad():
    global key
    for rowKey in range(4):
        row[rowKey].value(1)
        for colKey in range(4):
            if column[colKey].value() == 1:
                key = keyMatrixNum[rowKey][colKey]
                row[rowKey].value(0)
                return(key)
        row[rowKey].value(0)

def flip_blink(pin):
    global blink
    blink = not blink
    showFrequency(new_frequency, True)

# Runs constantly via the main method
# this would be better as an async task to prevent blocking, but since it's the only task needed this is OK for now
def handleKey():
    global last_key
    global frequency
    global new_frequency
    global wave

    key = scanKeypad()
    if key is not None:
        if key < 10:
            # Start a timer to interrupt every 1 second
            timer_blink.init(mode=Timer.PERIODIC, period=500, callback=flip_blink)
            if last_key == 14:
                # If 'dot' * was last pressed, this key will do the decimal part
                new_frequency = new_frequency.to_int_truncate() + DecimalNumber(key, 1)
                showFrequency(new_frequency, True)
            else:
                if new_frequency == 0:
                    new_frequency = DecimalNumber(key, 0)
                else:
                    new_frequency = (new_frequency.to_int_truncate() * DecimalNumber(10, 0)) + DecimalNumber(key, 0)
                if new_frequency <= max_freq:
                    showFrequency(new_frequency, True)
                else:
                    display.set_line(1)
                    display.set_string("Err: Max 12.5MHz")
                    new_frequency = DecimalNumber(0)
                    showFrequency(new_frequency, True)
                    return
        elif key == 12:
            # Cancel
            timer_blink.deinit()
            new_frequency = DecimalNumber(0)
            showFrequency(frequency, False)
        elif key == 13:
            # Apply frequency, or toggle on/off
            timer_blink.deinit()
            if new_frequency != frequency and new_frequency > DecimalNumber(0):
                frequency = new_frequency
                new_frequency = DecimalNumber(0)

            showFrequency(frequency, False)
        elif key == 15:
            # Change wave type
            wave = wave + 1
            if wave > 2:
                wave = 0
        elif key == 10:
            # Increase 1/3 octave
            timer_blink.deinit()
            new_frequency = DecimalNumber(0)
            for i in range(32):
                octave_1_3 = DecimalNumber(octaves_1_3[i], 1)
                if octave_1_3 > frequency:
                    frequency = octave_1_3
                    break
            showFrequency(frequency, False)
        elif key == 11:
            # Decrease 1/3 octave
            timer_blink.deinit()
            new_frequency = DecimalNumber(0)
            for i in range(32, 0, -1):
                octave_1_3 = DecimalNumber(octaves_1_3[i], 1)
                if octave_1_3  < frequency:
                    frequency = octave_1_3
                    break
            showFrequency(frequency, False)

        last_key = key
        showStatus()
        updateAD8833()
        
    # debounce
    utime.sleep(0.1)

# Format the frequency onto the LCD display
def showFrequency(freq_in, editing):
    display.set_line(0)
    # Left filled with spaces (prefixed) to 12 characters
    if (editing & blink):
        display.set_string(" {:>12}_Hz".format(freq_in.to_string_thousands()))
    else:
        display.set_string(" {:>12} Hz".format(freq_in.to_string_thousands()))

def updateAD8833():
    # Set the frequency
    ad9833.change_freq(frequency)
    # Apply the wave type
    if wave == 0:   
        ad9833.set_sine()
    elif wave == 1:
        ad9833.set_triangle()
    elif wave == 2:
        ad9833.set_square()

def showStatus():
    # The second line shows On/Off status and the wave type being output
    display.set_line(1)
    wave_str = "Sine"
    running_str ="ON"
    if wave == 1:
        wave_str = "Triangle"
    elif wave == 2:
        wave_str = "Square"
    
    # Wave type right filled (suffixed) to 13 characters, leaving 3 characters to display ON/OFF
    display.set_string("{:<13}{:}".format(wave_str, running_str))


# Entry Here
utime.sleep(1)
display.init()

showFrequency(frequency, False)
showStatus()
updateAD8833()

while True:
    handleKey()
    #wdt.feed()