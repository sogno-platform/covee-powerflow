# Copyright (c) 2020 Manuel Pitz, RWTH Aachen University
#
# Licensed under the Apache License, Version 2.0, <LICENSE-APACHE or
# http://apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-MIT or
# http://opensource.org/licenses/MIT>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.
import time

from dmu import dmu
from httpSrv import httpSrv

def listChanged(data, name, handle):
    print("list changed")

def dictChanged(data, name, handle):
    print("dict changed")

def subelementChanged(data, name, handle):
    print("subelement changed")

def mixedListChanged(data, name, handle):
    print("mixed list changed")

def mixedSubelementhanged(data, name, handle):
    print("mixed subelement changed")


print("start")


dmuObj = dmu()


#create elements
dmuObj.addElm("listTest",[])
dmuObj.addElm("dictTest",{"level1" : { "level2" : "testval" }})
dmuObj.addElm("mixedTest",{"level1" : { "list" : [] }})

#register handlers on different elements and subelements
dmuObj.addRx(listChanged,"listTest")
dmuObj.addRx(listChanged,"dictTest")
dmuObj.addRx(subelementChanged,"dictTest","level1","level2")
dmuObj.addRx(mixedListChanged,"mixedTest","level1","list")
dmuObj.addRx(mixedSubelementhanged,"mixedTest","level1")



dmuObj.setDataSubset({"level1" : { "level2" : "newValue1" }},"dictTest")#overwrite the whole dict
dmuObj.setDataSubset("newValue2","dictTest","level1","level2")#overwrite just one element

dmuObj.setDataSubset([1,2,3],"listTest")#overwrite a list

dmuObj.setDataSubset({ "list" : [1,2,3] },"mixedTest","level1")#overwrite multiple subelments

dmuObj.setDataSubset([4,5,6],"mixedTest","level1","list")#overwrite a list


while True:
    time.sleep(1)

print("end")
sys.exit(0)
