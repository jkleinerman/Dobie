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


    def addAccess(self, ctrllerMac, access):
        '''
        Receives the controller MAC and access dictionary.
        The access dictionary has some person parameters.
        With them it creates the message to send it to controller (to add).
        It gives the created message to the network manager thread.
        '''
        
        accessJson = json.dumps(access).encode('utf8')

        msg = CUD + b'A' + b'C' + accessJson + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def updAccess(self, ctrllerMac, access):
        '''
        Receives the controller MAC and access dictionary.
        With them it creates the message to send it to controller (to update).
        It gives the created message to the network manager thread.
        '''

        accessJson = json.dumps(access).encode('utf8')

        msg = CUD + b'A' + b'U' + accessJson + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def delAccess(self, ctrllerMac, accessId):
        '''
        Receives the controller MAC and the access ID.
        With them it creates the message to send it to controller (to delete).
        It gives the created message to the network manager thread.
        '''
        accessId = str(accessId).encode('utf8')
        msg = CUD + b'A' + b'D' + b'{"id": ' + accessId + b'}' + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def addLiAccess(self, ctrllerMac, liAccess):
        '''
        Receives the controller MAC and limited access dictionary.
        The limited access dictionary has some person parameters.
        With them it creates the message to send it to controller (to add).
        It gives the created message to the network manager thread.
        '''

        liAccessJson = json.dumps(liAccess).encode('utf8')

        msg = CUD + b'L' + b'C' + liAccessJson + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def updLiAccess(self, ctrllerMac, liAccess):
        '''
        Receives the controller MAC and limited access dictionary.
        With them it creates the message to send it to controller (to update).
        It gives the created message to the network manager thread.
        '''

        liAccessJson = json.dumps(liAccess).encode('utf8')

        msg = CUD + b'L' + b'U' + liAccessJson + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)


    def delLiAccess(self, ctrllerMac, liAccessId):
        '''
        Receives the controller MAC and the limited access ID.
        With them it creates the message to send it to controller (to delete).
        It gives the created message to the network manager thread.
        '''
        liAccessId = str(liAccessId).encode('utf8')
        msg = CUD + b'L' + b'D' + b'{"id": ' + liAccessId + b'}' + END
        self.netMngr.sendToCtrller(msg, ctrllerMac)



    def updPerson(self, ctrllerMacsToUpdPrsn, person):
        '''
        Receives a list of controller MAC addresses to send the update person msg
        and a person dictionary to create the message.
        '''
        personJson = json.dumps(person).encode('utf8')

        msg = CUD + b'P' + b'U' + personJson + END

        for ctrllerMac in ctrllerMacsToUpdPrsn:
            self.netMngr.sendToCtrller(msg, ctrllerMac)



    def delPerson(self, ctrllerMacsToDelPrsn, personId):
        '''
        Receives a list of controller MAC addresses to send the delete person msg.
        With the person ID creates the message to send to the controllers
        '''
        personId = str(personId).encode('utf8')
        msg = CUD + b'P' + b'D' + b'{"id": ' + personId + b'}' + END
        
        for ctrllerMac in ctrllerMacsToDelPrsn:
            self.netMngr.sendToCtrller(msg, ctrllerMac)


