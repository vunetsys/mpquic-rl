import os

#file_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')
file_list = os.listdir('.')
mptcp_folder_list = []
for file in file_list:
	if 'mptcp' == file[-5:]:
		mptcp_folder_list.append(file)
f_quic_go = open('quic_go_result.txt', 'w+')
f_mp_quic = open('mp_quic_result.txt', 'w+')

f_mp_quic.write('bandwidth ' +' rtt '+'  small_time(ms) '+' big_time(s) '+' folder\n')
f_quic_go.write('bandwidth ' +' rtt '+'  small_time(ms) '+' big_time(s) '+' folder\n')


for folder in mptcp_folder_list:
	subFolder1 = os.path.join(folder,os.listdir(folder)[0])
	files_in_subFolder1 = os.listdir(subFolder1)
	print(folder)
	for file in files_in_subFolder1:
		###### read bandwidth & delay
		if os.path.isfile(os.path.join(subFolder1, file)):
			with open(os.path.join(subFolder1, file), 'r') as fi:
				lines = fi.readlines()
			for line in lines:
				if 'path_0' in line:
					data = line.split(':')[1].split(',')
					rtt = float(data[0]) * 2
					bandwidth = float(data[2])
					break
		else:
			subFolder2 = os.path.join(subFolder1, file)
			subFolder3 = os.path.join(subFolder2, os.listdir(subFolder2)[0])
			files_in_subFolder3 = os.listdir(subFolder3)
			project_mark = -1
			for file in files_in_subFolder3:
				###### read PROJECT : quic-go -> project_mark = 0; mp-quic -> project_mark = 1
				if 'https_quicTest' == file:
					with open(os.path.join(subFolder3, file), 'r') as fi:
						lines = fi.readlines()
					for line in lines:
						if 'project' in line:
							if 'quic-go' in line:
								project_mark = 0
							else:
								project_mark = 1
				else:
					###### read time
					if 'quic_client.log' == file:
						with open(os.path.join(subFolder3, file), 'r') as fi:
							lines = fi.readlines()
						for i in range(len(lines)-1):
							if 'Info' in lines[i+1] and 's' == lines[i][-2:-1]:
								###### small time is ??? ms
								if 'ms' == lines[i][-3:-1]:
									small_time = float(lines[i].split(' ')[-1].split('ms')[0])
								###### small time is ??? s -> change into ???*1000 ms
								else:
									small_time = float(lines[i].split(' ')[-1].split('s')[0])*1000
						big_time = (lines[-1].split(' ')[-1].split('s')[0])

	if project_mark == 0:
		f_quic_go.write('%f '%bandwidth+'%f '%rtt+'%f    '%small_time+'%s '%big_time+' %s\n'%folder)
		bandwidth = 0 #reset
		rtt = 0 #reset
		small_time = 0 #reset
		big_time = 0 #reset
	else:
		f_mp_quic.write('%f '%bandwidth+'%f '%rtt+'%f    '%small_time+'%s '%big_time+' %s\n'%folder)
		bandwidth = 0 #reset
		rtt = 0 #reset
		small_time = 0  # reset
		big_time = 0  # reset



f_mp_quic.close()
f_quic_go.close()