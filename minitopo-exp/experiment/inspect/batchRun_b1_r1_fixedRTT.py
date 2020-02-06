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



###### single-path PROJECT line
line_singlepath_PROJECT_num = 57
###### single-path bandwidth & delay line
line_singlepath_bandwidth_num = 121
######  single-path source file
singlepath_sourcefile='shi_highbdp_quic_singlepath.py'
######  single-path backup source file
singlepath_bkfile=singlepath_sourcefile+'_bk'
######  single-path backup sourcefile
os.system('cp '+singlepath_sourcefile+' '+singlepath_bkfile)
######  single-path tmpfile
singlepath_tmpfile='tmp_highbdp_quic_singlepath.py'



###### path_manager rtt line
line_pathmanager_fixed_rtt_num = 162
line_pathmanager_fixed_rtt_num2 = 256
line_pathmanager_fixed_rtt_num3 = 323

line_pathmanager_fixed_bandwidth_num = 163
line_pathmanager_fixed_bandwidth_num2 = 257
line_pathmanager_fixed_bandwidth_num3 = 324

###### path_manager bandwidth line
###### path_manager rtt line
line_pathmanager_rtt_num = 165
line_pathmanager_rtt_num2 = 260
line_pathmanager_rtt_num3 = 327

line_pathmanager_bandwidth_num = 166
line_pathmanager_bandwidth_num2 = 261
line_pathmanager_bandwidth_num3 = 328

######  path_manager source file
pathmanager_sourcefile='path_manager.go'
######  path_manager backup source file
pathmanager_bkfile=pathmanager_sourcefile+'_bk'
######  path_manager backup sourcefile
os.system('cp '+pathmanager_sourcefile+' '+pathmanager_bkfile)
######  path_manager tmpfile
pathmanager_tmpfile='tmp_path_manager.go'



######  PROJECT List
PROJECT_LIST = ['mp-quic','quic-go']
######  set bandwidth max & step --> generate bandwidth list (like [1, 25, 50, 75, 100])
fixed_bandwidth = 1
fixed_rtt = 1

max_bandwidth = 100
step_bandwidth = 10
bandwidth_list = []
bandwidth_list.append(1)
for tmp in range(step_bandwidth, max_bandwidth+step_bandwidth, step_bandwidth):
   bandwidth_list.append(tmp)
######  set delay max & step --> generate delay list (like [1, 50, 100, ..., 400])
# max_delay = 400
# step_delay = 40
delay_list = []
delay_list.append(1)
# for tmp in range(step_delay, max_delay+step_delay, step_delay):
#      delay_list.append(tmp)


exam_num = 1

######  start loop
######  change PROJECT in a loop ...
######  change bandwidth in a loop ...
######  change delay in a loop ...
for project in PROJECT_LIST:
    for bandwidth in bandwidth_list:
        for delay in delay_list:

            ###############################  change single-path.py  ############################
            ######  read from sourcefile and write to tmpfile
            fr = open(singlepath_sourcefile,'r')
            fw = open(singlepath_tmpfile,'w+')
            lines = fr.readlines()
            counter = 1
            for line in lines:
                if counter == line_singlepath_PROJECT_num:
                    fw.write('                    PROJECT: \"%s\",     # quic-go is the prioritized stream scheduling project, mp-quic is the original multipath-quic project\n'%project)
                else:
                    if counter == line_singlepath_bandwidth_num:
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
            os.system('cp '+singlepath_tmpfile+' '+singlepath_sourcefile)



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
            repeat_num = 2
            while (repeat_num > 0):
                ###############################  get all http folders before running single-path  ###############################
                before_folder_list = os.listdir('/Users/shixiang/git/minitopo-experiences/experiences')

                ###############################  run single-path  ############################
                os.system('./'+singlepath_sourcefile)
                time.sleep(30)

                ###############################  judge if single-path finishes  ############################
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
                    time.sleep(5)

                ###### make sure quic_client.log and quic_server.log complete
                time.sleep(10)
                repeat_num = repeat_num - 1
