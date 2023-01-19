from dmu.dmu import dmu
from dmu.httpSrv import httpSrv
from dmu.mqttClient import mqttClient
import coloredlogs, logging, threading
from threading import Thread, Event
import os


coloredlogs.install(level='DEBUG',
fmt='%(asctime)s %(levelname)-8s %(name)s[%(process)d] %(message)s',
field_styles=dict(
    asctime=dict(color='green'),
    hostname=dict(color='magenta'),
    levelname=dict(color='white', bold=True),
    programname=dict(color='cyan'),
    name=dict(color='blue')))
logging.info("Program Start")

if bool(os.getenv('MQTT_ENABLED')):
    mqtt_url = str(os.getenv('MQTTURL'))
    mqtt_port = int(os.getenv('MQTTPORT'))
    mqtt_user = str(os.getenv('MQTTUSER'))
    mqtt_password = str(os.getenv('MQTTPASS'))
else:
    mqtt_url = "mqtt"
    mqtt_port = 1883
    mqtt_password = ""
    mqtt_user = ""


############################ Start the Server #######################################################

''' Initialize objects '''
dmuObj = dmu()

''' Start mqtt client '''
mqttObj = mqttClient(mqtt_url, dmuObj, mqtt_port, mqtt_user, mqtt_password)

#######################################################################################################

# send from PMU
dmuObj.addElm("edgePMU3", {})
mqttObj.attachPublisher("/location_10003/30025/edgePMU3 ch1 amplitude","json","edgePMU3")
dmuObj.addElm("edgePMU4", {})
mqttObj.attachPublisher("/location_10001/30001/edgePMU4 ch1 amplitude","json","edgePMU4")
dmuObj.addElm("edgePMU9", {})
mqttObj.attachPublisher("/location_10002/30013/edgePMU9 ch1 amplitude","json","edgePMU9")

# send from Kibertnet
dmuObj.addElm("location4", {})
mqttObj.attachPublisher("/location_4/4/operationPower","json","location4")
dmuObj.addElm("location7", {})
mqttObj.attachPublisher("/location_7/7/operationPower","json","location7")
dmuObj.addElm("location34", {})
mqttObj.attachPublisher("/location_34/34/operationPower","json","location34")
dmuObj.addElm("location35", {})
mqttObj.attachPublisher("/location_35/35/operationPower","json","location35")
dmuObj.addElm("location36", {})
mqttObj.attachPublisher("/location_36/36/operationPower","json","location36")

while True:
    dmuObj.setDataSubset({"time": "2023-01-18T11:29:00Z", "value": 234.4702},"edgePMU3")
    dmuObj.setDataSubset({"time": "2023-01-18T11:37:00Z", "value": 0.8},"location4")