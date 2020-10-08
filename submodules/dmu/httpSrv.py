# Copyright (c) 2020 Manuel Pitz, RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0, <LICENSE-APACHE or
# http://apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-MIT or
# http://opensource.org/licenses/MIT>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging, json, time


class httpSrv:
    def __init__(self, host, port, dmuObj):
        self.__log = logging.getLogger(__name__)
        logging.getLogger('httpd-ken').setLevel(logging.ERROR)
        self.__log.debug("Start HTTP server on %s:%s",host,port)
        self.__reqHandle = reqHandler
        self.__reqHandle.registerdmu(self.__reqHandle, dmuObj)
        httpd = HTTPServer((host, port), self.__reqHandle)
        httpd.serve_forever()


class reqHandler(BaseHTTPRequestHandler):

    def log_message(self, *args ):
        pass
   
    def registerdmu(self, dmuObj):
        self.__dmuObj = dmuObj

    def do_GET(self):
        self.__log = logging.getLogger(__name__)
        availableActions = ["get", "add", "remove"]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._send_cors_headers()
        self.end_headers()

        pathArray = []
        for data in self.path.split("/"):
            if data:
                pathArray.append(data)

        if len(pathArray)<=1 or (not pathArray[0] in availableActions):
            self.__log.warning("GET Path mismatch %s", self.path)
            self.wfile.write(('{"status":"url_error"}').encode('utf-8'))
            return
            
        if pathArray[0] == "get":
            if not self.__dmuObj.elmExists(pathArray[1]):
                self.__log.warning("Element does not exist %s", pathArray[1])
                self.wfile.write(('{"status":"elm_does_not_exist"}').encode('utf-8'))
                return
            try:
                pathArray.pop(0)
                self.wfile.write(json.dumps({"data" : self.__dmuObj.getDataSubset(pathArray[0],pathArray[1:])}).encode('utf-8'))
            except TypeError:
                self.__log.warning("Requests data that was not JSON serializable")
                self.wfile.write(json.dumps({"status":"non_serializable_data_requested"}).encode('utf-8'))
                return
            
        elif pathArray[0] == "add":
            if self.__dmuObj.addElm(pathArray[1],None):
                self.wfile.write(('{"status":"success"}').encode('utf-8'))
                return
            else:
                self.__log.warning("Error creating element %s", self.path)
                self.wfile.write(('{"status":"creation_error"}').encode('utf-8'))
                return               

        elif pathArray[0] == "remove":
            pass #@todo to be implemented


    def do_POST(self):
        self.__log = logging.getLogger(__name__)
        availableActions = ["set","query","search","grafana"]

        content_len = int(self.headers.get('Content-Length'))
        
        pathArray = []
        for data in self.path.split("/"):
            if data:
                pathArray.append(data)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._send_cors_headers()
        self.end_headers()

        if len(pathArray) <= 1 or (not pathArray[0] in availableActions):
            self.__log.warning("POST Path mismatch %s", self.path)
            self.wfile.write(('{"status":"url_error"}').encode('utf-8'))
            return

        post_body = self.rfile.read(content_len)
        try:
            json_content = json.loads(post_body.decode('utf-8'))
        except:
            self.__log.error("Json data invalid")
            self.wfile.write(('{"status":"json_data_invalid"}').encode('utf-8'))
            return
        if pathArray[0] == "set":#update value in existing element
            if not "data" in json_content:
                self.__log.warning("No data element in content")
                self.wfile.write(('{"status":"no_data_element"}').encode('utf-8'))
                return
            pathArray.pop(0)
            if self.__dmuObj.setDataSubset(json_content["data"],pathArray):
                self.wfile.write(('{"status":"success"}').encode('utf-8'))
            else:
                self.wfile.write(('{"status":"data_set_error"}').encode('utf-8'))
                self.__log.warning("Data could not be set %s", pathArray[1])
        elif pathArray[0] == "grafana":#grafana interface
            if pathArray[1] == "search":#grafana search
                self.wfile.write(json.dumps(self.__dmuObj.getAllElementNames()).encode('utf-8'))
            elif pathArray[1] == "query":#grafana query
                dataArray = []
                tempTimestamp = time.time()*1000 #used to timetag single values
                for i in range(len(json_content["targets"])):
                    if not "target" in json_content["targets"][i]:#for some reason grafana requests something stange first
                        continue
                    elmName = json_content["targets"][i]["target"]
                    elmList = elmName.split("/")
                    if not self.__dmuObj.elmExists(elmList[0],elmList[1:]):
                        self.__log.warning("Element does not exist %s", elmName)
                        dataArray.append({"target": elmList[-1], "datapoints" : []})#add empty element to make client happy if non existig element is queried
                        continue
                    try:
                        outputData = self.__dmuObj.getDataSubset(elmList[0],elmList[1:])
                        if isinstance(outputData,list):
                            if len(outputData)>1:
                                dataArray.append({"target": elmList[-1], "datapoints" : sorted(outputData, key = lambda x: x[1])})
                            else:
                                dataArray.append({"target": elmList[-1], "datapoints" : [outputData]})
                        #elif isinstance(outputData,float) or isinstance(outputData,int):
                        else:
                            dataArray.append({"target": elmList[-1], "datapoints" : [[outputData,tempTimestamp]]})
                    except TypeError:
                        self.__log.warning("Requests data that was not JSON serializable")
                        dataArray.append({"target": elmList[-1], "datapoints" : []})#add empty element to make client happy if non existig element is queried
                self.wfile.write(json.dumps(dataArray).encode('utf-8'))
            else:
                self.wfile.write(('{"status":"grafana_url_error"}').encode('utf-8'))
                self.__log.warning("Unknown url %s", pathArray[1])

    def _send_cors_headers(self):
        """ Sets headers required for CORS """
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,ORIGIN")
        self.send_header("Access-Control-Allow-Headers", "x-api-key,Content-Type")

    def do_OPTIONS(self) :

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Headers", "accept, Content-Type")
        self.end_headers()