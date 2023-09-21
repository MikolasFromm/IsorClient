import os
import time
import threading
import shutil
from flask import Flask, request, url_for, redirect, send_from_directory
from flask_basicauth import BasicAuth
from tableGenerator import TableGenerator
from locoHandler import LocoListHandler
from dumper import IsorDumper
from isorClient import IsorClient

app = Flask(__name__)  

basic_auth = BasicAuth(app)

# local environment variables
os.environ['ISOR_USERNAME'] = "username"
os.environ['ISOR_PASSWORD'] = "password"
os.environ['ISOR_DATA_CONFIG_PATH'] = "data/locoList.csv"
os.environ['ISOR_DATA_OUTPUT_PATH'] = "templates/output.html"
os.environ['ISOR_DATA_COLORS_PATH'] = "data/lokomotivy.json"
os.environ['ISOR_DATA_LAKY_CSS_PATH'] = "data/laky.css"
os.environ['ISOR_BASIC_AUTH_USERNAME'] = 'clientUsername'
os.environ['ISOR_BASIC_AUTH_PASSWORD'] = 'clientPassword'
dataLakyMigrateToPath = "static/laky.css"

## Azure WebAPP environment variables
username = os.environ['ISOR_USERNAME']
password = os.environ['ISOR_PASSWORD']
dataConfigPath = os.environ['ISOR_DATA_CONFIG_PATH']
dataOutputPath = os.environ['ISOR_DATA_OUTPUT_PATH']
dataColorsPath = os.environ['ISOR_DATA_COLORS_PATH']
dataLakyMigrateFromPath = os.environ['ISOR_DATA_LAKY_CSS_PATH']
dataLakyMigrateToPath = "static/laky.css"
app.config['BASIC_AUTH_USERNAME'] = os.environ['ISOR_BASIC_AUTH_USERNAME']
app.config['BASIC_AUTH_PASSWORD'] = os.environ['ISOR_BASIC_AUTH_PASSWORD']

app.logger.setLevel("INFO")
app.logger.info("Starting the app...")

app.logger.info("Migrating the laky.css file...")
if (os.path.exists(dataLakyMigrateFromPath)):
    shutil.copyfile(dataLakyMigrateFromPath, dataLakyMigrateToPath)

app.logger.info("Creating the IsorClient, IsorDumper, TableGenerator and LocoListHandler...")
isorClient = IsorClient(app.logger, username, password)
isorDumper = IsorDumper(app.logger, isorClient)
tableGenerator = TableGenerator(dataOutputPath)
locoHandler = LocoListHandler(dataConfigPath, dataColorsPath, app.logger)

app.logger.info("Starting the IsorClient request handler...")
threading.Thread(target=isorClient.RequestHandler).start()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':

        app.logger.info("[GET] Loading the index page...")

        timeWaitingForLock = time.time()
        while tableGenerator.outputLock and time.time() - timeWaitingForLock < 10:
            time.sleep(0.1)

        if time.time() - timeWaitingForLock >= 10:
            app.logger.debug("Timeout while waiting for the index page to be written")
            raise Exception("Timeout while waiting for the index page to be written")

        html = open(dataOutputPath, "r", encoding="utf-8").read()

        app.logger.debug("Index page read")

        return html
    
    elif request.method == 'POST':

        app.logger.info("[POST] from the index page...")

        ## requesting refresh
        if request.form.get('start_dump') != None:

            app.logger.debug(f"Deserializing the locomotive list...")

            locoHandler.deserialize()

            app.logger.debug(f"Locomotive list deserialized")
            app.logger.debug(f"Updating the index table...")

            updateData(locoHandler.locoList)

            app.logger.debug(f"Index table updated")

            return redirect(url_for('list_redirect'))
    
        ## requesting new single locomotive
        elif request.form.get('get_single_loco_button') != None:
                
                app.logger.debug(f"Obtainig the locomotive number...")
    
                locoNum = request.form['loco_number_single']
    
                app.logger.info(f"Checking the locomotive number {locoNum}...")
    
                if not locoHandler.checkLokoInput(locoNum):
                    return "Zadejte číslo vlaky v jednom z následujících formátů: '749121' nebo '7491210' nebo '925427491210'"
    
                app.logger.debug(f"Redirecting to the locomotive page...")
    
                return redirect(url_for("get", loco_id=locoNum))
        
        ## requesting new single train
        elif request.form.get('get_single_train_button') != None:

                app.logger.debug(f"Obtainig the train number...")
    
                trainNum = request.form['train_number_single']
    
                app.logger.info(f"Checking the train number {trainNum}...")
    
                app.logger.debug(f"Redirecting to the locomotive page...")
    
                return redirect(url_for("getTrain", train_id=trainNum))


