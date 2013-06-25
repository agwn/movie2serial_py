from __future__ import print_function

import wx
from PIL import Image

from Queue import Queue

from threading import Thread
import SocketServer


newImageQueue = None
nextImage = None

IMGSIZE = (60, 32)
WINSIZE = (120, 80)

def get_image():
    global newImageQueue
    global nextImage
    
    # Put your code here to return a PIL image from the camera.
    if (newImageQueue.qsize() > 0):
        #imageBuff = newImageQueue.get()
        #nextImage = Image.new('RGB',IMGSIZE)
        #nextImage.putdata(imageBuff)
        nextImage = newImageQueue.get()
        if False:
            print('Display:  Got image:',nextImage.size)
    return nextImage

def pil_to_wx(image):
    width, height = image.size
    buffer = image.convert('RGB').tostring()
    bitmap = wx.BitmapFromBuffer(width, height, buffer)
    return bitmap

class Panel(wx.Panel):
    def __init__(self, parent):
        super(Panel, self).__init__(parent, -1)
        self.SetSize(WINSIZE)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.update()
    def update(self):
        self.Refresh()
        self.Update()
        wx.CallLater(15, self.update)
    def create_bitmap(self):
        image = get_image()
        bitmap = pil_to_wx(image)
        return bitmap
    def on_paint(self, event):
        bitmap = self.create_bitmap()
        dc = wx.AutoBufferedPaintDC(self)
        xoff = (WINSIZE[0]-IMGSIZE[0])//2
        yoff = (WINSIZE[1]-IMGSIZE[1])//2
        dc.DrawBitmap(bitmap,xoff, yoff)

class Frame(wx.Frame):
    def __init__(self):
        style = wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX
        super(Frame, self).__init__(None, -1, 'Camera Viewer', style=style)
        panel = Panel(self)
        self.Fit()



class MyUDPHandler(SocketServer.BaseRequestHandler):
    '''
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    '''

    def receive(self, data):
        global newImageQueue
        
        ledCnt = IMGSIZE[0]
        stripCnt = IMGSIZE[1]
        
        packet_length = stripCnt*ledCnt*3 + 1
        
        if (len(data) != packet_length):
            print('Packet size mismatch. Expected '+str(packet_length)+', got',len(data))
            return
            
        if (data[0] == 2):
            # We got a new mode, so copy it out
            modeName = data[1:]
            return
    
        if (ord(data[0]) != 1):
            print('Packet header mismatch. Expected 1, got',ord(data[0]))
            return
    
        if (newImageQueue.qsize() > 0):
            print('Buffer full, dropping frame!')
            return
    
        tmp = Image.fromstring('RGB', (ledCnt, stripCnt), data[1:])
    
        try:
            newImageQueue.put(tmp)
        except KeyboardInterrupt, msg:
            print('Interrupted Exception caught {0}'.format(msg[1]))


    def handle(self):
        data = self.request[0]
        socket = self.request[1]
        self.receive(data)
        
def main():
    global newImageQueue
    global nextImage
    
    newImageQueue = Queue(2)
    nextImage = Image.new('L', IMGSIZE)
    
    HOST, PORT = "localhost", 58082
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    print('starting udp server')
    server_thread.start()
    print("Server loop running in thread:", server_thread.name)

    app = wx.PySimpleApp()
    frame = Frame()
    frame.Center()
    frame.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()