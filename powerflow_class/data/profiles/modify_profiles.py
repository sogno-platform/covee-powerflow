import numpy as np 
import csv
import os

cwd = os.getcwd()
wd = os.path.join(cwd, 'covee/powerflow/data/profiles')

csv_file = '/Test/Load_profile_2.csv'
profile = wd + csv_file


with open(os.path.join(wd, profile)) as csv_file: 
    profile_ = csv.reader(csv_file, delimiter=',')
    x = list(profile_)
    profile_ = np.array(x).astype("float")


profile_ = np.hstack((profile_,profile_))

rows = profile_
with open(os.path.join(profile), 'w+', encoding="ISO-8859-1", newline='') as csv_file:
    wr = csv.writer(csv_file)
    for row in rows:
        wr.writerow(row)
    csv_file.close()

