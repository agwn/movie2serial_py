#!/usr/bin/env python

from __future__ import print_function
from __future__ import division

import platform         # os identification

import serial           # serial output
import time             # delays

from PIL import Image   # PIL
import numpy as np      # arrays
from scipy import ndimage

from threading import Thread
from Queue import Queue
from DemoTransmitter import DemoTransmitter
import socket

import display

numPorts = 0            # the number of serial ports in use
maxPorts = 8            # maximum number of serial ports


serialPort = None

ledSerial = {}          # serial handles to all connected displays
ledArea = {}            # the area of the movie each port gets, in % (0-100)
ledLayout = {}          # layout of rows, true = even is left->right
ledImage = {}           # image sent to each port
errorCount = 0
framerate = 15

stripCnt = 32           # Number of strips around the circumference of the sphere
ledCnt = 60             # Number of lights along the strip
packet_length = stripCnt*ledCnt*3 + 1

demoMode = True
newImageQueue = None

# ledstar interaction components
demoTransmitter = None


#UDP_IP = "127.0.0.1"
#UDP_PORT = 58082

#udp = None

maxConvertedByte = 0

def setup():
    global newImageQueue
    global udp
    global demoTransmitter
    global serialPort
    
    newImageQueue = Queue(2)

    print(platform.platform())
    os = platform.platform()
    if ('Linux' in os):
        serialPort = '/dev/ttyACM0'
    elif ('Windows' in os):
        serialPort = 'COM6'
    else:
        # should not get here
        serialPort = 'dummy'
    # testing
    serialPort = 'dummy'
    serialConfigure(serialPort)
    
    # configure input
    #udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # UDP
    #udp.bind((UDP_IP, UDP_PORT))
    
    # create window
    #size(ledCnt, stripCnt)  # create the window
    
    demoTransmitter = DemoTransmitter(ledCnt, stripCnt, newImageQueue)
    demoTransmitter.start()

#while True:
#    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
#    print "received message:", data


def mapByte(b):
    global maxConvertedByte
    
    c = 256+b if (b<0) else b

    if (c > maxConvertedByte):
        maxConvertedByte = c
        print('Max Converted Byte is now '+c)

    return c


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

    newImage = np.zeros((ledCnt, stripCnt,3), 'uint8')

    for i in range(ledCnt):
       for j in range(ledCnt):
           loc = (i*stripCnt+j)
           newImage[loc] = int((0xff<<24 | mapByte(data[loc*3 + 1])<<16) | (mapByte(data[loc*3 + 2])<<8) | (mapByte(data[loc*3 + 3])))

    try:
        newImageQueue.put(newImage)
    except KeyboardInterrupt, msg:
        print('Interrupted Exception caught {0}'.format(msg[1]))


# frameUpdate runs for each new frame received from newImageQueue
def frameUpdate(f):
    global ledImage
    global ledArea
    global ledSerial

    for i in range(numPorts):
        # copy a portion of the movie's image to the LED image
        imageWidth,imageHeight,colorDepth = ledImage[i].shape
        areaX  = ledArea[i][0][0]
        areaY = ledArea[i][0][1]
        areaWidth  = ledArea[i][1][0]-ledArea[i][0][0]
        areaHeight = ledArea[i][1][1]-ledArea[i][0][1]

        xoffset = percentage(imageWidth, areaX)
        yoffset = percentage(imageHeight, areaY)
        xwidth =  percentage(imageWidth, areaWidth)
        yheight = percentage(imageHeight, areaHeight)
        #print('frameUpdate:','xoff',xoffset,'yoff',yoffset,'xw',xwidth,'yh',yheight,0,0,
        #        'iw',imageWidth,'ih',imageHeight,'aw',areaWidth,'ah',areaHeight)
        ledImage[i] = f[xoffset:(xoffset+xwidth), yoffset:(yoffset+yheight)]

        # convert the LED image to raw data
        ledData = image2data(ledImage[i], ledLayout[i])
        serialData = list(ledData.flatten())

        if (i == 0):
            usec = int(((1000000.0 / framerate) * 0.75))
            serialData.insert(0, 0xff&int(usec >> 8)) # at 75% of the frame time
            serialData.insert(0, 0xff&int(usec))   # request the frame sync pulse
            serialData.insert(0, ord('*'))  # first Teensy is the frame sync master
        else:
            serialData.insert(0, 0)
            serialData.insert(0, 0)
            serialData.insert(0, ord('%'))  # others sync to the master board

        # send the raw data to the LEDs  :-)
        print(serialData[:(3+3*6)])
        
        #ledSerial[i].write(serialData)


