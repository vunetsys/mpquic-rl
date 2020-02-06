inputFile = 'quic_go_result.txt'
outFile = 'changed_'+inputFile

with open(inputFile, 'r') as fi:
	lines = fi.readlines()

fo = open(outFile, 'w+')
for i in range(1, len(lines)):
	line = lines[i]
	temps = line.split('\n')[0].split(' ')
	datas = []
	for temp in temps:
		if temp != '':
			datas.append(temp)
	bandwidth = float(datas[0])
	rtt = float(datas[1])
	small_time = float(datas[2])
	if 'm' in datas[3]:
		minute = float(datas[3].split('m')[0])
		second = float(datas[3].split('m')[1])
	else:
		minute = 0
		second = float(datas[3])
	big_time = minute*60+second
	fo.write('%f '%bandwidth+'%f '%second+'%f '%small_time+'%f\n'%big_time)

fo.close()
