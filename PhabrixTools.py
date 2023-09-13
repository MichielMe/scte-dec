from functools import reduce

def print_like_phabrix_ui(dataframe) -> None:
    row = 0
    index = 0

    for entry in dataframe:
        print(row, index, entry)
        index = index + 1
        if index == 20:
            index = 0
            row = row + 20

# phabrix will return the index position of the anc grid as well
# 0x14 (20), 0x28 (40), 0x3c (60) etc. we need to ignore this
def ignore_20th_digit(my_list) -> list:
    #print("3. IGNORE 20TH DIGIT:\n", my_list)
    new_list = []
    index = 1
    for item in my_list:
        #print(index, item)
        if index == 21:
            #print("passed", index, item)
            index = 1
        else:
            new_list.append(item)
            index = index + 1
    return new_list

def phabrix_to_string(my_list) -> str:
    #print("4. PHABRIX TO STRING:\n", my_list)
    line = ""
    '''
    print("1 debug: ", my_list)
    print("2 debug: ", my_list[6:])
    print("3 debug: ", my_list[6:-7])
    '''
    debug_line = "DEBUG: "

    #print_like_phabrix_ui(my_list)

    # ANC Packet:
    # Start sequence 0x000 0x3FF 0x3FF ([0] [1] [2])
    # DID Data Identifier ([3])
    # SDID Secondary Data Identifier ([4])
    # DBN Data Block Number ([5])
    # DC Data Count ([6])
    # UDW <-- we want this data, so we start the list at the sixth element
    # CS Checksum (skipped by [-1])
    
    '''
    print("Start Sequence: ", my_list.pop(0), my_list.pop(0), my_list.pop(0))
    print("Data Identifier (DID): ", my_list.pop(0))
    print("Secondary Data Identifier (SDID): ", my_list.pop(0))
    print("Data Block Number (DBN): ", my_list.pop(0))
    print("Data Count (DC): ", my_list.pop(0))
    print("UDW: ")
    '''
    
    # start from UDW: (we remove the checksum field at the end)
    for item in my_list[7:-1]:
        #print( item, len( item), item[-2:].zfill(2))
        if (len(item) == 5):
            line = line + item[-2:]
        else:
            line = line + item[-1:].zfill(2)
        debug_line = debug_line + "0x" + item[-2:] + " "
    #print (debug_line)
    
    return line

def convert_to_hex(dataframe) -> list:
    #print("2. CONVERT TO HEX:\n", dataframe)
    return [hex(int(hex_data)).zfill(2) for hex_data in dataframe]

def skip_data(data) -> list:
    #print("1. SKIP DATA:\n", data)
    # skip the first 23 numbers, internal to Phabrix, the last 9 also seem irrelevant
    return data[22:-8]

# make helper function to make processing pipeline of data
def compose(*functions):
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

phabrix_preprocessor = compose(skip_data, convert_to_hex, ignore_20th_digit, phabrix_to_string)

