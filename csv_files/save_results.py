import csv
import os
import numpy as np

class save_results:

    def __init__(self, voltage, reactive_power, active_power, active_power_batt, iterations):       
        self.voltage = voltage
        self.reactive_power = reactive_power
        self.active_power = active_power
        self.active_power_batt = active_power_batt
        self.iterations = iterations
    
    
    def save_csv(self):
        cwd = os.getcwd()
        wd = os.path.join(cwd, 'csv_files/results')
        wd.replace("\\", "/")

        rows = self.voltage
        with open(os.path.join(wd, 'voltage.csv'), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
            wr = csv.writer(csv_file)
            for row in rows:
                wr.writerow(row)
        csv_file.close()

        rows = zip(self.iterations,self.iterations)
        with open(os.path.join(wd, 'time.csv'), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
            wr = csv.writer(csv_file)
            for row in rows:
                wr.writerow(row)
        csv_file.close()

        rows = self.reactive_power
        with open(os.path.join(wd, 'reactive_power.csv'), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
            wr = csv.writer(csv_file)
            for row in rows:
                wr.writerow(row)
        csv_file.close()

        rows = self.active_power
        with open(os.path.join(wd, 'active_power.csv'), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
            wr = csv.writer(csv_file)
            for row in rows:
                wr.writerow(row)
        csv_file.close()

        rows = self.active_power_batt
        with open(os.path.join(wd, 'active_power_batt.csv'), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
            wr = csv.writer(csv_file)
            for row in rows:
                wr.writerow(row)
        csv_file.close()

