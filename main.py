import utime
from time import sleep
from machine import Pin
from mpy_decimal import *
from lcd import HD44780
from ad9833 import AD9833

display = HD44780()
ad9833 = AD9833()

# https://electrocredible.com/matrix-keypad-raspberry-pi-pico-micropython/
#keyMatrix = [
#    [ "1", "2", "3", "A" ],
#    [ "4", "5", "6", "B" ],
#    [ "7", "8", "9", "C" ],
#    [ "*", "0", "#", "D" ]
#]
keyMatrixNum = [
    [ 1, 2, 3, 10 ],
    [ 4, 5, 6, 11 ],
    [ 7, 8, 9, 12 ],
    [ 14, 0, 15, 13 ]
]
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
running = 0 # 0 = off, 1 = on
last_key = 0

# 1/3 octaves (multiplied by 10):
octaves_1_3 = [125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000, 25000, 31500, 40000, 50000, 63000, 80000, 100000, 125000, 160000, 200000]

for item in rowPins:
    row.append(Pin(item, Pin.OUT))
for item in colPins:
    column.append(Pin(item, Pin.IN, Pin.PULL_DOWN))
key = 0

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


def handleKey():
    global last_key
    global frequency
    global new_frequency
    global running
    global wave

    key = scanKeypad()
    if key is not None:
        if key < 10:
            if last_key == 14:
                # If 'dot' * was last pressed, this key will do the decimal part
                new_frequency = new_frequency.to_int_truncate() + DecimalNumber(key, 1)
                showFrequency(new_frequency)
            else:
                if new_frequency == 0:
                    new_frequency = DecimalNumber(key, 0)
                else:
                    new_frequency = (new_frequency.to_int_truncate() * DecimalNumber(10, 0)) + DecimalNumber(key, 0)
                if new_frequency <= max_freq:
                    showFrequency(new_frequency)
                else:
                    display.set_line(1)
                    display.set_string("Err: Max 12.5MHz")
                    new_frequency = 0
                    showFrequency(new_frequency)
                    return
        elif key == 12:
            # Cancel
            new_frequency = DecimalNumber(0)
            showFrequency(frequency)
        elif key == 13:
            # Apply frequency, or toggle on/off
            if new_frequency != frequency and new_frequency > DecimalNumber(0):
                frequency = new_frequency
                new_frequency = DecimalNumber(0)
                running = True
            else:
                running = not running

            showFrequency(frequency)
        elif key == 15:
            # Change wave type
            wave = wave + 1
            if wave > 2:
                wave = 0
        elif key == 10:
            # Increase 1/3 octave
            new_frequency = DecimalNumber(0)
            for i in range(32):
                octave_1_3 = DecimalNumber(octaves_1_3[i], 1)
                if octave_1_3 > frequency:
                    frequency = octave_1_3
                    break
            showFrequency(frequency)
        elif key == 11:
            # Decrease 1/3 octave
            new_frequency = DecimalNumber(0)
            for i in range(32, 0, -1):
                octave_1_3 = DecimalNumber(octaves_1_3[i], 1)
                if octave_1_3  < frequency:
                    frequency = octave_1_3
                    break
            showFrequency(frequency)

        last_key = key
        showStatus()
        updateAD8833()
        
    # debounce
    utime.sleep(0.1)

def showFrequency(freq_in):
    display.set_line(0)
    # Bug in format means only integers have thousands separator (,), so decimal is split into integer and fractional part
    # Integer part is left filled (prefixed) to 10 characters
    display.set_string(" {:>12} Hz".format(freq_in.to_string_thousands()))

def updateAD8833():
    if running:
        ad9833.change_freq(frequency)
        if wave == 0:   
            ad9833.set_sine()
        elif wave == 1:
            ad9833.set_triangle()
        elif wave == 2:
            ad9833.set_square()
    else:
        ad9833.change_freq(DecimalNumber(0))

def showStatus():
    display.set_line(1)
    wave_str = "Sine"
    running_str ="OFF"
    if wave == 1:
        wave_str = "Triangle"
    elif wave == 2:
        wave_str = "Square"
    
    if running:
        running_str ="ON"
    
    # Wave type right filled (suffixed) to 13 characters, leaving 3 characters to display ON/OFF
    display.set_string("{:<13}{:}".format(wave_str, running_str))


# Entry Here
display.init()

showFrequency(frequency)
showStatus()
updateAD8833()

while True:
    handleKey()
    