@app.route('/get/loco/<loco_id>', methods=['GET', 'POST'])
@basic_auth.required
def get(loco_id):
    app.logger.info(f"Obtaining locomotive {loco_id}...")

    if not locoHandler.checkLokoInput(loco_id):
        return "Zadejte číslo vlaky v jednom z následujících formátů: '749121' nebo '7491210' nebo '925427491210'"
    
    ## parse the loco number

    loco_id = loco_id.replace('.', '') ## deprecated

    loco = locoHandler.getLoco(loco_id)

    if loco is None:

        app.logger.debug(f"Locomotive {loco_id} not found")

        return "No such locomotive"
    
    app.logger.debug(f"Locomotive {loco_id} found")
    
    ## when freshly loading
    if request.method == 'GET':

        app.logger.info(f"[GET] Loading locomotive {loco_id}...")

        res = isorDumper.dumpSingleLocomotive(loco)

        app.logger.debug(f"Locomotive {loco_id} dumped")

        if res is not None:

            app.logger.debug(f"Generating the table for locomotive {loco_id}...")

            return tableGenerator.getSingleLocoIndexTable(res, isorDumper.singleQueryRequestDelay)
        else:     
            
            app.logger.debug(f"Too many requests, remaining: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds")

            return f"Too many requests, try again after: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds"
    
    ## when clicking refresh button
    elif request.method == 'POST':

        ## requesting refresh
        if (request.form.get('start_dump') != None):

            app.logger.info(f"[POST] Loading locomotive {loco_id}...")

            res = isorDumper.dumpSingleLocomotive(loco)

            app.logger.debug(f"Locomotive {loco_id} dumped")

            if res is not None:

                app.logger.debug(f"Generating the table for locomotive {loco_id}...")

                return tableGenerator.getSingleLocoIndexTable(res, isorDumper.singleQueryRequestDelay)
            else:     

                app.logger.debug(f"Too many requests, remaining: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds")
                
                return f"Too many requests, try again after: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds"        

        ## requesting new single locomotive  
        elif request.form.get('get_single_loco_button') != None:
        
            app.logger.debug(f"Obtainig the locomotive number...")

            locoNum = request.form['loco_number_single']

            app.logger.info(f"Checking the locomotive number {locoNum}...")

            if not locoHandler.checkLokoInput(locoNum):
                return "Zadejte číslo vlaky v jednom z následujících formátů: '749121' nebo '7491210' nebo '925427491210'"

            app.logger.debug(f"Redirecting to the locomotive page...")

            return redirect(url_for("get", loco_id=locoNum))
        
        ## requesting new single train
        elif request.form.get('get_single_train_button') != None:

                app.logger.debug(f"Obtainig the train number...")
    
                trainNum = request.form['train_number_single']
    
                app.logger.info(f"Checking the train number {trainNum}...")
    
                app.logger.debug(f"Redirecting to the locomotive page...")
    
                return redirect(url_for("getTrain", train_id=trainNum))

