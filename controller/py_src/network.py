import threading
import logging
import datetime
import time
import os

import select
import socket
import json

import database
import queue

from config import *

import sys





int_EVT  = 0x01
int_REVT = 0x02
int_EVS  = 0x03
int_REVS = 0x04
int_CUD  = 0x05
int_RCUD = 0x06
int_END  = 0x1F


EVT  = bytes([int_EVT])
REVT = bytes([int_REVT])
EVS  = bytes([int_EVS])
REVS = bytes([int_REVS])
CUD  = bytes([int_CUD])
RCUD = bytes([int_RCUD])
END  = bytes([int_END])


#EVT  = b'#'
#REVT = b'$'
#CUD  = b'%'
#RCUD = b'&'
#END  = b'.\n'


class Unblocker(object):
    
    def __init__(self):
        self.readPipe, self.writePipe = os.pipe()

    def getFd(self):
        return self.readPipe

    def unblock(self):
        os.write(self.writePipe, b'0')

    def receive(self):
        os.read(self.readPipe, 10)

    



class NetMngr(threading.Thread):

    '''
    This thread receives the events from the main thread, tries to send them to the server.
    When it doesn't receive confirmation from the server, it stores them in database.
    '''
    def __init__(self, netToEvent, netToReSnd, exitFlag):


        #Invoking the parent class constructor, specifying the thread name, 
        #to have a understandable log file.
        super().__init__(name = 'NetMngr', daemon = True)

        #Buffer to receive bytes from server
        self.inBuffer = b''
        #Buffer to send bytes to server
        self.outBuffer = b''


        #Queue to send responses to Event Thread
        self.netToEvent = netToEvent

        #Queue to send responses to ReSender Thread
        self.netToReSnd = netToReSnd


        #Queue used to send events from event thread to network thread
        self.outBufferQue = queue.Queue()

        #Lock to protect access to above dictionary 
        self.lockNetPoller = threading.Lock()

        #Poll Network Object
        self.netPoller = select.poll()

        #Pipe to wake up the thread blocked in poll() call
        #self.readPipe, self.writePipe = os.pipe()

        self.unblocker = Unblocker()
        self.unBlkrFd = self.unblocker.getFd()

        #Registering above pipe in netPoller object
        self.netPoller.register(self.unBlkrFd)

        #Socket server
        self.srvSock = None

        #Registering the socket in the network poller object
#        self.netPoller = None
 
        #Flag to know when the Main thread ask as to finish
        self.exitFlag = exitFlag

        #Thread exit code
        self.exitCode = 0

        #Getting the logger
        self.logger = logging.getLogger('Controller')

        self.connected = False



    def checkExit(self):
        '''
        Check if the main thread ask this thread to exit using exitFlag
        If true, call sys.exit and finish this thread
        '''
        if self.exitFlag.is_set():
            self.logger.info('Network thread exiting.')
            sys.exit(self.exitCode) 



    def sendEvent(self, event):
        '''
        '''

        if self.connected:

            jsonEvent = json.dumps(event).encode('utf8')
            outMsg = EVT + jsonEvent + END
            #Writing the msgs in a queue because we can not assure the method sendEvent
            #will not be called again before the poll() wake up to send the bytes
            self.outBufferQue.put(outMsg)
            with self.lockNetPoller:
                try:
                    self.netPoller.modify(self.srvSock, select.POLLOUT)
                    self.unblocker.unblock()
                except FileNotFoundError:
                    self.logger.debug('The socket was closed and POLLNVALL was not captured yet.')
            
        else:
            print('Raising exception')



    def reSendEvents(self, eventList):
        '''
        '''

        if self.connected:

            outMsg = b''
            for event in eventList:
                jsonEvent = json.dumps(event).encode('utf8')
                outMsg += EVS + jsonEvent
            outMsg += END

            self.outBufferQue.put(outMsg)
            with self.lockNetPoller:
                try:
                    self.netPoller.modify(self.srvSock, select.POLLOUT)
                    self.unblocker.unblock()
                except FileNotFoundError:
                    self.logger.debug('The socket was closed and POLLNVALL was not captured yet.')

        else:
            print('Raising exception')




    def procRecMsg(self, msg):
        '''
        Analyzes the messages received from the server. If a reply
        '''
        #Event response
        if msg.startswith(REVT):
            response = msg.strip(REVT+END)
            response = response.decode('utf8')
            self.netToEvent.put(response)

        elif msg.startswith(REVS):
            response = msg.strip(REVS+END)
            response = response.decode('utf8')
            self.netToReSnd.put(response)
        



    def run(self):
        '''
        This is the main method of the thread. Most of the time it is blocked waiting 
        for queue messages coming from the "Main" thread.
        '''

        while True:

            try:
                #Connecting to server
                self.srvSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.srvSock.connect((SERVER_IP, SERVER_PORT))
                #Registering the socket in the network poller object
                self.netPoller.register(self.srvSock, select.POLLIN)
                self.connected = True
                self.logger.info('Connected to server. IP: {}, PORT: {}'.format(SERVER_IP, SERVER_PORT))

                while self.connected:

                    for fd, pollEvnt in self.netPoller.poll(NET_POLL_MSEC):


                        if fd == self.unBlkrFd:
                            self.unblocker.receive()
                            continue

                        if pollEvnt & select.POLLIN:
                            moreData = self.srvSock.recv(REC_BYTES)
                            self.logger.debug('Receiving: {}'.format(moreData))
                            if not moreData:         # end-of-file
                                self.srvSock.close() # next poll() will POLLNVAL, and thus clean up
                                continue                # Continue to the next pollEvnt if any
                            msg = self.inBuffer + moreData
                            if msg.endswith(END):
                                self.procRecMsg(msg)
                            else:
                                self.inBuffer = msg



                        elif pollEvnt & select.POLLOUT:
                            try:
                                while True:
                                    outBuffer = self.outBufferQue.get(block = False)
                                    self.logger.debug('Sending: {}'.format(outBuffer))
                                    self.srvSock.sendall(outBuffer)
                            except queue.Empty:
                                pass #No more data to send in queue
                            #No se bien por que tengo que hacer esto pero sino lo hago
                            #la proxima llamada a netPoller.poll se bloquea por siempre
                            with self.lockNetPoller:
                                self.netPoller.modify(self.srvSock, select.POLLIN)



                        elif pollEvnt & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                            self.logger.info('The connection with server was broken.')
                            with self.lockNetPoller:
                                self.netPoller.unregister(fd)
                                #self.netPoller = None
                            #self.srvSock = None
                            self.connected = False

                    #Cheking if Main thread ask as to finish.
                    self.checkExit()





            except (ConnectionRefusedError, ConnectionResetError):
                #Cheking if Main thread ask as to finish.
                self.checkExit()
                self.logger.info('Reconnecting to server in {} seconds..'.format(RECONNECT_TIME))
                time.sleep(RECONNECT_TIME)

    
