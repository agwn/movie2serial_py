#!/usr/bin/env python

from __future__ import print_function
from __future__ import division

import serial           # serial output
import time             # delays
#import numpy            # arrays
from PointsAndRectangles import Rect
from PIL import Image   # PIL
from threading import Thread
from Queue import Queue
from DemoTransmitter import DemoTransmitter
import socket

numPorts = 0            # the number of serial ports in use
maxPorts = 8            # maximum number of serial ports


ledSerial = []          # serial handles to all connected displays
ledArea = []            # the area of the movie each port gets, in % (0-100)
ledLayout = []          # layout of rows, true = even is left->right
ledImage = []           # image sent to each port
errorCount = 0
framerate = 0

ledCnt = 60             # Number of lights along the strip
stripCnt = 32           # Number of strips around the circumference of the sphere
packet_length = stripCnt*ledCnt*3 + 1

demoMode = True
newImageQueue = None

# ledstar interaction components
demoTransmitter = None


UDP_IP = "127.0.0.1"
UDP_PORT = 58082

udp = None

maxConvertedByte = 0

def setup():
    global newImageQueue
    global udp
    global demoTransmitter
    
    newImageQueue = Queue(2)
    #serialConfigure("dummy")
    serialConfigure("COM46")
    
    # configure input
    #udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # UDP
    #udp.bind((UDP_IP, UDP_PORT))
    
    # create window
    #size(ledCnt, stripCnt)  # create the window
    
    demoTransmitter = DemoTransmitter(stripCnt, ledCnt)
    demoTransmitter.start()



def mapByte(b):
    global maxConvertedByte
    
    c = 256+b if (b<0) else b

    if (c > maxConvertedByte):
        maxConvertedByte = c
        print('Max Converted Byte is now '+c)

    return c


#while True:
#    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
#    print "received message:", data

def receive(data, ip, port):
    global demoMode
    global modeName
    global newImageQueue
    
    print(' new datas!')
    if (demoMode):
        print('Started receiving data from '+ip+'. Demo mode disabled.')
        # should switch back if no data stops coming
        demoMode = false

    if (data[0] == 2):
        # We got a new mode, so copy it out
        modeName = data[:]
        return

    if (data[0] != 1):
        print('Packet header mismatch. Expected 1, got '+data[0])

    if (data.length != packet_length):
        print('Packet size mismatch. Expected '+packet_length+', got '+data.length)

    if (newImageQueue.size() > 0):
        print('Buffer full, dropping frame!')
        return

    newImage = Image.new('RGB',stripCnt,ledCnt)

#    for i in range(stripCnt*ledCnt):
#        newImage[i] = (int)(0xff<<24 | mapByte(data[i*3 + 1])<<16) | (mapByte(data[i*3 + 2])<<8) | (mapByte(data[i*3 + 3]))

    for i in range(ledCnt):
       for j in range(ledCnt):
           loc = (i*stripCnt+j)
           newImage[loc] = int((0xff<<24 | mapByte(data[loc*3 + 1])<<16) | (mapByte(data[loc*3 + 2])<<8) | (mapByte(data[loc*3 + 3])))

    try:
        newImageQueue.put(newImage)
    except KeyboardInterrupt, msg:
        print('Interrupted Exception caught {0}'.format(msg[1]))



# movieEvent runs for each new frame of movie data
def frameUpdate(f):
    #global ledData
    #global ledSerial

    for i in range(numPorts):
        # copy a portion of the movie's image to the LED image
        xoffset = percentage(ledImage[i].width, ledArea[i].x)
        yoffset = percentage(ledImage[i].height, ledArea[i].y)
        xwidth =  percentage(ledImage[i].width, ledArea[i].width)
        yheight = percentage(ledImage[i].height, ledArea[i].height)
        print(xoffset+" "+yoffset+" "+xwidth+" "+yheight+" "+0+" "+0+" "+ledImage[i].width+" "+ 
              ledImage[i].height+" "+ledArea[i].width+" "+ledArea[i].height)
        ledImage[i].copy(f, xoffset, yoffset, xwidth, yheight, 0, 0, ledImage[i].width, ledImage[i].height)
        # convert the LED image to raw data
        ledData =  byte[(ledImage[i].width * ledImage[i].height * 3) + 3]
        image2data(ledImage[i], ledData, ledLayout[i])
        if (i == 0):
            ledData[0] = '*'  # first Teensy is the frame sync master
            usec = int(((1000000.0 / framerate) * 0.75))
            ledData[1] = (byte)(usec)   # request the frame sync pulse
            ledData[2] = (byte)(usec >> 8) # at 75% of the frame time
        else:
            ledData[0] = '%'  # others sync to the master board
            ledData[1] = 0
            ledData[2] = 0

        # send the raw data to the LEDs  :-)
        #print('write len: '+ledData.length)
        ledSerial[i].write(ledData)


