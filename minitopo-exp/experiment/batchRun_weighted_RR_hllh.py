#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python

import os
import csv
import sys
import time

###### function for judging if a file exists in the folder
def judging_file(file, folder='..'):
    for filename in os.listdir(folder):
        deeper_dir = os.path.join(folder, filename)
        if os.path.isfile(deeper_dir) and file in filename:
            return True
        if os.path.isdir(deeper_dir):
            return judging_file(file, deeper_dir)
    return False


######  web browse source file
browse_sourcefile='shi_WRR_singlerun.py'
######  web browse backup source file
browse_bkfile=browse_sourcefile+'_bk'
######  overwrite sourcefile
os.system('cp '+browse_sourcefile+' '+browse_bkfile)
######  web browse tmpfile
browse_tmpfile='tmp_browse.py'
website_listfile='website_list.txt'

###### line multifile:
# safari 11 prioritize the common five type files in below:
# file1 - HTML(26KB,255),
# file2 - images(900KB,8),
# file3 - JS (373KB,24)
# file4 - CSS(59KB,24),
# file5 - fonts (97KB, 16) or XHR

line_MULTIFILE = 71
###### line web browse
line_if_browse_num = 57
###### web site line
line_website_num = 58
###### web browse PROJECT line
line_browse_PROJECT_num = 59
######  scheduler line
line_fstream_scheduler = 60
###### single file line
line_single_file = 64
###### browse bandwidth & delay line
line_browse_bandwidth_num = 128

###### path_manager rtt line
line_pathmanager_fixed_rtt_num = 162
line_pathmanager_fixed_rtt_num2 = 258
line_pathmanager_fixed_rtt_num3 = 325

line_pathmanager_fixed_bandwidth_num = 163
line_pathmanager_fixed_bandwidth_num2 = 259
line_pathmanager_fixed_bandwidth_num3 = 326

line_pathmanager_rtt_num = 166
line_pathmanager_rtt_num2 = 262
line_pathmanager_rtt_num3 = 329

line_pathmanager_bandwidth_num = 167
line_pathmanager_bandwidth_num2 = 263
line_pathmanager_bandwidth_num3 = 330

######  path_manager source file
pathmanager_sourcefile='path_manager.go'
######  path_manager backup source file
pathmanager_bkfile=pathmanager_sourcefile+'_bk'
os.system('cp '+pathmanager_sourcefile+' '+pathmanager_bkfile)
pathmanager_tmpfile='tmp_path_manager.go'



######  PROJECT List
PROJECT_LIST = ['mp-quic']


###### FStream (project quic-go)  scheduler List
SCHEDULER_LIST = ['MultiPath'] #


######  Bandwidth & delay list
fixed_bandwidth = 1
fixed_rtt = 400
# data_num = 11
# step_bandwidth = 10
# step_delay = 40
data_num = 6
step_bandwidth = 20
step_delay = 80
bandwidth_delay_list = []


bandwidth_delay_list.append((100, 1))
for tmp in range(1, data_num-1):
     bandwidth_delay_list.append((100-tmp*step_bandwidth, tmp*step_delay))

bandwidth_delay_list.append((1, 400))



###### transfer one file (1) or two(0)
single_file = '0'

print(bandwidth_delay_list)



exam_num = 1

######  start loop
######  change PROJECT in a loop ...
######  change website in a loop
######  change quic-go (fstream) scheduler in a loop ...
######  change bandwidth in a loop ...
######  change delay in a loop ...


