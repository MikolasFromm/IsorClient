import time
import requests
import queue
from flask import Flask
from isorDataTypes import IsorRequest, IsorResponse

class IsorClient:
    def __init__(self, logger : Flask.logger, username : str, password : str):
        self.logger = logger

        ## credentials
        self.username = username
        self.password = password

        ## urls
        self.url_login = "https://isor.spravazeleznic.cz/Login/Login"
        self.url_request_loco = "https://isor.spravazeleznic.cz/Dotazy/D1320"
        self.url_request_train = "https://isor.spravazeleznic.cz/Dotazy/D2040"
        self.url_mainpage = "https://isor.spravazeleznic.cz/"

        ## request delay
        self.lastRequest = time.time()
        self.requestDelay = 0.5
        self.lastRequestUrl = ""

        ## session cookies
        self.logged = False
        self.sessionCookies = None
        self.loginTimeOut = 60 * 60 ## 1 hour

        ## requests queue
        self.requestQueue = queue.Queue()
        self.responseDict = {}

        self.loginToISOR()

    def GetResponse(self, request : IsorRequest) -> IsorResponse:
        self.requestQueue.put(request)

        while request.guid not in self.responseDict:
            pass
        
        return self.responseDict.pop(request.guid)
    
    def RequestHandler(self):
        while True:
            if (time.time() - self.lastRequest) > self.requestDelay and not self.requestQueue.empty():
                request = self.requestQueue.get()
                
                self.logger.debug(f"Handling request {request.guid}...")


                if (self.lastRequestUrl != request.url or (time.time() - self.lastRequest) > self.loginTimeOut):
                    self.checkLogOn(request.url)

                rawResponse = requests.post(request.url, data = request.body, cookies=self.sessionCookies)

                self.lastRequestUrl = request.url

                self.lastRequest = time.time()

                response = IsorResponse(rawResponse.status_code, rawResponse.text, request.guid)

                self.responseDict[request.guid] = response

                self.logger.debug(f"Request {request.guid} handled!")

                self.requestQueue.task_done()

    def loginToISOR(self):
        self.logger.info("Trying to log in to ISOR...")

        ## make simple GET request to obtain any sessionId
        cookieGetter = requests.get(self.url_login)
        self.sessionCookies = cookieGetter.cookies

        ## validate the sessionCookie with correct username and password
        loginPayload = {'jmeno': self.username, 'heslo': self.password}
        validation = requests.post(self.url_login, data = loginPayload, cookies=self.sessionCookies)

        ## check if we are logged in
        if self.requestPageAvailable(self.url_request_loco) and validation.status_code == 200:
            
            self.logger.debug("Logged in to ISOR!")

            self.logged = True

            return True
        else:

            self.logger.debug("Failed to log in to ISOR!")

            self.logged = False

            raise Exception("Failed to log in to ISOR!")

    def checkLogOn(self, page):
        self.logger.debug("Checking if logged into ISOR...")

        if not self.requestPageAvailable(page):

            self.logger.debug("Not logged in to ISOR, trying to log in again...")

            result = self.loginToISOR()

            if not result:

                self.logger.debug("Failed to log again in to ISOR!")

                raise Exception("Failed to log in to ISOR!")

    def requestPageAvailable(self, page):
        self.logger.debug(f"Trying to open {page} to check if logged in...")

        ## If we open (locked) request page and the request page is returned, we are logged in

        logOnTestRequest = requests.get(page, cookies=self.sessionCookies)
        openedPage = logOnTestRequest.url

        self.logger.debug(f"Page {openedPage} openned, expected {page}...")

        if openedPage != page: ## if the url is the login page, we are not logged in
            return False
        else:
            return True
