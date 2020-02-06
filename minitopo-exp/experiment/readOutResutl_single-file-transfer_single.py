import os

def is_number(n):
    try:
        float(n)   # Type-casting the string to `float`.
                   # If string is not a valid `float`,
                   # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True

flag = False
small_time = 0

#file_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')
file_list = os.listdir('.')
mptcp_folder_list = []
for file in file_list:
	if 'mptcp' == file[-5:]:
		mptcp_folder_list.append(file)

f_all = open('all_sft_result.txt','w+')

f_all.write('Project '+'Bandwidth '+'RTT       '+'Scheduler '+'time(s) '+' Folder\n')


for folder in mptcp_folder_list:
	print(folder)
	subFolder1 = os.path.join(folder,os.listdir(folder)[0])
	if subFolder1.find(".DS_Store") != -1:
		subFolder1 = os.path.join(folder,os.listdir(folder)[1])

	files_in_subFolder1 = os.listdir(subFolder1)

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
						elif 'path_scheduler' in line:
							if project_mark == 0:
								line = line.strip()
								scheduler = line.split(':')[1]
							else:
								scheduler = "none"
				else:
					###### read time
					if 'quic_client.log' == file:
						with open(os.path.join(subFolder3, file), 'r') as fi:
							lines = fi.readlines()

						for i in range(len(lines)-1):
							if 'Info' in lines[i+1] :
								###### small time is ??? ms
								if 'ms' == lines[-1][-3:-1]:
									small_time = float(lines[-1].split(' ')[-1].split('ms')[0])/1000
								###### small time is ??? s -> change into ???*1000 ms
								else:
									small_time = lines[-1].split(' ')[-1].split('s')[0]
									if 'm' in small_time:
										minute = float(small_time.split('m')[0])
										second = float(small_time.split('m')[1])
										small_time = minute * 60 + second
									else:
										small_time = float(small_time)

#and is_number(small_time)
	if  small_time != 0  :
		if project_mark == 0:
			project = "quic-go"
			f_all.write(
				'%s ' % project + '%f ' % bandwidth + '%f ' % rtt + '%s    ' % scheduler + '%f    ' % small_time+ ' %s\n' % folder)

			bandwidth = 0 #reset
			rtt = 0 #reset
			small_time = 0 #reset
		else:
			project = "mp-quic"
			f_all.write(
				'%s ' % project + '%f ' % bandwidth + '%f ' % rtt + '%s    ' % scheduler + '%f    ' % small_time+ ' %s\n' % folder)

			bandwidth = 0 #reset
			rtt = 0 #reset
			small_time = 0  # reset


f_all.close()