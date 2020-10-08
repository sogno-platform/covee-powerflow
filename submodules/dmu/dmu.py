
# Copyright (c) 2020 Manuel Pitz, RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0, <LICENSE-APACHE or
# http://apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-MIT or
# http://opensource.org/licenses/MIT>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.
import logging, copy, threading, time, requests, json, uuid

dataStruct = {
    "data" : None,
    "notifier" : None,
    "lock" : None,
}

txSyncStruct = {
    "target"  : [],
    "thread" : [],
    "subelements" : []
}

rxSyncStruct = {
    "action" : [],
    "thread" : [],
    "threadRun" : True,
    "subelements" : []
}

class dmu:
    def __init__(self):
        self.__rxSyncRegestry = {}
        self.__txSyncRegestry = {}
        self.__data = {}
        self.__log = logging.getLogger(__name__)
        self._dmuTargets = []#a list of other dmus to sync with

    def addSubElm(self, data, name, *args):
        '''
            this function can be used to create new subelements
            if return is -2 this means error
            if return is -1 this means ok dict
            if return is >= 0 this is the list index
        '''
        name, args = self.__handleListArguments(name, args)
        addList = True
        if not self.elmExists(name, args):
            if not self.elmExists(name, args[:-1]):
                self.__log.error("Motherelemnts dont't exists %s->%s", name, '->'.join(str(x) for x in args[:-1]))
                return -1
            else:
                addList = False
        
        self.__data[name]["lock"].acquire()

        target = self.__data[name]
        args.insert(0,"data")
        lastKey = ""
        keyCount = len(args)
        loopIteration = 0
        for key in args:                   
            lastKey = key
            if (not isinstance(target[key],dict) and not isinstance(target[key],list)) or (loopIteration >= (keyCount - 1)):
                break    
            target = target[key]
            loopIteration = loopIteration + 1

        if isinstance(target[lastKey],dict):
            target[lastKey].update({args[-1]: copy.deepcopy(data)})
        elif isinstance(target[lastKey],list):
            target[lastKey].append(copy.deepcopy(data))
            ret = len(target[lastKey]) -1

        self.generateNotifiers(self.__data[name]["notifier"],name,self.__data[name]["data"])
        self.__data[name]["lock"].release()

        return ret


    def addElm(self, name, data, notify = False):
        '''
        This function creates new elements and sets the initial data including the datatype.
        The data strucutre should be changed afterwards (makes source code complicated)
        '''

        if name in self.__data:
            self.__log.error("Element %s already exists", name)
            return False
        else:
            dataStruct["data"] = data
            self.__data.update({name : copy.deepcopy(dataStruct)})
            self.__data[name]["lock"] = threading.Lock()
            self.__data[name]["lock"].acquire()
            self.__data[name]["notifier"] = {}
            self.__data[name]["notifier"].update({"handle" : threading.Condition(), "sub" : {}})
            self.generateNotifiers(self.__data[name]["notifier"],name,self.__data[name]["data"])

            self.__data[name]["lock"].release()
            if notify:
                with self.__data[name]["notifier"]["handle"]:
                    self.__data[name]["notifier"]["handle"].notify_all()
            return True
        return False

    def generateNotifiers(self, target, name, data = None):
        '''
        this function generates all notifiers and is auto called by dmu itself to update new values
        '''
        if isinstance(data, dict):#register notifiers for each subelements
            for key in data:
                if not key in target["sub"]:#create if not exists
                    target["sub"].update({key : { "handle" : threading.Condition(), "sub" : {}}})
                self.generateNotifiers(target["sub"][key], name, data[key])
    
    def cleanNotifiers(self, target, name, subElmList = None):
        '''
        this function cleans orphaned values from the notifier list and also from the rx and tx sync regestry
        '''
        if subElmList is None:
            subElmList = []
        removeKeys = []
        removeSubElmList = []
        for key in target["sub"]:
            subElmList.append(key)
            self.cleanNotifiers(target["sub"][key], name, copy.deepcopy(subElmList))
            if not self.elmExists(name,subElmList):
                removeKeys.append(key)
                removeSubElmList.append(copy.deepcopy(subElmList))
            del subElmList[-1]

        for i in range(len(removeKeys)):  
            uuid = self.getThreadUuid(name,removeSubElmList[i])
            if uuid != None:
                self.rmRx(name,uuid)
            del target["sub"][removeKeys[i]]

    def buildNamesMap(self, data, listIn):
        ret = []
        if isinstance(data, dict):
            for key in data:
                listIn.append(key)
                returnList = self.buildNamesMap(data[key],copy.deepcopy(listIn))
                listIn.pop()
                ret = ret + copy.deepcopy(returnList)
        elif isinstance(data, list) and len(data) < 10:#@todo this 10 is not a good approach think about something better
            for i in range(len(data)):
                listIn.append(str(i))
                returnList = self.buildNamesMap(data[i],copy.deepcopy(listIn))
                listIn.pop()
                ret = ret + copy.deepcopy(returnList)
        else:
        #elif isinstance(data, list) or isinstance(data,int) or isinstance(data,float):
            ret.append("/".join(listIn))     
        return ret

    def getAllElementNames(self):
        elm = []
        for key in self.__data:
            elm = elm + self.buildNamesMap(self.__data[key]["data"],[key])

        return elm

    def rxThread(self, name, uuid):
        while self.__rxSyncRegestry[name][uuid]["threadRun"]:
            if not self.elmExists(name):
                continue
            status, data = self.getDataSubsetUpdate(name,self.__rxSyncRegestry[name][uuid]["subelements"])
            if not status:#wait statemant ran into timeout
                continue
            self.__rxSyncRegestry[name][uuid]["action"](data,name,self.__rxSyncRegestry[name][uuid]["subelements"])

    def getThreadUuid(self,name, *args):
        '''
            returns the thread uuid if exists otherwise none
        '''

        name, args = self.__handleListArguments(name, args)

        if not name in self.__rxSyncRegestry:
            logging.warn("No rx handle registered for %s", name)
            return None

        for key in self.__rxSyncRegestry[name]:
            if self.__rxSyncRegestry[name][key]["subelements"] == args:
                return key
        
        return None

    def addRx(self, handle, name, *args):
        '''
        creats a handle for new incoming data
        '''
        name, args = self.__handleListArguments(name, args)

        
        if not name in self.__rxSyncRegestry:
            self.__rxSyncRegestry.update({name : {}})
        
        if not self.elmExists(name,args):
            logging.warn("One or more element do not exist %s->%s",name, '->'.join(args))
            return False

        uuidStr = str(uuid.uuid1())
        self.__rxSyncRegestry[name][uuidStr] = copy.deepcopy(rxSyncStruct)

        
        self.__rxSyncRegestry[name][uuidStr]["action"] = handle
        self.__rxSyncRegestry[name][uuidStr]["subelements"] = args
        thread = threading.Thread(target = self.rxThread, args = (name, uuidStr))
        self.__log.debug("Add sync rx action for %s->%s", name, '->'.join(args))
        self.__rxSyncRegestry[name][uuidStr]["thread"] = thread
        thread.start()
        return uuidStr

    def rmRx(self, name, uuid):
        '''
        remove a handle for new incoming data
        '''

        if not name in self.__rxSyncRegestry:
            logging.warn("Try to remove RX thread from non existing object %s", name)
            return False
        
        if not uuid in self.__rxSyncRegestry[name]:
            logging.warn("RX element does not exists %s->%s", name, '->'.join(args))
            return False
        
        threadHandle = self.__rxSyncRegestry[name][uuid]["thread"]
        self.__rxSyncRegestry[name][uuid]["threadRun"] = False
        threadHandle.join()
        logging.warn("Thread with uuid %s was terminated",uuid)
        del self.__rxSyncRegestry[name][uuid]




    def addTx(self, target, name, *args):
        '''
        creates a forwarder to send the update to another instance of the dmu
        '''
        name, args = self.__handleListArguments(name, args)
        if not name in self.__txSyncRegestry:
            self.__txSyncRegestry.update({name : {}})

        if target not in self.__txSyncRegestry[name]:
            self.__txSyncRegestry[name].update({target : {}})

        uuidStr = str(uuid.uuid1())
        self.__txSyncRegestry[name][target][uuidStr] = copy.deepcopy(txSyncStruct)

        self.__txSyncRegestry[name][target][uuidStr]["target"] = target
        self.__txSyncRegestry[name][target][uuidStr]["subelements"] = args
        thread = threading.Thread(target = self.txThread, args = (target, name , uuidStr))
        self.__txSyncRegestry[name][target][uuidStr]["thread"] = thread
        thread.start()
        self.__log.debug("Add sync tx thread for %s to %s", name, target)



    def txThread(self, target, name, uuidStr):
        while True:
            status,data = self.getDataSubsetUpdate(name,self.__txSyncRegestry[name][target][uuidStr]["subelements"])
            if not status:#wait statemant ran into timeout
                continue
            data = json.dumps({"data" : data}).encode('utf-8')
            if len(self.__txSyncRegestry[name][target][uuidStr]["subelements"]) > 0 :
                urlParam = "/" + '/'.join(self.__txSyncRegestry[name][target][uuidStr]["subelements"])
            else:
                urlParam = ""
            try:
                result = requests.post("http://" + target + "/set/" + name + urlParam, data = data)
            except:
                self.__log.warning("Remote dmu %s note reachable", target)

    def setDataSubsetList(self,args):
        return self.setDataSubset(args[0],args[1],args[2:])

    def setDataSubset(self,data,name,*args):
        '''
            write data into name and args subset
        '''
        name, args = self.__handleListArguments(name, args)
        ret = True
        noNotify = False#used to handle the case of writing to an array
        if not name in self.__data:
            self.__log.error("Element %s does not exists", name)
            ret = False
        else:
            self.__data[name]["lock"].acquire()
            target = self.__data[name]
            args.insert(0,"data")
            lastKey = ""
            keyCount = len(args)
            loopIteration = 0
            for key in args:
                if isinstance(target, dict):
                    if key not in target:
                        self.__log.error("Element %s does not exist in %s ", key, name)
                        ret = False
                        break
                elif isinstance(target, list):
                    if key > len(target) - 1:
                        self.__log.error("Element %s does not exist in %s ", key, name)
                        ret = False
                        break                    
                lastKey = key
                if (not isinstance(target[key],dict) and not isinstance(target[key],list)) or (loopIteration >= (keyCount - 1)):
                    break    
                target = target[key]
                loopIteration = loopIteration + 1
            if ret is True:
                target[lastKey] = copy.deepcopy(data)

            self.generateNotifiers(self.__data[name]["notifier"], name,self.__data[name]["data"])
            self.cleanNotifiers(self.__data[name]["notifier"], name)

            self.__data[name]["lock"].release()
            if ret is True:
                notifier = self.getNotifierHandle(self.__data[name]["notifier"], args[1:])
                with notifier:
                    notifier.notify_all()

        return ret

    def getNotifierHandle(self, target, argsList):
        if len(argsList) > 0 and argsList[0] in target["sub"]:
            return self.getNotifierHandle(target["sub"][argsList[0]],argsList[1:])
        else:
            return target["handle"]


    def getDataSubset(self,name,*args):
        '''
            reads a subset from a data element 
        '''
        ret = None
        name, args = self.__handleListArguments(name, args)
        if not name in self.__data:
            self.__log.error("Element %s does not exists", name)
        else:
            self.__data[name]["lock"].acquire()
            target = self.__data[name]["data"]
            try:
                for arg in args:
                    if isinstance(target, list):
                        arg = int(arg)#make sure we convert it to integer
                    target = target[arg]
                ret = copy.deepcopy(target)
            except KeyError:
                self.__log.error("Could not find the requested data in element {}: {}".format(name,args))
            finally:
                self.__data[name]["lock"].release()
                return ret

    def getDataSubsetUpdate(self,name,*args):
        '''
            reads a subset from a data element 
        '''
        data = None
        status = True
        name, args = self.__handleListArguments(name, args)
        if not name in self.__data:
            self.__log.error("Element %s does not exists", name)
        else:
            notifier = self.getNotifierHandle(self.__data[name]["notifier"], args)
            with notifier:
                notifier.wait()
            self.__data[name]["lock"].acquire()
            target = self.__data[name]["data"]
            try:
                for arg in args:
                    target = target[arg]
                data = copy.deepcopy(target)
            except KeyError:
                self.__log.exception("Could not find the requested data")
            finally:
                self.__data[name]["lock"].release()
                return status, data


    def elmExists(self, name, *args):
        '''
        check if key exists
        '''
        ret = None
        name, args = self.__handleListArguments(name, args)

        if name in self.__data:
            ret = True
        else:
            ret = False

        if ret is not False and len(args) > 0:#check submelements
            target = self.__data[name]["data"]
            for arg in args:
                if isinstance(target, dict):
                    if arg in target:
                        target = target[arg]
                        continue
                elif isinstance(target, list):
                    try:#try to access the vlaue
                        target = target[int(arg)]
                        continue
                    except:
                        ret = False
                break

        
        return ret

    def __handleListArguments(self,name,args):
        ''' handles cases of lists and values as arguements '''

        if isinstance(name,list):
        # if we pass only a list, instead of a single name and than comma sperated args, extract the first element as the name
            return str(name[0]), name[1:]

        if len(args) == 1 and isinstance(args[0],list):
        # if we pass a list in as argument instead of several arguments, squash it
            return str(name), [arg for arglist in args for arg in arglist]
        elif isinstance(args, tuple):
            return str(name), list(args)
        else:
            return str(name), args
