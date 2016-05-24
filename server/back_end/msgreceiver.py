import pymysql
import queue
import logging
import json

import genmngr
import database
from config import *
from msgheaders import *


class MsgReceiver(genmngr.GenericMngr):

    def __init__(self, exitFlag):

        #Invoking the parent class constructor, specifying the thread name, 
        #to have a understandable log file.
        super().__init__('MsgReceiver', exitFlag)

        self.dataBase = database.DataBase(DB_HOST, DB_USER, DB_PASSWD, DB_DATABASE)
    
        self.netToMsgRec = queue.Queue()





    def run(self):
        '''
        This is the main method of the thread. Most of the time it is blocked waiting 
        for queue messages coming from the "Network" thread.
        '''


        while True:
            try:
                #Blocking until Main thread sends an event or EXIT_CHECK_TIME expires 
                msg = self.netToMsgRec.get(timeout=EXIT_CHECK_TIME)
                self.checkExit()

                if msg.startswith(EVT):

                    event = msg.strip(EVT+END).decode('utf8')
                    event = json.loads(event)
                    events = [event]
                    self.dataBase.saveEvents(events)


                elif msg.startswith(EVS):

                    events = msg[1:-1].split(EVS)
                    events = [json.loads(evnt.decode('utf8')) for evnt in events]
                    self.dataBase.saveEvents(events)



            except queue.Empty:
                #Cheking if Main thread ask as to finish.
                self.checkExit()








    #def __del__(self):
   
        #self.connection.commit() 
        #self.connection.close()