website = 'none'
for (bandwidth, delay) in bandwidth_delay_list:
    for project in PROJECT_LIST:
        for scheduler in SCHEDULER_LIST:

            ###############################  change browse.py  ############################
            ######  read from sourcefile and write to tmpfile
            fr = open(browse_sourcefile,'r')
            fw = open(browse_tmpfile,'w+')
            lines = fr.readlines()
            counter = 1
            for line in lines:
                if counter == line_if_browse_num:
                    fw.write('                    WEB_BROWSE: "0",     # single file transfer: 0  ;  web browse: 1\n')
                elif counter == line_single_file:
                    fw.write('                    SINGLE_FILE: \"%s\", # default 0, means transfer two file simultaneously, if 1 only transfer the first file\n'%single_file)
                elif counter == line_browse_PROJECT_num:
                    fw.write('                    PROJECT: \"%s\",     # quic-go is the prioritized stream scheduling project, mp-quic is the original multipath-quic project\n'%project)
                elif counter == line_website_num:
                    fw.write('                    JSON_FILE: \"%s\",   # specify websites to download\n'%website)
                elif counter == line_fstream_scheduler:
                    fw.write('                    PATH_SCHEDULER:\"%s\",   # quic-go param: MultiPath; SinglePath\n'%scheduler)
                elif counter == line_browse_bandwidth_num:
                    fw.write(
                        '    mptcpTopos = [{\'netem\': [(0, 0, \'loss 0.00%%\'), (1, 0, \'loss 0.00%%\')], \'paths\': [{\'queuingDelay\': \'0\', \'delay\': \'%f\'' % (
                                float(
                                    fixed_rtt) / 2.0) + ', \'bandwidth\': \'%d\'' % fixed_bandwidth + '}, {\'queuingDelay\': \'0\', \'delay\': \'%f\'' % (
                                float(delay) / 2.0) + ', \'bandwidth\': \'%d\'}]}]\n' % bandwidth)
                else:
                    fw.write(line)
                counter = counter+1
            fr.close()
            fw.close()
            ######  replace sourcefile
            os.system('cp '+browse_tmpfile+' '+browse_sourcefile)



            ###############################  change path_manager.go ############################
            ######  read from sourcefile and write to tmpfile
            fr = open(pathmanager_sourcefile,'r')
            fw = open(pathmanager_tmpfile,'w+')
            lines = fr.readlines()
            counter = 1
            for line in lines:
                if counter == line_pathmanager_rtt_num or counter == line_pathmanager_rtt_num2 or counter == line_pathmanager_rtt_num3:
                    fw.write('\t\trtt = %d * time.Millisecond\n' % delay)
                else:
                    if counter == line_pathmanager_bandwidth_num or counter == line_pathmanager_bandwidth_num2 or counter == line_pathmanager_bandwidth_num3:
                        fw.write('\t\tbandwidth = %d\n' % bandwidth)
                    else:
                        if counter == line_pathmanager_fixed_rtt_num or counter == line_pathmanager_fixed_rtt_num2 or counter == line_pathmanager_fixed_rtt_num3:
                            fw.write('\t\trtt = %d * time.Millisecond\n' % fixed_rtt)
                        else:
                            if counter == line_pathmanager_fixed_bandwidth_num or counter == line_pathmanager_fixed_bandwidth_num2 or counter == line_pathmanager_fixed_bandwidth_num3:
                                fw.write('\t\tbandwidth = %d\n' % fixed_bandwidth)
                            else:
                                fw.write(line)
                counter = counter + 1
            fr.close()
            fw.close()
            ######  replace sourcefile
            os.system('cp '+pathmanager_tmpfile+' '+pathmanager_sourcefile)

            ###############################  SCP  ############################
            os.system('scp -P 3022 '+pathmanager_sourcefile+' mininet@127.0.0.1:/home/mininet/go/src/github.com/lucas-clemente/quic-go')
            repeat_num = 5
            while (repeat_num > 0):
                ###############################  get all http folders before running browse  ###############################
                before_folder_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')

                ###############################  run browse  ############################
                os.system('./'+browse_sourcefile)
                time.sleep(30)

                ###############################  judge if browse finishes  ############################
                found = False  # find result folder of this run
                while found is False:
                    after_folder_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')
                    for folder in after_folder_list:
                        if ('mptcp' in folder) and (not folder in before_folder_list):
                            check_folder = folder
                            found = True
                            break
                    if found is False:
                        time.sleep(10)

                finishes_mark = 0
                print(check_folder)
                while finishes_mark == 0:
                    if judging_file('quic_client.log', check_folder) and judging_file('quic_server.log', check_folder):
                        finishes_mark = 1
                    if finishes_mark == 0:
                        time.sleep(5)

                ###### make sure quic_client.log and quic_server.log complete
                time.sleep(15)
                repeat_num = repeat_num - 1