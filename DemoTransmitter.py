import threading
from PIL import Image, ImageDraw
import time

class DemoTransmitter(threading.Thread):

    def __init__(self, ledCnt, stripCnt, queue):
        threading.Thread.__init__(self)
        self._stop = threading.Event()

        self.demoMode = True
        self.stripCnt = stripCnt
        self.ledCnt = ledCnt
        self.imageQueue = queue
        self.interval = 6
        self.animationStep = 0
        #self.im = Image.new('RGB',(ledCnt, stripCnt))


    def makeDemoFrame(self):
        im = Image.new('RGB',(self.ledCnt, self.stripCnt))

        for i in range(im.size[0]):
            if ((i%self.interval) == (self.animationStep%self.interval)):
            #if (0 == (i%self.interval)):
                for j in range(im.size[1]):
                    im.putpixel((i,j),0xFF0000)

        self.animationStep = self.animationStep+1
        
        #im.show()
        return im


    def run(self):
        while (self.demoMode):
            if self.imageQueue.empty():
                if self.animationStep == 9:
                    self.demoMode = False
                else:
                    im = self.makeDemoFrame()
                    print('Transmit: Queue empty. Creating new image of size:',im.size)
                    self.imageQueue.put(im.getdata())
            time.sleep(0.45)
        print 'Transmit: Done!'
                
            
if __name__ == "__main__":
    tr = DemoTransmitter(32,60)
    tr.start()

