#
'''
    Simple script file thats help on spliting our dependency graphs
'''
from sklearn.model_selection import train_test_split
import json

with open('./environment/graphs.json', 'r') as fp:
    data = json.load(fp)

x_train, x_test = train_test_split(data, test_size=0.2, random_state=42, shuffle=True)

# Save results
with open('./environment/train_graphs.json', 'w') as fp:
    json.dump(x_train, fp, ensure_ascii=True, indent=4, sort_keys=True)

with open('./environment/test_graphs.json', 'w') as fp:
    json.dump(x_test, fp, ensure_ascii=True, indent=4, sort_keys=True)