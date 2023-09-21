import json
from datetime import datetime
from flask import Flask
from dataclasses import dataclass

@dataclass
class Loco:
    def __init__(self, shortNumber, fullNumber, note , editor, color = ""):
        self.number = shortNumber
        self.note = note
        self.editor = editor
        self.fullNumber = fullNumber
        self.color = color

class LocoExportModel:
    def __init__(self, id, fullId, color, function="", trainNum="---", trainNumReservation="---", place="", time=""):
        self.id = id
        self.fullId = fullId
        self.color = color
        self.function = function
        self.trainNum = trainNum
        self.trainNumReservation = trainNumReservation
        self.place = place
        self.time = time

class LocoListHandler:
    def __init__(self, path : str, colorPath : str, logger : Flask.logger = None):
        self._logger = logger
        self.dataConfigPath = path
        self.locoList : list[Loco] = self.deserialize()
        self.colorList = self.deserializeColors(colorPath)
        
    def serialize(self):
        self._logger.info("Sorting and serializing the loco list...")

        self.locoList.sort(key=lambda x: x.number)

        with open(self.dataConfigPath, "w", encoding='utf-8') as file:
            for loco in self.locoList:
                file.write(f"{loco.number};{loco.fullNumber};{loco.note};{loco.editor};{loco.color}\n")
        return

    def deserialize(self):
        self._logger.info("Deserializing the loco list...")
        with open(self.dataConfigPath, "r", encoding='utf-8') as file:
            data = file.readlines()
            locoList = []
            for line in data:
                line = line.split(";")
                if len(line) == 5:
                    locoList.append(Loco(line[0], line[1], line[2], line[3], line[4].strip()))
            return locoList
        
    def deserializeColors(self, path : str):
        self._logger.info("Deserializing the colors...")
        file = open(path, "rb")
        data = json.load(file)
        file.close()
        return data
    
    def getColor(self, loco : str):
        self._logger.info(f"Trying to find color for locomotive {loco}...")
        ## expecting that the loco is "749121" format
        for color in self.colorList.keys():
            if loco in self.colorList[color]:
                return color
        return None

    def addLoco(self, number : str, note : str, editor : str) -> Loco:
        self._logger.info(f"Trying to find .css color and adding locomotive {number}...")
        shortNum = self.parseFullLocoNumber(number)
        color = self.getColor(shortNum)
        loco = None
        
        ## check for duplicates
        for loco in self.locoList:
            if loco.fullNumber == number:
                self._logger.warning(f"Locomotive {number} already exists, updating...")
                loco.note = note
                loco.editor = editor

                if (color is not None):
                    loco.color = color

                self.serialize()
                return loco

        if (color is not None):
            self._logger.debug(f"Locomotive {number} has color: {color}...")
            loco = Loco(shortNum, number, note, editor, color)
            self.locoList.append(loco)
        else:
            loco = Loco(shortNum, number, note, editor)
            self.locoList.append(loco)

        self.serialize()
        return loco
    
    def addLocoTemp(self, number : str) -> Loco:
        self._logger.info(f"Trying to find .css color and locomotive {number}...")
        shortNum = self.parseFullLocoNumber(number)
        color = self.getColor(shortNum)
        loco = Loco(shortNum, number, "", "", color)
        return loco
    
    def removeLoco(self, loco : Loco):
        self._logger.info(f"Removing locomotive {loco.number}...")
        self.locoList = [x for x in self.locoList if x.fullNumber != loco.fullNumber]
        self.serialize()
        return
    
    def getLoco(self, number : str):
        for loco in self.locoList:
            if loco.number == number:
                return loco
            
        return self.addLocoTemp(number)
    
    def parseFullLocoNumber(self, fullNumber : str):
        self._logger.info(f"Parsing full number {fullNumber}...")
        ## expecting that the loco is "749121" format
        if (len(fullNumber) == 6):
            return fullNumber
        elif (len(fullNumber) == 7):
            return fullNumber[:-1]
        else:
            return fullNumber[5:-1]
        
    def checkLokoInput(self, LocoNum):
        if LocoNum == "":
            return False
        if LocoNum[0] == "0":
            return False
        if len(LocoNum) != 6 and len(LocoNum) != 7 and len(LocoNum) != 12:
            return False
        if not LocoNum.isdigit():
            return False
        return True