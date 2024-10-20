import utime
from time import sleep
from machine import Pin
from machine import WDT
from lcd import HD44780

# Will reset the Pico if unresponsive after 1 seconds. Use wdt.feed() to indicate 'alive'
wdt = WDT(timeout=1000) #timeout is in ms

display = HD44780()

# https://electrocredible.com/matrix-keypad-raspberry-pi-pico-micropython/
keyMatrix = [
    [ "1", "2", "3", "A" ],
    [ "4", "5", "6", "B" ],
    [ "7", "8", "9", "C" ],
    [ "*", "0", "#", "D" ]
]
colPins = [7,6,5,4]
rowPins = [3,2,1,0]
row = []
column = []

for item in rowPins:
    row.append(Pin(item, Pin.OUT))
for item in colPins:
    column.append(Pin(item, Pin.IN, Pin.PULL_DOWN))
key = '0'


def scanKeypad():
    global key
    for rowKey in range(4):
        row[rowKey].value(1)
        for colKey in range(4):
            if column[colKey].value() == 1:
                key = keyMatrix[rowKey][colKey]
                row[rowKey].value(0)
                return(key)
        row[rowKey].value(0)

def printKey():
    key = scanKeypad()
    if key is not None:
        display.set_line(1)
        display.set_string("Key :{}".format(key))
    utime.sleep(0.2)
    
# Entry Here
display.init()

display.set_line(0)
display.set_string("Hello world!")

while True:
    printKey()
    wdt.feed()
    