### movieEvent runs for each new frame of movie data
##void movieEvent(Movie m):
##    # read the movie's next frame
##    m.read()
##    
##    #if (framerate == 0) framerate = m.getSourceFrameRate()
##    framerate = 30.0 # TODO, how to read the frame rate???
##    
##    for i in range(numPorts):
##        # copy a portion of the movie's image to the LED image
##        xoffset = percentage(m.width, ledArea[i].x)
##        yoffset = percentage(m.height, ledArea[i].y)
##        xwidth =  percentage(m.width, ledArea[i].width)
##        yheight = percentage(m.height, ledArea[i].height)
##        ledImage[i].copy(m, xoffset, yoffset, xwidth, yheight,
##                         0, 0, ledImage[i].width, ledImage[i].height)
##        # convert the LED image to raw data
##        byte[] ledData =  new byte[(ledImage[i].width * ledImage[i].height * 3) + 3]
##        image2data(ledImage[i], ledData, ledLayout[i])
##        if (i == 0):
##            ledData[0] = '*'  # first Teensy is the frame sync master
##            int usec = (int)((1000000.0 / framerate) * 0.75)
##            ledData[1] = (byte)(usec)   # request the frame sync pulse
##            ledData[2] = (byte)(usec >> 8) # at 75% of the frame time
##        else:
##            ledData[0] = '%'  # others sync to the master board
##            ledData[1] = 0
##            ledData[2] = 0
##        
##        # send the raw data to the LEDs  :-)
##        ledSerial[i].write(ledData) 
#
#
## image2data converts an image to OctoWS2811's raw data format.
## The number of vertical pixels in the image must be a multiple
## of 8.  The data array must be the proper size for the image.
#def void image2data(Image image, byte[] data, boolean layout):
#    offset = 3
#    x, y, xbegin, xend, xinc, mask
#    linesPerPin = image.height / 8
#    pixel[] = new int[8]
#
#    for y in range(linesPerPin):
#        if ((y & 1) == (layout ? 0 : 1)):
#            # even numbered rows are left to right
#            xbegin = 0
#            xend = image.width
#            xinc = 1
#        else:
#            # odd numbered rows are right to left
#            xbegin = image.width - 1
#            xend = -1
#            xinc = -1
#        for (x = xbegin; x != xend; x += xinc):
#            for (i=0; i < 8; i++):
#                # fetch 8 pixels from the image, 1 for each pin
#                pixel[i] = image.pixels[x + (y + linesPerPin * i) * image.width]
#                pixel[i] = colorWiring(pixel[i])
#            # convert 8 pixels to 24 bytes
#            for (mask = 0x800000; mask != 0; mask >>= 1) {
#                byte b = 0
#                for (i=0; i < 8; i++):
#                    if ((pixel[i] & mask) != 0):
#                        b |= (1 << i)
#                data[offset++] = b
#
### image2data converts an image to OctoWS2811's raw data format.
### The number of vertical pixels in the image must be a multiple
### of 8.  The data array must be the proper size for the image.
##void image2data(PImage image, byte[] data, boolean layout) {
##    int offset = 3
##    int x, y, xbegin, xend, xinc, mask
##    int linesPerPin = image.height / 8
##    int pixel[] = new int[8]
##
##    for (y = 0; y < linesPerPin; y++):
##        if ((y & 1) == (layout ? 0 : 1)):
##            # even numbered rows are left to right
##            xbegin = 0
##            xend = image.width
##            xinc = 1
##        else:
##            # odd numbered rows are right to left
##            xbegin = image.width - 1
##            xend = -1
##            xinc = -1
##
##        for (x = xbegin; x != xend; x += xinc):
##            for (int i=0; i < 8; i++):
##                # fetch 8 pixels from the image, 1 for each pin
##                pixel[i] = image.pixels[x + (y + linesPerPin * i) * image.width]
##                pixel[i] = colorWiring(pixel[i])
##            # convert 8 pixels to 24 bytes
##            for (mask = 0x800000; mask != 0; mask >>= 1):
##                byte b = 0
##                for (int i=0; i < 8; i++):
##                    if ((pixel[i] & mask) != 0):
##                        b |= (1 << i)
##                data[offset++] = b


# translate the 24 bit color from RGB to the actual
# order used by the LED wiring.  GRB is the most common.
def colorWiring(c):
    # return c  # RGB
    return ((c & 0xFF0000) >> 8) | ((c & 0x00FF00) << 8) | (c & 0x0000FF) # GRB - most common wiring


### ask a Teensy board for its LED configuration, and set up the info for it.
##def serialConfigure(portName):
##    # only store the info and increase numPorts if Teensy responds properly
##    ledImage[0] = Image.new('RGB', ledCnt, stripCnt)
##    print(stripCnt+'x'+ledCnt)
##
##    ledArea[0] = new Rectangle(0, 0, 60, 32)

