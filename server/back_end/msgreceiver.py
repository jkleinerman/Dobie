import pymysql
import queue
import logging
import json
import re

import genmngr
import database
from config import *
from msgheaders import *


class MsgReceiver(genmngr.GenericMngr):
    '''
    This thread is created by the main thread.
    When the network thread receives a message from the controller, it 
    put the message in "netToMsgRec" queue. This thread get the message
    from the queue and do the necessary operation with DB. In this way
    the network thread do not lose time doing things in DB.
    '''

    def __init__(self, exitFlag):

        #Invoking the parent class constructor, specifying the thread name, 
        #to have a understandable log file.
        super().__init__('MsgReceiver', exitFlag)

        self.dataBase = None

#        self.commitHndlrs = {'S': self.dataBase.commitDoor,
#                             'A': self.dataBase.commitAccess,
#                             'L': self.dataBase.commitLiAccess,
#                             'P': self.dataBase.commitPerson
#                            }
    
        self.netToMsgRec = queue.Queue()





    def run(self):
        '''
        This is the main method of the thread. Most of the time it is blocked waiting 
        for queue messages coming from the "Network" thread.
        '''

        self.dataBase = database.DataBase(DB_HOST, DB_USER, DB_PASSWD, DB_DATABASE, self)

        self.commitHndlrs = {'S': self.dataBase.commitDoor,
                             'A': self.dataBase.commitAccess,
                             'L': self.dataBase.commitLiAccess,
                             'P': self.dataBase.commitPerson
                            }



        while True:
            try:
                #Blocking until Network thread sends an msg or EXIT_CHECK_TIME expires 
                msg = self.netToMsgRec.get(timeout=EXIT_CHECK_TIME)
                self.checkExit()

                #When the controller sends an Event
                if msg.startswith(EVT):

                    event = msg.strip(EVT+END).decode('utf8')
                    event = json.loads(event)
                    events = [event]
                    self.dataBase.saveEvents(events)

                #When the controller sends many Events (Retransmitting)
                elif msg.startswith(EVS):

                    events = msg[1:-1].split(EVS)
                    events = [json.loads(evnt.decode('utf8')) for evnt in events]
                    self.dataBase.saveEvents(events)


                #When the controller sends a response to CRUD message
                elif msg.startswith(RCUD):
                    
                    crudResponse = msg.strip(RCUD+END).decode('utf8')
                    crudId = re.search('"id":\s*(\d*)', crudResponse).groups()[0]
                    crudTypeResp = crudResponse[0]

                    #When a response from an update or delete person is received, it is
                    #necessary to pass to commitPerson method the controller MAC.
                    #The rest of commit methods just need the crudId.
                    if crudTypeResp == 'P':
                        ctrllerMac = re.search('"mac":\s*(\w{12})', crudResponse).groups()[0]
                        self.dataBase.commitPerson(crudId, ctrllerMac)
                    else:
                        self.commitHndlrs[crudTypeResp](crudId)


            except queue.Empty:
                #Cheking if Main thread ask as to finish.
                self.checkExit()




