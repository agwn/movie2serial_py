import threading
from PIL import Image, ImageDraw
import time

class DemoTransmitter(threading.Thread):

    def __init__(self, stripCnt, ledCnt):
        threading.Thread.__init__(self)
        self._stop = threading.Event()

        self.demoMode = True
        self.animationStep = 0
        self.ledCnt = ledCnt
        self.stripCnt = stripCnt
        self.interval = 10
        self.im = Image.new('RGB',(ledCnt,stripCnt))


    def makeDemoFrame(self):
        self.im = Image.new('RGB',(self.ledCnt,self.stripCnt))

        draw = ImageDraw.Draw(self.im)
        
        for i in range(self.ledCnt):
            if self.animationStep == i%self.interval:
                draw.line((i,0,i,self.im.size[1]), fill=0xff0000)
            else:
                draw.line((i,0,i,self.im.size[1]), fill=0x0)
        del draw
                
        self.animationStep = (self.animationStep+1)%self.interval
        
        return self.im


    def run(self):
        while (self.demoMode):
            self.makeDemoFrame()
            if self.animationStep == 5:
                #self.im.show()
                self.demoMode = False
            else:
                print self.animationStep
                time.sleep(1)
        print 'Done!'
                
            
if __name__ == "__main__":
    tr = DemoTransmitter(32,60)
    tr.start()
