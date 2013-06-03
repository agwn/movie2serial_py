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
        self.interval = 3
        self.animationStep = 1
        #self.im = Image.new('RGB',(ledCnt, stripCnt))


    def makeDemoFrame(self):
        im = Image.new('RGB',(self.ledCnt, self.stripCnt))

        draw = ImageDraw.Draw(im)
        
        for i in range(self.ledCnt):
            #color = (0xff0000&(((i+self.animationStep)%0xff)<<16)) | (0x00ff00&(((i+self.animationStep)%0xff)<<8)) | (0x0000ff&(((i+self.animationStep)%0xff)<<0))
            #draw.line((i,0,i,im.size[1]), fill=(color))
            if ((self.animationStep%self.interval) == (i%self.interval)):
                draw.line((i,0,i,im.size[1]), fill=0xff0000)
            else:
                draw.line((i,0,i,im.size[1]), fill=0x0)
        del draw
                
        self.animationStep = self.animationStep+1
        
        return im


    def run(self):
        while (self.demoMode):
            if self.imageQueue.empty():
                im = self.makeDemoFrame()
                #print('Transmit: Queue empty. Creating new image of size:',im.size)
                if self.animationStep == self.interval+2:
                    #self.im.show()
                    self.demoMode = False
                else:
                    #print self.animationStep
                    self.imageQueue.put(im.getdata())
            time.sleep(0.1)
        print 'Transmit: Done!'
                
            
if __name__ == "__main__":
    tr = DemoTransmitter(32,60)
    tr.start()

