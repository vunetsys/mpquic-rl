# Some useful operations on data we need for our training

def allUnique(x, debug=False):
    '''
        Simplest way to check if all items in a list are unique
        with early exit
    '''
    # return len(x) == len(set(x))
    if debug:
        seen = set()
        for i in x:
            if i in seen:
                print("Not unique: {}".format(i))
            else:
                seen.add(i)
        print ("allUnique len(x) = {} and len(seen) = {}".format(len(x), len(seen)))
        return len(x) == len(seen)

    seen = set()
    return not any(i in seen or seen.add(i) for i in x)



def getTrainingVariables(request):
    '''
        Return all necessary state/training variables from the request
        They might come in random order so rotate them
    '''
    if request['Path1']['PathID'] == 1:
        return request['Path1']['SmoothedRTT'], request['Path1']['Bandwidth'], request['Path1']['Packets'], \
            request['Path1']['Retransmissions'], request['Path1']['Losses'], \
            request['Path2']['SmoothedRTT'], request['Path2']['Bandwidth'], request['Path2']['Packets'], \
            request['Path2']['Retransmissions'], request['Path2']['Losses']
    else:
        return request['Path2']['SmoothedRTT'], request['Path2']['Bandwidth'], request['Path2']['Packets'], \
            request['Path2']['Retransmissions'], request['Path2']['Losses'], \
            request['Path1']['SmoothedRTT'], request['Path1']['Bandwidth'], request['Path1']['Packets'], \
            request['Path1']['Retransmissions'], request['Path1']['Losses']


def arrangeStateStreamsInfo(states, stream_info):
    '''
        Concurrency in MPQUIC results in slightly different ordering of stream_ids,
        Since we only care about the server side of events (for training and validation)
        We rearrange the stream_info based on the order of states received
        As a matching value we have the request-path (e.g. /index.html == /index.html)
    '''
    assert (len(states) == len(stream_info))

    for i, state in enumerate(states):
        for j, stream in enumerate(stream_info):
            if stream['Path'] == state['RequestPath']:
                stream['StreamID'] = state['StreamID']
                # reorder streams
                if i != j:
                    stream_info[i], stream_info[j] = stream_info[j], stream_info[i]

    return stream_info