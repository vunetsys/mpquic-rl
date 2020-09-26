import os
import shutil


ROOT_FOLDER = ''
DEST_FOLDER = ''

NAME_FOLDER_SUFFIX = ''

# returns folders not client.log files
def retrieve_clogs_folders(folder):
    subfolders = [ f.path for f in sorted(os.scandir(folder), key=os.path.getmtime) if f.is_dir() ]

    curated_file_list = []
    for s in subfolders:
        if 'https_quic_' in s:
            dir_0 = os.listdir(s)
            for d in dir_0:
                if '0_d' in d:
                    curated_file_list.append(s)
    return curated_file_list



clogs = retrieve_clogs_folders(ROOT_FOLDER)
assert len(clogs) == 200

for i in range(10):

    d_path = DEST_FOLDER + str(i+1) + NAME_FOLDER_SUFFIX
    os.mkdir(d_path)
    
    sub_list = clogs[(i*20):(i*20)+20]
    for s in sub_list:
        shutil.move(s, d_path)
