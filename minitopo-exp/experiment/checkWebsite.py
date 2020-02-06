import os

path = '/Users/shixiang/Desktop/request_website_code/dependency_graphs'  #dependency file of the websites to be download
outFile = 'website_list.txt'


fo = open(outFile, 'w+')

for file in os.listdir(path):
	file_path = os.path.join(path, file)
	if os.path.isdir(file_path):
		fo.write(file+'\n')
fo.close()