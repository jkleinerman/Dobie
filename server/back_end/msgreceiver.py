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
    put the message in "toMsgRec" queue. This thread get the message
    from the queue and do the necessary operation with DB. In this way
    the network thread do not lose time doing things in DB.
    '''

    def __init__(self, exitFlag, toCrudReSndr, toRtEvent):

        #Invoking the parent class constructor, specifying the thread name,
        #to have a understandable log file.
        super().__init__('MsgReceiver', exitFlag)


        #The creation of this object was moved to the run method to avoid
        #freezing the main thread when there is no connection to database.
        self.dataBase = None

        #Commit handlers were moved to the run method since the dataBase
        #object and its method doesn't exist yet.
        self.commitHndlrs = None

        #The ctrllerMsger is used to send to the controllers the message
        #to delete the visitors when they pass trough exit doors
        #The object is set in the main thread
        self.ctrllerMsger = None

        #This queue will be used to tell the Crud Resender Thread that the
        #the controller is ready to receive all the data when it is re-provisioned
        self.toCrudReSndr = toCrudReSndr

        self.toRtEvent = toRtEvent

        self.toMsgRec = queue.Queue()





    def run(self):
        '''
        This is the main method of the thread. Most of the time it is blocked waiting
        for queue messages coming from the "Network" thread.
        '''

        #First of all, the database should be connected by the execution of this thread
        self.dataBase = database.DataBase(DB_HOST, DB_USER, DB_PASSWD, DB_DATABASE, self)
        #Now we can set the commit handlers.
        self.commitHndlrs = {'S': self.dataBase.commitDoor,
                             'U': self.dataBase.commitUnlkDoorSkd,
                             'E': self.dataBase.commitExcDayUds,
                             'A': self.dataBase.commitAccess,
                             'L': self.dataBase.commitLiAccess,
                             'P': self.dataBase.commitPerson
                            }

        while True:
            try:
                #Blocking until Network thread sends an msg or EXIT_CHECK_TIME expires
                msg = self.toMsgRec.get(timeout=EXIT_CHECK_TIME)
                self.checkExit()

                #When the controller sends an Event
                if msg.startswith(EVT):

                    event = msg.strip(EVT+END).decode('utf8')
                    event = json.loads(event)

                    #The events coming from the controller have the card number instead of
                    #the person id because the person trying to pass a door controlled by this controller,
                    #couldn't be in this controller (no access in any of the doors controlled by it) but
                    #the person could be in the central data base. In this situation it is desirable to
                    #show the involved person in the event, also when they are denyied.
                    #cardNum2PrsnId() function is used to put the person id in the event dictionary and
                    #remove the card number.
                    try:
                        self.dataBase.cardNum2PrsnId(event)
                    except database.EventError:
                        self.logger.warning("Error converting cardNumber to personId. Ignoring this event.")
                        continue

                    try:
                        #Before sending the event to the events-live.js application,
                        #it should be formatted adding some fields. This is done
                        #using "getFmtEvent" function from database.
                        fmtEvent = self.dataBase.getFmtEvent(event)
                        self.toRtEvent.put(fmtEvent)
                    except database.EventError as eventError:
                        self.logger.warning("Error trying to format event.")
                        self.logger.debug(eventError)

                    if self.dataBase.isValidVisitExit(event):
                        personId = event['personId']
                        logMsg = "Visitor exiting. Removing from system person with ID = {}".format(personId)
                        self.logger.info(logMsg)
                        ctrllerMacsToDelPrsn = self.dataBase.markPerson(personId, database.TO_DELETE)
                        self.ctrllerMsger.delPerson(ctrllerMacsToDelPrsn, personId)

                    events = [event]
                    self.dataBase.saveEvents(events)

                #When the controller sends many Events (Retransmitting)
                elif msg.startswith(EVS):

                    events = msg[1:-1].split(EVS)
                    events = [json.loads(evnt.decode('utf8')) for evnt in events]

                    for event in events:
                        try:
                            self.dataBase.cardNum2PrsnId(event)
                        except database.EventError:
                            self.logger.warning("Error converting cardNumber to personId. Ignoring this event.")
                            continue

                        if self.dataBase.isValidVisitExit(event):
                            personId = event['personId']
                            logMsg = "Visitor exiting. Removing from system person with ID = {}".format(personId)
                            self.logger.info(logMsg)
                            ctrllerMacsToDelPrsn = self.dataBase.markPerson(personId, database.TO_DELETE)
                            self.ctrllerMsger.delPerson(ctrllerMacsToDelPrsn, personId)
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

                #When the controller sends a Keep Alive message
                elif msg.startswith(KAL):
                    ctrllerMac = msg.strip(KAL+END).decode('utf8')
                    self.logger.debug('Receiving Keep Alive message from: {}.'.format(ctrllerMac))
                    try:
                        revivedCtrller = self.dataBase.setCtrllerReachable(ctrllerMac)
                        #If the controller wasn't alive previously, "revivedCtrller" will not be None,
                        #and a JSON will be sent to "rtevent" thread.
                        if revivedCtrller:
                            self.toRtEvent.put(revivedCtrller)
                    except database.ControllerError:
                        self.logger.error("Controller: {} can't be set alive.".format(ctrllerMac))


                #When the controller sends a response to Request Re Provisioning message
                elif msg.startswith(RRRP):
                    ctrllerMac = msg.strip(RRRP+END).decode('utf8')
                    self.logger.debug(f'Receiving Response to Request re-provisioning message from: {ctrllerMac}.')
                    try:
                        #Since the controller answered with RRRP, we are sure that it
                        #cleared its DB. The following line, sets all the CRUDs of this
                        #controller to state: TO_ADD in the server DB.
                        self.dataBase.reProvController(ctrllerMac)
                        #Now, the MAC of this controller is sent to CrudReSndr Thread
                        #to tell him to re-provision this controller
                        self.toCrudReSndr.put(ctrllerMac)
                    except (database.ControllerError, database.ControllerNotFound) as reProvError:
                        self.logger.debug(reProvError)
                        self.logger.error(f'Error re-provisioning controller: {ctrllerMac}')

            except queue.Empty:
                #Cheking if Main thread ask us to finish.
                self.checkExit()
