import re
import time
from flask import Flask
from locoHandler import Loco, LocoExportModel
from isorClient import IsorClient
from isorDataTypes import IsorRequest

class IsorDumper:
    def __init__(self, logger : Flask.logger, isorClient : IsorClient):            
        self.url_login = "https://isor.spravazeleznic.cz/Login/Login"
        self.url_request_loco = "https://isor.spravazeleznic.cz/Dotazy/D1320"
        self.url_request_train = "https://isor.spravazeleznic.cz/Dotazy/D2040"
        self.url_mainpage = "https://isor.spravazeleznic.cz/"

        ## REGEX
        self.searchRexeg = "(\d\d\d\d\d \d\d\d\d\d\d-\d  \D*[\+\-]?.*\d\d.\d\d.\d\d\d\d \d\d:\d\d)"
        self.correctRowRegex = "(\d\d\d\d [+|-]\D* \d\d.\d\d.\d\d\d\d \d\d:\d\d \d\d\d\d\d\d \d.\D*)"
        self.lastStationRegex = "(\D* )"
        self.datumRegex = "(\d\d.\d\d.\d\d\d\d \d\d:\d\d)"
        self.trainNumberRegex = "( \d\d\d\d\d\d )"
        self.postrRegex = "\d\. [\D]* HV"
        self.trainPositionsRegex = "(<pre>([\s\S]*|[\w\W]*|[\d\D]*)<\/pre>)"

        self.reservationHeadingText = "stanice zahájení     funkce               vlak   stanice cílová/odst  stanice zahájení     funkce               vlak   stanice cílová/odst"

        ## seconds between requests
        self.lastRequest_wholeTable = 0
        self.lastRequest_singleQuery = 0
        self.wholeTableRequestDelay = 1800
        self.singleQueryRequestDelay = 10

        self.isorClient = isorClient
        self._logger = logger

    def dumpSingleLocomotive(self, locomotive : Loco, timeoutByPass = False) -> LocoExportModel:

        time_diff = (time.time() - self.lastRequest_singleQuery)

        self._logger.info(f"Trying to dump single locomotive {locomotive.number}...")

        if ((time_diff > self.singleQueryRequestDelay) or timeoutByPass):

            result = self.dumpLocomotivePOST(locomotive)
            self.lastRequest_singleQuery = time.time()

            return result
        else:
            self._logger.debug(f"Request too soon: {(self.singleQueryRequestDelay - time_diff)}s remaining")
            return None

    def dumpLocomotivePOST(self, locomotive : Loco) -> LocoExportModel:        
        ## default values
        exportModel = LocoExportModel(f"{locomotive.number[:-3]}.{locomotive.number[3:]}", locomotive.fullNumber, locomotive.color)
        cutLenght = 0

        self._logger.info(f"Dumping locomotive {locomotive.number}...")

        requestBody = { 'cisloLokomotivy' : locomotive.fullNumber }

        response = self.isorClient.GetResponse(IsorRequest(self.url_request_loco, requestBody))

        ## update the last request time
        self.lastRequest = time.time()

        if response.status == 200:
            foundCurrentData = True
            ## get the respnse text
            html = response.text

            if foundCurrentData:

                self._logger.debug(f"Trying to find correctRow with regex")

                ## get the last known-position
                matches = re.findall(self.correctRowRegex, html)
                if (len(matches) == 0 or len(matches[0]) == 0):

                    self._logger.debug(f"Couldn't find correctRow for locomotive {locomotive.number}")

                    foundCurrentData = False
                else:
                    firstBestRow = matches[0].strip()
            
            if foundCurrentData:
                self._logger.debug(f"Trying to find funkceLoko with regex")

                ## get the funkceLoko
                funkceMatch = re.findall(self.postrRegex, firstBestRow)
                if (len(funkceMatch) == 0 or len(funkceMatch[0]) == 0):    
                    self._logger.debug(f"Couldn't find funkceLoko for locomotive {locomotive.number}")
                else:
                    exportModel.function = funkceMatch[0].strip()
    
            if foundCurrentData:

                self._logger.debug(f"Trying to find last station with regex")

                ## get the train position
                firstBestRow = firstBestRow[5:] ## shorten by the unused input
                positionMatch = re.findall(self.lastStationRegex, firstBestRow)
                if (len(positionMatch) == 0 or len(positionMatch[0]) == 0):

                    self._logger.debug(f"Couldn't find last station for locomotive {locomotive.number}")

                    foundCurrentData = False
                else:
                    cutLenght = len(positionMatch[0])
                    exportModel.place = positionMatch[0].strip()

            if foundCurrentData:

                self._logger.debug(f"Trying to find date with regex")

                firstBestRow = firstBestRow[cutLenght:] ## shorten by the parsed input
                dateMatch = re.findall(self.datumRegex, firstBestRow)
                if (len(dateMatch) == 0 or len(dateMatch[0]) == 0):

                    self._logger.debug(f"Couldn't find date for locomotive {locomotive.number}")
                    
                    foundCurrentData = False
                else:
                    cutLenght = len(dateMatch[0])
                    exportModel.time = dateMatch[0].strip()
            
            if foundCurrentData:

                self._logger.debug(f"Trying to find train number with regex")

                firstBestRow = firstBestRow[cutLenght:] ## shorten by the parsed input
                trainNumberMatch = re.findall(self.trainNumberRegex, firstBestRow)
                if (len(trainNumberMatch) == 0 or len(trainNumberMatch[0]) == 0):

                    self._logger.debug(f"Couldn't find train number for locomotive {locomotive.number}")

                    foundCurrentData = False
                else:
                    exportModel.trainNum = trainNumberMatch[0].strip().lstrip('0')
            
            if not foundCurrentData:

                self._logger.debug(f"Couldn't find current position for locomotive {locomotive.number}. Trying to find last known position...")

                oldPositionMatch = re.findall(self.searchRexeg, html)
                if (len(oldPositionMatch) == 0 or len(oldPositionMatch[0]) == 0):

                    self._logger.debug(f"Couldn't find last known position for locomotive {locomotive.number}.")

                    return exportModel 
                
                cutLenght = len(oldPositionMatch[0])
                oldPosition = oldPositionMatch[0].strip()

                self._logger.debug(f"Trying to find date with regex from last known position...")

                datumMatch = re.findall(self.datumRegex, oldPositionMatch[0])
                if (len(datumMatch) == 0 or len(datumMatch[0]) == 0):

                    self._logger.debug(f"Couldn't find last known position for locomotive {locomotive.number}.")

                    return exportModel
                
                cutLenght = len(datumMatch[0])
                exportModel.time = datumMatch[0].strip()

                oldPosition = oldPosition[14:-cutLenght].strip() ## remove the loconumber ("91547 380004-2") and the datum at the end

                if ' +' in oldPosition:
                    exportModel.place = f"+{oldPosition.split(' +')[1].strip()}"
                elif ' -' in oldPosition:
                    exportModel.place = f"-{oldPosition.split(' -')[1].strip()}"
                else: ## no + or - in the string
                    exportModel.place = list(filter(None, oldPosition.split("  ")))[1].strip()
            
            self._logger.debug(f"Trying to find reservations for locomotive {locomotive.number}...")

            ## check reservations
            if self.reservationHeadingText in html:

                self._logger.debug(f"Locomotive {locomotive.number} has reservations!")

                index = html.index(self.reservationHeadingText)
                html = html[index:]

                self._logger.debug(f"Trying to find train number with regex from reservations...")

                reservationTrainNum = re.findall(self.trainNumberRegex, html)
                if (len(reservationTrainNum) == 0 or len(reservationTrainNum[0]) == 0):

                    self._logger.debug(f"Couldn't find reservation train number for locomotive {locomotive.number}.")

                else:
                    ## default backup value
                    nextTrainNum = "---"

                    ## first try the first reservation
                    tempNextTrainNum = reservationTrainNum[0].strip().lstrip('0')
                    if (tempNextTrainNum != exportModel.trainNum): ## if different from the current train
                            nextTrainNum = tempNextTrainNum
                    else:
                    ## secondly try the second reservation
                        if (len(reservationTrainNum) > 1): ## if there are more reservations, usually the first is for the same train, skip it
                            tempNextTrainNum = reservationTrainNum[1].strip().lstrip('0') ## take the second reservation
                            if (tempNextTrainNum != exportModel.trainNum): ## if different from the current train
                                nextTrainNum = tempNextTrainNum

                    exportModel.trainNumReservation = nextTrainNum ## save the reservation

        ## return the result
        return exportModel
            
    def dumpLocomotivesPOST(self, locomotives : list[Loco]) -> list[LocoExportModel]:
        self._logger.debug("Dumping locomotives...")

        result = list(map(self.dumpLocomotivePOST, locomotives))

        self.lastRequest_wholeTable = time.time()

        return result

    def dumpTrainPost(self, train, timeoutByPass = False):

        self._logger.debug("Trying to dump train...")

        time_diff = (time.time() - self.lastRequest_singleQuery)

        if ((time_diff > self.singleQueryRequestDelay) or timeoutByPass):

            self._logger.info(f"Dumping train {train}...")

            requestBody = { 'cisloVlaku' : train, 'identifikace' : "", 'filtraceBodu' : "2" }

            response = self.isorClient.GetResponse(IsorRequest(self.url_request_train, requestBody))

            self.lastRequest_singleQuery = time.time()

            if response.status == 200:
                html = response.text
                matchings = re.findall(self.trainPositionsRegex, html)
                if (len(matchings) == 0 or len(matchings[0]) == 0):

                    self._logger.debug(f"Couldn't parse train detail {train}.")

                    return "Couldn't parse data"
                else:
                    return matchings[0][0]
            else:

                self._logger.debug(f"Couldn't get data for train {train}: ERROR {response.status}")
                return "Couldn't get data"
            
        else:
            self._logger.debug(f"Request too soon, {(self.singleQueryRequestDelay - time_diff)}s remaining...")
            return None