# image2data converts an image to OctoWS2811's raw data format.
# The number of vertical pixels in the image must be a multiple
# of 8.  The data array must be the proper size for the image.
def image2data(image, layout):
    debugConvert = False
    
    offset = 3
    #xbegin, xend, xinc, mask
    colCnt = image.shape[0]
    rowCnt = image.shape[1]
    linesPerPin = rowCnt // 8
    pixel = np.zeros((8,colCnt*linesPerPin,3), 'uint8')
    if debugConvert:
        print('image2data pixels', pixel.shape)

    # swap rows and columns to make indexing easier
    #with image.transpose((1,0,2)) as im:
    im = image.transpose((1,0,2))
    if debugConvert:
        print('image2data im',im.shape)
        print(im[0:3,0])

    for i in range(8):
        for y in range(linesPerPin):
            if ((y & 1) == (0 if layout else 1)):
                # even numbered rows are left to right
                if debugConvert:
                    print('>'+str((i*linesPerPin)+y),'',end='')
                pixel[i,y*colCnt:(y+1)*colCnt] = im[i*linesPerPin+y,:colCnt]
            else:
                # odd numbered rows are right to left
                if debugConvert:
                    print('<'+str((i*linesPerPin)+y),'',end='')
                pixel[i,y*colCnt:(y+1)*colCnt] = im[i*linesPerPin+y,colCnt::-1]
        if debugConvert:
            print()

    # remap colors as needed
    pixel = colorWiring(pixel)
    return pixel[:,::-1,:]


# translate the 24 bit color from RGB to the actual
# order used by the LED wiring.  GRB is the most common.
def colorWiring(pxls):
    return pxls                 # RGB
    #return pxls[:,:,(2,0,1)]   # GRB


# ask a Teensy board for its LED configuration, and set up the info for it.
def serialConfigure(portName):
    global numPorts
    global maxPorts
    global errorCount
    global ledSerial
    global ledArea
    global ledLayout
    global ledImage
    
    if (numPorts >= maxPorts): 
        print('too many serial ports, please increase maxPorts')
        errorCount += 1
        return
    
    if 'dummy' == portName:
        print('Configuring for:',portName)
        param = [ledCnt,stripCnt,0,0,0,0,0,100,100]
        ledImage[numPorts] = np.zeros((int(param[0]), int(param[1]), 3), 'uint8')
        print(ledImage[numPorts].shape)
        ledArea[numPorts] = ((int(param[5]), int(param[6])), (int(param[7]), int(param[8])))
        ledLayout[numPorts] = (int(param[5]) == 0)
        numPorts += 1
    else:
        try:
            ledSerial[numPorts] = serial.Serial(portName)
            #ser = serial.Serial(portName)
            #ledSerial[numPorts] = ser
            if (ledSerial[numPorts] == None):
                raise NullPointer
            ledSerial[numPorts].write('?')
        except serial.SerialException, msg:
            print("Serial port " + portName + " does not exist or is non-functional\n{0}".format(msg[0]))
            errorCount += 1
            return
        time.sleep(0.05)
        line = ledSerial[numPorts].readline(100)
        if (line == None):
            print("Serial port " + portName + " is not responding.")
            print("Is it really a Teensy 3.0 running VideoDisplay?")
            errorCount += 1
            return
        param = []
        param = line.rstrip().split(",")
        print(param)
        if (len(param) != 12):
            print("Error: port " + portName + " did not respond to LED config query")
            errorCount += 1
            return
        # only store the info and increase numPorts if Teensy responds properly
        ledImage[numPorts] = np.zeros((int(param[0]), int(param[1]), 3), 'uint8')
        ledArea[numPorts] = ((int(param[5]), int(param[6])), (int(param[7]), int(param[8])))
        ledLayout[numPorts] = (int(param[5]) == 0)
        numPorts += 1
        
        #ledImage[numPorts] = Image.new('RGB', Integer.parseInt(param[0]), Integer.parseInt(param[1]))
        #ledArea[numPorts] = Rect((Integer.parseInt(param[5]), Integer.parseInt(param[6])),
        #                         (Integer.parseInt(param[7]), Integer.parseInt(param[8])))
        #ledLayout[numPorts] = (Integer.parseInt(param[5]) == 0)
        #numPorts += 1


