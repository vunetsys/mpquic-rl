'''
    TODO: Fill this comment
'''
import os



def retrieve_clogs():
    QUIC_PREFIX = 'quic' + '/' + '1'
    CLIENT_FILE = 'quic_client.log'
    folder = './'
    subfolders = [ f.path for f in os.scandir(folder) if f.is_dir() ]

    curated_file_list = []
    for s in subfolders:
        if 'https_quic_' in s:
            dir_0 = os.listdir(s)
            for d in dir_0:
                if '0_d' in d:
                    fp = s + '/' + d + '/' + QUIC_PREFIX + '/' + CLIENT_FILE
                    if os.path.isfile(fp):
                        curated_file_list.append(fp)
    return curated_file_list


def main():
    client_logs = retrieve_clogs()
    assert len(client_logs) == 100

if __name__ == "__main__":
    main()