from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from locoHandler import Loco, LocoListHandler, LocoExportModel
from dumper import IsorDumper

class TableGenerator:
    def __init__(self, path : str):
        ## output.html LOCK
        self.outputDataPath = path
        self.outputLock = False
        self.templateTablePath = "templates/table.html"
        self.templateTableRowPath = "templates/tableRow.html"
        self.templateTableEmptyRowPath = "templates/emptyRow.html"
        self.templateAdditionTablePath = "templates/add.html"
        self.templateAdditionTableRowPath = "templates/addRow.html"
        self.templateRouteTable = "templates/route.html"

    class ContentModel:
        def __init__(self, locomotives : list[LocoExportModel]):
            self.hotLocomotives = [] ## those with move in the last 24h or with a reservation
            self.coldLocomotives = [] ## those with no move in the last 24h and without a reservation
            self.singleLoco = None

            self.separateLocomotives(locomotives)

        def separateLocomotives(self, locomotives : list[LocoExportModel]):
            
            ## if there is only one loco, it is the single loco
            if (len(locomotives) == 1):
                self.singleLoco = locomotives[0]
                return
            
            ## else make the separation
            currentTime = datetime.now(ZoneInfo('Europe/Berlin'))
            for loco in locomotives:
                timeDiff = currentTime.replace(tzinfo=None) - datetime.strptime(loco.time, "%d.%m.%Y %H:%M")
                timeDiffSeconds = timeDiff.total_seconds()

                if (loco.trainNumReservation != "---") or ( (timeDiffSeconds / 3600 ) <= 24 ): ## when having a reservation or a move in the last 24h
                    self.hotLocomotives.append(loco)
                else:
                    self.coldLocomotives.append(loco)

    def getIndexTableAsync(self, locomotives : list[Loco], dumper : IsorDumper):
        self.getIndexTable(dumper.dumpLocomotivesPOST(locomotives), dumper.wholeTableRequestDelay)

    def getIndexTable(self, response : list[LocoExportModel], delay : int):
        currentTime = datetime.now(ZoneInfo('Europe/Berlin')).strftime("%Y-%m-%d %H:%M:%S")
        nextUpdateTime = (datetime.now(ZoneInfo('Europe/Berlin')) + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")

        table = self.createTable(response, currentTime, nextUpdateTime)
        ## save the table to a file

        self.outputLock = True

        with open(self.outputDataPath, "w", encoding="utf-8") as file:
            file.write(table)

        self.outputLock = False

    def updateIndexTable(self, response):
        newRow = self.fillTableRow(response)
        data = ""
        with open(self.outputDataPath, "r", encoding="utf-8") as file:
            data = file.read()

        data = data.replace('<!-- [EMPTY-ROW] -->', f"{newRow}\n<!-- [EMPTY-ROW] -->\n")

        self.outputLock = True

        with open(self.outputDataPath, "w", encoding="utf-8") as file:
            file.writelines(data)

        self.outputLock = False
    
    def getSingleLocoIndexTable(self, response, delay):
        currentTime = datetime.now(ZoneInfo('Europe/Berlin')).strftime("%Y-%m-%d %H:%M:%S")
        nextUpdateTime = (datetime.now(ZoneInfo('Europe/Berlin')) + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
        table = self.createTable([response], currentTime, nextUpdateTime) ## making a list with one element to use the same function
        return table
    
    def getRouteTable(self, response, delay):
        currentTime = datetime.now(ZoneInfo('Europe/Berlin')).strftime("%Y-%m-%d %H:%M:%S")
        nextUpdateTime = (datetime.now(ZoneInfo('Europe/Berlin')) + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
        table = self.fillRouteTemplate(response, currentTime, nextUpdateTime)
        return table

    ## Creates a new table with pictures and buttons
    def createTable(self, response : list[LocoExportModel], updateTime : str, nextUpdateTime : str):
        return self.fillTable(TableGenerator.ContentModel(response), updateTime, nextUpdateTime)

    ## Fills the table with all pictures in the picture directory
    def fillTable(self, response : ContentModel, updateTime : str, nextUpdateTime : str):
        rows = ""

        ## when only single loco, create just one entry
        if (response.singleLoco is not None):
            rows += self.fillTableRow(response.singleLoco)

        ## else fill the whole table and separate hot/cold locos
        else:
            ## fill fresh locos
            for data in response.hotLocomotives:
                rows += self.fillTableRow(data)
            
            ## make spacing
            rows += self.fillEmptyTableRow()

            ## fill cold locos
            for data in response.coldLocomotives:
                rows += self.fillTableRow(data)

        template = open(self.templateTablePath, "r", encoding="utf-8").read()
        template = template.replace("[TABLE-ROWS]", rows)
        template = template.replace("[TABLE-LAST-UPDATE]", updateTime)
        template = template.replace("[TABLE-NEXT-UPDATE]", nextUpdateTime)
        return template

    ## Fills a table row with the picture and buttons
    def fillTableRow(self, data : LocoExportModel):
        template = open(self.templateTableRowPath, "r", encoding="utf-8").read()
        template = template.replace("[LOCO_ID]", data.id)
        template = template.replace("[LOCO_FULL_ID]", data.fullId)

        if (data.color is not None): ## color can be None when the loco is not in the list
            template = template.replace("[LOCO_COLOR]", data.color)

        template = template.replace("[LOCO_FUNCTION]", data.function)
        template = template.replace("[LOCO_TRAIN_NUM]", data.trainNum)
        template = template.replace("[LOCO_TRAIN_NUM_RESERVATION]", data.trainNumReservation)
        template = template.replace("[LOCO_POSITION]", data.place)
        template = template.replace("[LOCO_TIME]", data.time)
        return template
    
    def fillEmptyTableRow(self):
        template = open(self.templateTableEmptyRowPath, "r", encoding="utf-8").read()
        return template

    def createAdditionTable(self, data : LocoListHandler):
        return self.fillAdditionTable(data)
    
    def fillAdditionTable(self, data : LocoListHandler):
        rows = ""
        for loco in data.locoList:
            rows += self.fillAdditionTableRow(loco)
        template = open(self.templateAdditionTablePath, "r", encoding="utf-8").read()
        template = template.replace("[TABLE-ROWS]", rows)
        return template
    
    def fillAdditionTableRow(self, data : Loco):
        template = open(self.templateAdditionTableRowPath, "r", encoding="utf-8").read()
        template = template.replace("[LOCO-ID]", data.fullNumber)
        template = template.replace("[LOCO-NOTE]", data.note)
        template = template.replace("[LOCO-EDITOR-NAME]", data.editor)
        return template
    
    def fillRouteTemplate(self, data, updateTime, nextRequestTime):
        template = open(self.templateRouteTable, "r", encoding="utf-8").read()
        template = template.replace("[ROUTE-LAST-UPDATE]", updateTime)
        template = template.replace("[ROUTE-NEXT-UPDATE]", nextRequestTime)
        template = template.replace("[ROUTE-CONTENT]", data)
        return template