# draw runs every time the screen is redrawn - update the frame...
def draw():
    if (newImageQueue.qsize() > 0):
        imageBuff = newImageQueue.get()
        tmp = Image.new('RGB',(ledCnt, stripCnt))
        tmp.putdata(imageBuff)
        print('Display:  Got image:',tmp.size)
        #tmp.show()

        nextImage = np.array(tmp.getdata()).reshape(tmp.size[0], tmp.size[1], 3)

        frameUpdate(nextImage)

        print()


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


def main():
    print('Testing stream to serial')
    setup()
    time.sleep(1)
    for i in range(6):
        print('Display:  Attempt',i,'to draw')
        draw()
        time.sleep(0.11)

if __name__ == "__main__":
    main()




## image2data converts an image to OctoWS2811's raw data format.
## The number of vertical pixels in the image must be a multiple
## of 8.  The data array must be the proper size for the image.
#void image2data(PImage image, byte[] data, boolean layout) {
#    int offset = 3
#    int x, y, xbegin, xend, xinc, mask
#    int linesPerPin = image.height / 8
#    int pixel[] = new int[8]
#
#    for (y = 0; y < linesPerPin; y++):
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
#
#        for (x = xbegin; x != xend; x += xinc):
#            for (int i=0; i < 8; i++):
#                # fetch 8 pixels from the image, 1 for each pin
#                pixel[i] = image.pixels[x + (y + linesPerPin * i) * image.width]
#                pixel[i] = colorWiring(pixel[i])
#            # convert 8 pixels to 24 bytes
#            for (mask = 0x800000; mask != 0; mask >>= 1):
#                byte b = 0
#                for (int i=0; i < 8; i++):
#                    if ((pixel[i] & mask) != 0):
#                        b |= (1 << i)
#                data[offset++] = b


## draw runs every time the screen is redrawn - show the movie...
#void draw() {
#  # show the original video
#  image(myMovie, 0, 80)
#  
#  # then try to show what was most recently sent to the LEDs
#  # by displaying all the images for each port.
#  for (int i=0; i < numPorts; i++) {
#    # compute the intended size of the entire LED array
#    int xsize = percentageInverse(ledImage[i].width, ledArea[i].width)
#    int ysize = percentageInverse(ledImage[i].height, ledArea[i].height)
#    # computer this image's position within it
#    int xloc =  percentage(xsize, ledArea[i].x)
#    int yloc =  percentage(ysize, ledArea[i].y)
#    # show what should appear on the LEDs
#    image(ledImage[i], 240 - xsize / 2 + xloc, 10 + yloc)
#  } 
#}


## movieEvent runs for each new frame of movie data
#def movieEvent(Movie m):
#    # read the movie's next frame
#    m.read()
#    
#    #if (framerate == 0) framerate = m.getSourceFrameRate()
#    framerate = 30.0 # TODO, how to read the frame rate???
#    
#    for i in range(numPorts):
#        # copy a portion of the movie's image to the LED image
#        xoffset = percentage(m.width, ledArea[i].x)
#        yoffset = percentage(m.height, ledArea[i].y)
#        xwidth =  percentage(m.width, ledArea[i].width)
#        yheight = percentage(m.height, ledArea[i].height)
#        ledImage[i].copy(m, xoffset, yoffset, xwidth, yheight,
#                         0, 0, ledImage[i].width, ledImage[i].height)
#        # convert the LED image to raw data
#        byte[] ledData =  new byte[(ledImage[i].width * ledImage[i].height * 3) + 3]
#        image2data(ledImage[i], ledData, ledLayout[i])
#        if (i == 0):
#            ledData[0] = '*'  # first Teensy is the frame sync master
#            int usec = (int)((1000000.0 / framerate) * 0.75)
#            ledData[1] = (byte)(usec)   # request the frame sync pulse
#            ledData[2] = (byte)(usec >> 8) # at 75% of the frame time
#        else:
#            ledData[0] = '%'  # others sync to the master board
#            ledData[1] = 0
#            ledData[2] = 0
#        
#        # send the raw data to the LEDs  :-)
#        ledSerial[i].write(ledData) 

