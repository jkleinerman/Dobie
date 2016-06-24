import logging

import socket
import json


from network import *
from config import *





class CtrllerMsger(object):

    '''
    This class is responsible of create the message to be sent to the controller
    '''
    def __init__(self, netMngr):
        '''
        Receive the netMngr to be able to call sendToCtrller method
        of this object
        '''
        self.netMngr = netMngr



    def addPassage(self, ctrllerMac, passage):
        '''
        Receives the controller MAC and a dictionary with passage parameters.
        With them it creates the message to send it to controller (to add)
        It gives the created message to the network manager thread.
        '''
        passageJson = json.dumps(passage).encode('utf8')
        msg = CUD + b'S' + b'C' + passageJson + END 
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def updPassage(self, ctrllerMac, passage):
        '''
        Receives the controller MAC and a dictionary with passage parameters.
        With them it creates the message to send it to controller (to update).
        It gives the created message to the network manager thread.        
        '''
        passageJson = json.dumps(passage).encode('utf8')
        msg = CUD + b'S' + b'U' + passageJson + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)



    def delPassage(self, ctrllerMac, passageId):
        '''
        Receives the controller MAC and the passage ID.
        With them it creates the message to send it to controller (to delete).
        It gives the created message to the network manager thread.        
        '''
        passageId = str(passageId).encode('utf8')
        msg = CUD + b'S' + b'D' + b'{"id": ' + passageId + b'}' + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def addAccess(self, ctrllerMac, person, access):
        print(ctrllerMac, person, access)

