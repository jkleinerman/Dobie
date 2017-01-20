#!/usr/bin/env python3


import logging
import logging.handlers

import threading
import subprocess


import passage
import database
from config import *





class IoIface(object):

    def __init__(self, dataBase):

        #Getting the logger
        self.logger = logging.getLogger('Controller')

        #IoIface Proccess
        self.ioIfaceProc = None
        
        self.dataBase = dataBase


    #---------------------------------------------------------------------------#

    def start(self):
        '''
        Start the IO Interface process.
        Leave self.ioIfaceProc and self.pssgsControl with new objects.
        '''

        #In the followng section we generate the arguments to pass to the ioIface external program
        ioIfaceArgs = ''

        
        pssgsPinoutParams = self.dataBase.getPssgsPinoutParams()

        for pinoutId in pssgsPinoutParams:

            for pssgPinoutParamName in self.dataBase.getPssgPinoutParamsNames():
                #Since not all the columns names of Passage table are parameters of 
                #ioiface binary, they should be checked if they are in the IOFACE_ARGS list
                if pssgPinoutParamName in IOIFACE_ARGS:
                    pssgPinoutParamValue = pssgsPinoutParams[pinoutId][pssgPinoutParamName]
                    if pssgPinoutParamValue:
                        ioIfaceArgs += '--{} {} '.format(pssgPinoutParamName, pssgPinoutParamValue)



        #With the arguments to pass to the ioIface program, it is lauched using Popen
        #and saving the process object to be able to kill it when a passage is added, updated
        #or deleted.
        ioIfaceCmd = '{} {}'.format(IOIFACE_BIN, ioIfaceArgs)

        logMsg = 'Starting IO Interface with the following command: {}'.format(ioIfaceCmd)
        self.logger.info(logMsg)

        self.ioIfaceProc = subprocess.Popen(ioIfaceCmd, shell=True, 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.STDOUT
                                           )



    #---------------------------------------------------------------------------#

    def stop(self):
        '''
        This method is called by crud thread when a passage is added, updated or
        deleted.
        It set self.pssgsReconfFlag to tell all the "cleanerPssgMngr" or "starterAlrmMngr"
        threads to finish when they are running
        '''

        if self.ioIfaceProc:
            self.logger.info('Stoping IO Interface.')
            #Ask ioIface external program to finish (sending SIGTERM signal)
            self.ioIfaceProc.terminate()
            #Wait until it finish (It does not finish instantly). If we do not
            #wait, we end launching "ioIface" before the previous finish and a mess happen
            self.ioIfaceProc.wait()
        else:
            self.logger.info('IO Interface not running. Nothing to stop.')




    #----------------------------------------------------------------------------#

    def restart(self):
        '''
        This method call stop and start secuentially
        '''
        self.stop()
        self.start()
