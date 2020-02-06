import os

#file_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')
file_list = os.listdir('.')
mptcp_folder_list = []

object_index = 0

for file in file_list:
	if 'mptcp' == file[-5:]:
		mptcp_folder_list.append(file)
# f_quic_go = open('browse_quic_go_result.txt', 'w+')
# f_mp_quic = open('browse_mp_quic_result.txt', 'w+')
f_all = open('all_browse_result.txt','w+')

# f_mp_quic.write('Bandwidth '+'RTT       '+'Website '+'Scheduler '+'Page Load Time '+'Render Time '+'Object Index '+' Folder\n')
# f_quic_go.write('Bandwidth '+'RTT       '+'Website '+'Scheduler '+'Page Load Time '+'Render Time '+'Object Index '+' Folder\n')
f_all.write('Website        '+'Browser '+'Project '+'fixedBandwidth '+'fixedRTT '+'Bandwidth '+'RTT  '+'plr    '+'Scheduler '+'Page Load Time '+'Object Index '+' Folder\n')

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
				if 'path_1' in line:
					data = line.split(':')[1].split(',')
					rtt = float(data[0]) * 2
					bandwidth = float(data[2])
				if 'path_0' in line:
					data = line.split(':')[1].split(',')
					fixed_rtt = float(data[0]) * 2
					fixed_bandwidth = float(data[2])
		else:
			subFolder2 = os.path.join(subFolder1, file)
			plr = subFolder1.split('_')[12]
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
							project = line.split(':')[1]
							if 'quic-go' in line:
								project_mark = 0
							else:
								project_mark = 1
						elif 'json_file' in line:
							line = line.strip()
							website = line.split(':')[1]
						elif 'browser' in line:
							line = line.strip()
							browser = line.split(':')[1]
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
							if 'Page Load Time' in lines[i+1]:
								lines[i+1] = lines[i+1].strip()
								plt = float(lines[i+1].split(" ")[4])
							elif 'Render Time' in lines[i+1]:
								rt = float(lines[i+1].split(" ")[3])
							elif 'ObjectIndex' in lines[i+1]:
								object_index = float(lines[i+1].split(" ")[-1])

	if plt != 0 and rt != 0:

			f_all.write(
				 '%s   ' % website + '%s  ' % browser +'%s ' % project + '%f ' % fixed_bandwidth + '%f ' % fixed_rtt+ '%f ' % bandwidth + '%f ' % rtt  + '%s    ' % plr+ '%s    ' % scheduler + '%f        ' % plt + '%s ' %object_index + ' %s\n' % folder)
			# f_mp_quic.write(
			# 	'%f '%bandwidth+'%f '%rtt+'%s    '%website+'%s    '%scheduler+'%f    '%plt+'%s '%rt+ '%s ' %object_index+' %s\n'%folder)
			bandwidth = 0 #reset
			rtt = 0 #reset
			website = ''#reset
			plt = 0 #reset
			rt = 0 #reset
			object_index = 0 #reset



# f_mp_quic.close()
# f_quic_go.close()
f_all.close()