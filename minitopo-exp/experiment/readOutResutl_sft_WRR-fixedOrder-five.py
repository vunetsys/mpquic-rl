import os

orderlist = [1, 2, 3, 4, 5]


def is_number(n):
    try:
        float(n)   # Type-casting the string to `float`.
                   # If string is not a valid `float`,
                   # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True


#file_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')
file_list = os.listdir('.')
mptcp_folder_list = []
for file in file_list:
	if 'mptcp' == file[-5:]:
		mptcp_folder_list.append(file)
# f_quic_go = open('sft_quic_go_result.txt', 'w+')
# f_mp_quic = open('sft_mp_quic_result.txt', 'w+')
f_all = open('all_sft_result.txt','w+')

# f_mp_quic.write('Bandwidth '+'RTT       '+'Scheduler '+'Small_time(ms) '+'Big_time(s) '+' Folder\n')
# f_quic_go.write('Bandwidth '+'RTT       '+'Scheduler '+'Small_time(ms) '+'Big_time(s) '+' Folder\n')
outStr = 'Project '+'Bandwidth '+'RTT       '+'Scheduler '
for o in orderlist:
	outStr += 'random'+str(o)+'_time(s) '
outStr += ' Completion'
outStr += ' Folder\n'
f_all.write(outStr)


times = []
server_orders = [] # server stream order
client_orders = [] # client stream order
file_orders = []
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
				if 'path_1' in line:
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
							line = line.strip()
							project = line.split(":")[1]
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
					###### get server order
					if project_mark == 0:
						if 'quic_server.log' == file:
							with open(os.path.join(subFolder3, file), 'r') as fi:
								lines = fi.readlines()
							i_cur = 0
							new_conn = 0
							while i_cur < len(lines) and new_conn < 2:
								if 'Serving new connection' in lines[i_cur]:
									new_conn += 1
								i_cur += 1
							while i_cur < len(lines):
								if "Detected: Stream" in lines[i_cur] and "Not Detected: Stream" not in lines[i_cur]:
									stream_id = lines[i_cur].split('Detected: Stream')[1].split(' ')[1]
									server_orders.append(int(stream_id))
								i_cur += 1
					###### read time
					if 'quic_client.log' == file:
						with open(os.path.join(subFolder3, file), 'r') as fi:
							lines = fi.readlines()
						i_cur=0
						all_completion_time=0
						while i_cur < len(lines):
							if 'https://10.1.0.1:6121/random' in lines[i_cur].split(" ")[-2]:
								file_name = lines[i_cur].split(" ")[-2]
								file_name = file_name.split("/")[-1]
								file_name = file_name.split(":")[0]
								file_id = int(file_name[-1])
								file_orders.append(file_id)

								if 'ms' == lines[i_cur][-3:-1]:
									time = float(lines[i_cur].split(' ')[-1].split('ms')[0]) / 1000
									times.append(time)
								else:
									time = lines[i_cur].split(' ')[-1].split('s')[0]
									if 'm' in time:
										minute = float(time.split('m')[0])
										second = float(time.split('m')[1])
										time = float(minute * 60 + second)
										times.append(time)
									else:
										times.append(float(time))

							if 'Info' in lines[i_cur]:
								##### get stream id
								tmp = lines[i_cur].split('Info')[1].split(' ')[3]
								if tmp == 'b':
									stream_id = 11
								elif tmp == 'd':
									stream_id = 13
								else:
									stream_id = int(tmp)
								client_orders.append(stream_id)
							if 'Completed all' in lines[i_cur]:
								if 'ms' == lines[i_cur][-3:-1]:
									all_completion_time = float(lines[i_cur].split(' ')[-1].split('ms')[0]) / 1000
								else:
									time_tmp = lines[i_cur].split(' ')[-1].split('s')[0]
									if 'm' in time_tmp:
										minute = float(time_tmp.split('m')[0])
										second = float(time_tmp.split('m')[1])
										all_completion_time = float(minute * 60 + second)
									else:
										all_completion_time =float(time)
							i_cur += 1


	# for so,co,t in zip(server_orders ,client_orders, times):
	# 	print(so,co,t)

	# server_orders == orderlist  and
	if  len(times) == len(orderlist):
		outStr = '%s ' % project + '%f ' % bandwidth + '%f ' % rtt + '%s    ' % scheduler + '%f    ' %times[file_orders.index(orderlist[0])]
		for oi in range(1, len(orderlist)):
			outStr += '%f ' %times[file_orders.index(orderlist[oi])]
		outStr += '%f ' %all_completion_time
		outStr += ' %s\n' % folder
		f_all.write(outStr)
	bandwidth = 0 #reset
	rtt = 0 #reset
	server_orders = [] #reset
	client_orders = []
	file_orders = []
	times = [] #reset



f_all.close()