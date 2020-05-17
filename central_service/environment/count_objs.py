'''
    Simple script file that helps on selecting training "samples" for the environment
'''
import os
import json

PATH = './environment/dependency_graphs/'

lisdir = os.listdir(PATH)
print ("-------------------------------------------")
print ("Number of objects in dependency graph: {}".format(len(lisdir)))
print ("-------------------------------------------")


# Create an array that contains dict: "graph", "obj - size"
sizeof_graphs = []
for item in lisdir:
    sp = PATH + item + '/' + item + '.json'
    with open(sp, 'r') as fp:
        data = json.load(fp)

        sizeof_graphs.append({
            "file": item, 
            "size": len(data['objs'])
        })

# Order files by size
order_by_max = sorted(sizeof_graphs, key=lambda k: k['size'] )

# Save files ordered by size in ./logs/objs.json
with open('./objs.json', 'w') as fp:
    json.dump(order_by_max, fp, ensure_ascii=True, indent=4, sort_keys=True)


# count_object value that contains >= 32 objects/stream and less than 100
lar32 = [elem for elem in order_by_max if elem['size'] >= 32 and elem['size'] <= 100]
print ("---------------------------------------------------------")
print ("Objects in dependency graph that contain >= 32 files: {}".format(len(lar32)))
print ("---------------------------------------------------------")


# count_total_objects from graphs that contain >= 32 files and less than 100 
totalsize32 = 0
for elem in lar32:
    totalsize32 += elem['size']
print ("--------------------------------------------------------------")
print ("Total number of files in graphs that contain >= 32 files: {}".format(totalsize32))
print ("--------------------------------------------------------------")


# print objects >= 32 one by one for manual validation
print ("--------------------------------------------------------------")
for index, elem in enumerate(lar32):
    print ("{}, \t {}\t\t, size: {}".format(index+1, elem['file'], elem['size']))
print ("--------------------------------------------------------------")


# save graphs for training
with open('./graphs.json', 'w') as fp:
    json.dump(lar32, fp, ensure_ascii=True, indent=4, sort_keys=True)