# ask a Teensy board for its LED configuration, and set up the info for it.
def serialConfigure(portName):
    global numPorts
    global maxPorts
    global errorCount
    global ledSerial
    global ledArea
    global ledLayout
    global ledImage
    
    print(numPorts)
    
    if (numPorts >= maxPorts): 
        print('too many serial ports, please increase maxPorts')
        errorCount += 1
        return
    try:
        #ledSerial[numPorts] = serial.Serial(portName)
        ser = serial.Serial(portName)
        ledSerial.append(ser)
        if (ledSerial[numPorts] == None):
            raise NullPointer
        ledSerial[numPorts].write('?')
    except serial.SerialException, msg:
        print("Serial port " + portName + " does not exist or is non-functional\n{0}".format(msg[0]))
        errorCount += 1
        return
    time.sleep(0.05)
    line = ledSerial[numPorts].read(12)
    print(line)
    if (line == None):
        print("Serial port " + portName + " is not responding.")
        print("Is it really a Teensy 3.0 running VideoDisplay?")
        errorCount += 1
        return
    param = line.split(",")
    if (len(param) != 12):
        print("Error: port " + portName + " did not respond to LED config query")
        errorCount += 1
        return
    # only store the info and increase numPorts if Teensy responds properly
    ledImage[numPorts] = Image.new('RGB', int(param[0]), int(param[1]))
    ledArea[numPorts] = Rect((int(param[5]), int(param[6])), (int(param[7]), int(param[8])))
    ledLayout[numPorts] = (int(param[5]) == 0)
    numPorts += 1
    
    #ledImage[numPorts] = Image.new('RGB', Integer.parseInt(param[0]), Integer.parseInt(param[1]))
    #ledArea[numPorts] = Rect((Integer.parseInt(param[5]), Integer.parseInt(param[6])),
    #                         (Integer.parseInt(param[7]), Integer.parseInt(param[8])))
    #ledLayout[numPorts] = (Integer.parseInt(param[5]) == 0)
    #numPorts += 1


## draw runs every time the screen is redrawn - show the movie...
#def draw():
#    if (newImageQueue.size() > 0) {
#        color[] newImage = (color[])newImageQueue.remove()
#
#        # now need to stuff the values into a PImage
#        ledImage[0].loadPixels()
#        for (int i=0; i<ledCnt; i++):
#            for (int j=0; j<stripCnt; j++):
#                int loc = i*stripCnt+j
#                #print("i: "+i+" j: "+j+" "+hex(newImage[loc]))
#    
#                # Set the display pixel to the image pixel
#                ledImage[0].pixels[loc] = newImage[loc]
#        ledImage[0].updatePixels()
#
#        image(ledImage[0], 0, 0)
#
#        frameUpdate(nextImage)
#
#
### draw runs every time the screen is redrawn - show the movie...
##void draw() {
##  # show the original video
##  image(myMovie, 0, 80)
##  
##  # then try to show what was most recently sent to the LEDs
##  # by displaying all the images for each port.
##  for (int i=0; i < numPorts; i++) {
##    # compute the intended size of the entire LED array
##    int xsize = percentageInverse(ledImage[i].width, ledArea[i].width)
##    int ysize = percentageInverse(ledImage[i].height, ledArea[i].height)
##    # computer this image's position within it
##    int xloc =  percentage(xsize, ledArea[i].x)
##    int yloc =  percentage(ysize, ledArea[i].y)
##    # show what should appear on the LEDs
##    image(ledImage[i], 240 - xsize / 2 + xloc, 10 + yloc)
##  } 
##}
##


# scale a number by a percentage, from 0 to 100
def percentage(num, percent):
    mult = percentageFloat(percent)
    output = num * mult
    return int(output)


# scale a number by the inverse of a percentage, from 0 to 100
def percentageInverse(num, percent):
    div = percentageFloat(percent)
    output = num/div
    return int(output)

# convert an integer from 0 to 100 to a float percentage
# from 0.0 to 1.0.  Special cases for 1/3, 1/6, 1/7, etc
# are handled automatically to fix integer rounding.
def percentageFloat(percent):
    if (percent == 33):
        return (1.0/3.0)
    if (percent == 17):
        return (1.0/6.0)
    if (percent == 14):
        return (1.0/7.0)
    if (percent == 13):
        return (1.0/8.0)
    if (percent == 11):
        return (1.0/9.0)
    if (percent ==  9):
        return (1.0/11.0)
    if (percent ==  8):
        return (1.0/12.0)
    return int(float(percent)/100.0)


if __name__ == "__main__":
    print('Testing stream to serial')
    setup()
    #serialConfigure("dummy")