@app.route('/get/train/<train_id>', methods=['GET', 'POST'])
@basic_auth.required
def getTrain(train_id):
    if (train_id == "---"):
        return redirect(url_for('index'))
    
    if request.method == 'GET':

        app.logger.info(f"[GET] Loading train {train_id}...")

        res = isorDumper.dumpTrainPost(train_id)

        app.logger.debug(f"Train {train_id} dumped")

        if res is not None:

            app.logger.debug(f"Generating the table for train {train_id}...")

            return tableGenerator.getRouteTable(res, isorDumper.singleQueryRequestDelay)
        else:

            app.logger.debug(f"Too many requests, remaining: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds")

            return f"Too many requests, try again after: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds"
        
    ## when clicking refresh button
    elif request.method == 'POST':

        if request.form.get('start_dump') != None:

            app.logger.debug(f"Dumping train {train_id}...")

            res = isorDumper.dumpTrainPost(train_id)

            app.logger.debug(f"Train {train_id} dumped")

            if res is not None:

                app.logger.debug(f"Generating the table for train {train_id}...")

                return tableGenerator.getRouteTable(res, isorDumper.singleQueryRequestDelay) 
            else:

                app.logger.debug(f"Too many requests, remaining: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds")

                return f"Too many requests, try again after: {isorDumper.singleQueryRequestDelay - int(time.time() - isorDumper.lastRequest_singleQuery)} seconds"
                
        ## requesting new single locomotive  
        elif request.form.get('get_single_loco_button') != None:
        
            app.logger.debug(f"Obtainig the locomotive number...")

            locoNum = request.form['loco_number_single']

            app.logger.info(f"Checking the locomotive number {locoNum}...")

            if not locoHandler.checkLokoInput(locoNum):
                return "Zadejte číslo vlaky v jednom z následujících formátů: '749121' nebo '7491210' nebo '925427491210'"

            app.logger.debug(f"Redirecting to the locomotive page...")

            return redirect(url_for("get", loco_id=locoNum))
        
        ## requesting new single train
        elif request.form.get('get_single_train_button') != None:

                app.logger.debug(f"Obtainig the train number...")
    
                trainNum = request.form['train_number_single']
    
                app.logger.info(f"Checking the train number {trainNum}...")
    
                return redirect(url_for("getTrain", train_id=trainNum))
    
@app.route('/list_redirect')
def list_redirect():

    app.logger.debug("Redirecting to the list page...")

    return redirect(url_for('index'))

@app.route('/add_redirect')
def add_redirect():

    app.logger.debug("Redirecting to the add page...")

    return redirect(url_for('addloco'))

@app.route('/addloco', methods=['GET', 'POST'])
@basic_auth.required
def addloco():
    if request.method == 'GET':

        app.logger.info("[GET] Loading the add page...")

        return tableGenerator.createAdditionTable(locoHandler)
    
    elif request.method == 'POST':

        app.logger.info("[POST] Adding locomotive at the add page...")

        if request.form.get('add_loco') != None:

            app.logger.debug("Obtainig the locomotive number and note...")

            locoNum = request.form['loco_number']
            locoNote = request.form['loco_note']
            locoEditorName = request.form['loco_editor_name']

            app.logger.info(f"Checking the locomotive number {locoNum}...")

            if not locoHandler.checkLokoInput(locoNum):
                return "Zadejte číslo vlaky v jednom z následujících formátů: '749121' nebo '7491210' nebo '925427491210'"

            app.logger.debug(f"Adding locomotive {locoNum}...")

            newLoco = locoHandler.addLoco(locoNum, locoNote, locoEditorName)

            app.logger.debug(f"Dumping locomotive {newLoco}...")

            res = isorDumper.dumpSingleLocomotive(newLoco, timeoutByPass=True)

            if res is not None:

                app.logger.debug(f"Updating the index table...")

                tableGenerator.updateIndexTable(res)

            return redirect(url_for('add_redirect'))
        
        app.logger.debug(f"Scanning all locomotives to match the delete button...")

        for loco in locoHandler.locoList:
            if request.form.get(f"delete-{loco.fullNumber}") == "DELETE":

                app.logger.info(f"Deleting locomotive {loco.fullNumber}...")

                locoHandler.removeLoco(loco)
                break

        app.logger.debug("Generating the addition table...")

        tableGenerator.createAdditionTable(locoHandler)


        return redirect(url_for('add_redirect'))
        
    
def updateData(data):

    app.logger.info("Updating the index table...")

    if not checkTimeDelay(isorDumper.lastRequest_wholeTable, isorDumper.wholeTableRequestDelay):
        
        app.logger.debug(f"Too many requests, remaining: {isorDumper.wholeTableRequestDelay - int(time.time() - isorDumper.lastRequest_wholeTable)} seconds")

        return
    
    app.logger.debug(f"Creating new Thread for updating the index table...")

    thread = threading.Thread(target=tableGenerator.getIndexTableAsync, args=(locoHandler.locoList,isorDumper,))
    thread.start()

    ## to temporarily bypass the timeout and deny any other update requests
    isorDumper.lastRequest_wholeTable = time.time()

def checkTimeDelay(lastTime, delay):
    time_diff = time.time() - lastTime
    if time_diff < delay:
        return False
    return True

if __name__ == "__main__":
        app.run(host='0.0.0.0', debug=False, ssl_context='adhoc')