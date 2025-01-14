from datetime import datetime, timedelta
import argparse
import struct
import sys
import os

VBR_HEADER_STRUCTURE = '<3s8s5sIHHQIIBBHIQQQ'  # Size : 0x48 / <3s8s5s IHHQ IIBBHI QQ Q
SUPER_BLOCK_STRUCTURE = '<16sQQIIII16s16s16s16sQQ'  # Size : 0x80 / <16s QQ IIII 16s 16s 16s 16s QQ
CHECK_POINT_STRUCTURE = '<IIIIQQ16s16sIIIIIIIIIIIIII'  # Size : 0xC8 / <IIII QQ 16s 16s IIII IIII IIII II
CONTAINER_TABLE_STRUCTURE = '<QQ16s16s16s16s16s16s16s16sQII'  # Size : 0xA0 / <QQ 16s 16s 16s 16s 16s 16s 16s 16s QII
OBJECT_ID_TABLE_KEY_STRUCTURE = '<QQ'  # Size : 0x10 / <QQ
OBJECT_ID_TABLE_VALUE_STRUCTURE = '<IIIIIIII'  # Size : 0x20 / <IIII IIII
PARENT_CHILD_TABLE_STRUCTURE = '<I12sQQQQ'  # Size : 0x30 / <I12s QQ QQ

PAGE_HEADER_STRUCTURE = '<IIIIQQQQQQQQ'  # Size : 0x50 / <IIII QQ QQ QQ QQ
PAGE_REFERENCE_STRUCTURE = '<QQQQHBBHHQ'  # Size : 0x30 / <QQ QQ HBBHHQ

FILE_TABLE_NAME_STRUCTURE = '<HH'  # Size : 0x04 / <I (+ File Name Field)

DIRECTORY_TABLE_NAME_STRUCTURE = '<I'  # Size : 0x04 / <I (+ Directory Name Field)
DIRECTORY_TABLE_METADATA_STRUCTURE = '<QQQQQQ'  # Size : 0x30 / <QQ QQ QQ
STRUCTURE = '<'  # Size : 0x / <

INDEX_ROOT_STRUCTURE = '<IH6sHHH6sQQ'  # Size : 0x28 / <IH6sHH H6sQ Q
INDEX_HEADER_STRUCTURE = '<IIIB3sIIQII'  # Size : 0x28 / <IIIB3s IIQ II
INDEX_KEY_STRUCTURE = '<I'  # Size : 0x04 / <I
INDEX_ENTRY_STRUCTURE = '<IHHHHH'  # Size : 0x0C / <IHHHHH

ATTRIBUTE_HEADER_STRUCTURE = '<BBHIHBB'  # Size : 0x10 / <BBHIHBB
ATTRIBUTE_KEY_STRUCTURE = '<IIBB'  # Size : 0x0C / <IIBB

def read_vbr(image_file, base_cluster):
    image_file.seek(base_cluster)

    vbr_header = read_struct(image_file, VBR_HEADER_STRUCTURE)

    if (vbr_header[9] != 0x03):  # Check File System Version
        sys.exit(f"This ReFS is not 3.x version.\n")

    sector_size = vbr_header[7]
    clusters_per_sector = vbr_header[8]
    container_size = vbr_header[15]
    cluster_size = sector_size * clusters_per_sector

    return sector_size, cluster_size, container_size

def read_super_block(image_file, base_cluster, cluster_size):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x42505553"):  # Compair page header signature "SUPB"
        sys.exit(f"This block is not Super Block.\n")
    
    super_block = read_struct(image_file, SUPER_BLOCK_STRUCTURE)

    return super_block[11]  # Return Primary Check Point Cluster

def read_check_point(image_file, base_cluster, cluster_size):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x504b4843"):  # Compair page header signature "CHKP"
        sys.exit(f"This block is not Check Point.\n")
    
    check_point = read_struct(image_file, CHECK_POINT_STRUCTURE)

    image_file.seek(base_cluster * cluster_size + check_point[9])  # Offset of Object ID Table Page Reference
    object_id_table_page_reference = read_struct(image_file, PAGE_REFERENCE_STRUCTURE)

    image_file.seek(base_cluster * cluster_size + check_point[13])  # Offset of Parent Child Table Page Reference
    parent_child_table_page_reference = read_struct(image_file, PAGE_REFERENCE_STRUCTURE)

    image_file.seek(base_cluster * cluster_size + check_point[16])  # Offset of Container Table Page Reference
    container_table_page_reference = read_struct(image_file, PAGE_REFERENCE_STRUCTURE)

    return object_id_table_page_reference[0], parent_child_table_page_reference[0], container_table_page_reference[0]  # Return Object ID Table Cluster, Parent Child Table LCN, Container Table LCN

def read_container_table(image_file, base_cluster, cluster_size):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x2b42534d"):  # Compair page header signature "MSB+"
        sys.exit(f"This block is not Container Table.\n")
    
    container_table_key_dic = {}
    read_index(image_file, base_cluster, cluster_size, "Container Table", container_table_key_dic, None)

    return container_table_key_dic

def read_object_id_table(image_file, base_cluster, cluster_size, container_table_key_dic):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x2b42534d"):  # Compair page header signature "MSB+"
        sys.exit(f"This block is not Object ID Table.\n")
    
    object_id_table_lcn_dic = {}
    read_index(image_file, base_cluster, cluster_size, "Object ID Table", container_table_key_dic, object_id_table_lcn_dic)

    return object_id_table_lcn_dic

def read_parent_child_table(image_file, base_cluster, cluster_size, container_table_key_dic, object_id_table_lcn_dic):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x2b42534d"):  # Compair page header signature "MSB+"
        sys.exit(f"This block is not Parent Child Table.\n")

    # Declar Parent Child Table Global Dictionary
    global master_directory_tree_dic; master_directory_tree_dic = {}
    
    read_index(image_file, base_cluster, cluster_size, "Parent Child Table", container_table_key_dic, object_id_table_lcn_dic)

def traversing_directory_hierarchy(image_file, base_cluster, cluster_size, container_table_key_dic, object_id_table_lcn_dic):
    # Initial Assignment Value is 0x600 (Root Directory Object ID)
    visit_object_id = 0x600

    # Initial Assignment Value is '.\\' (Root Directory Path)
    global current_work_directory
    current_work_directory = '.' + '\\' + 'Root'
    
    # Stack to Keep Track of Visited Directory (All of object_id)
    directory_stack = [visit_object_id]

    # Clean Up Screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    while True:
        # Convert 'Directory Object ID' -> 'LCN' -> 'VCN'
        visit_object_id_vcn = lcn_to_vcn(cluster_size, container_size, object_id_table_lcn_dic[visit_object_id]["LCN"], container_table_key_dic)

        # Read File and Directory Table Lower of Current Directory Object ID
        lower_file_table_of_current_directory_dic, lower_directory_table_of_current_directory_dic = read_currnet_directory_table(image_file, visit_object_id_vcn, cluster_size, container_table_key_dic, object_id_table_lcn_dic, visit_object_id)

        # Update Lower Directory Table of Current Directory Dictionary Based Parent Child Table Info
        one_level_children = master_directory_tree_dic.get(visit_object_id, [])
        existing_object_ids = {entry['directory_object_id'] for entry in lower_directory_table_of_current_directory_dic.values()}
        for child_object_id, _ in one_level_children:
            if child_object_id not in existing_object_ids:
                new_index = max(lower_directory_table_of_current_directory_dic.keys(), default=0) + 1
                lower_directory_table_of_current_directory_dic[new_index] = {'directory_name': f'Unknown (Object ID :{hex(child_object_id)})', 'directory_object_id': child_object_id, 'last_access_time': 'Unknown'}

        print(f"master_directory_tree_dic : {master_directory_tree_dic}, lower_file_table_of_current_directory_dic : {lower_file_table_of_current_directory_dic}, lower_directory_table_of_current_directory_dic : {lower_directory_table_of_current_directory_dic}")

        # Print File and Directory Table Information Lower of Current Directory Object ID
        for key, value in lower_directory_table_of_current_directory_dic.items():
            print(f"d  {value.get('directory_name')}, {convert_filesystem_time(value.get('last_access_time'))}")
        for key, value in lower_file_table_of_current_directory_dic.items():
            print(f"f {value.get('file_name')}")

        # Input User Directory Name
        directory_name = input(f'\n{current_work_directory}> ')

        # Clean Up Screen
        os.system('cls' if os.name == 'nt' else 'clear')

        if directory_name == "..":
            if len(directory_stack) > 1:
                # Pop the current directory and move to the parent directory
                directory_stack.pop()
                visit_object_id = directory_stack[-1]
                current_work_directory = "\\".join(current_work_directory.split("\\")[:-1]) or ".\\"
            else:
                print("Error: Already at the root directory.\n")
            continue  # Skip further processing for '..'

        # Attempt to find the directory in the current directory's table
        directory_found = False
        for key, value in lower_directory_table_of_current_directory_dic.items():
            if value.get('directory_name') == directory_name:
                directory_stack.append(int(value.get('directory_object_id')))
                visit_object_id = int(value.get('directory_object_id'))
                current_work_directory = current_work_directory + '\\' + str(directory_name)
                directory_found = True
                break
        
        if not directory_found:
            print(f"Error: Directory '{directory_name}' not found.\n")

def read_currnet_directory_table(image_file, base_cluster, cluster_size, container_table_key_dic, object_id_table_lcn_dic, directory_object_id = 0x600):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x2b42534d"):  # Compair page header signature "MSB+"
        if (page_header[11] != directory_object_id):  # Compair page header to Reference Object ID
            sys.exit(f"This is not a table corresponding to the reference Object ID.\n")
        else:
            sys.exit(f"This block is not Table.\n")
    
    # Return Type of Four Variable - | File Name | File LCN | File Object ID | / | Directory Name | Directory Object ID | Directory Last Access Time |
    return read_index(image_file, base_cluster, cluster_size, "Directory Table", container_table_key_dic, object_id_table_lcn_dic)

def read_index(image_file, base_cluster, cluster_size, table_type, container_table_key_dic, object_id_table_lcn_dic):
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE))  # Move to Index Root

    index_root = read_struct(image_file, INDEX_ROOT_STRUCTURE)
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0])  # Move to Index Header

    index_header = read_struct(image_file, INDEX_HEADER_STRUCTURE)
    number_of_entries = index_header[6]
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_header[5])  # Move to Index Key (+ Index Header)

    lower_file_table_of_current_directory = {}
    lower_directory_table_of_current_directory = {}
    for key in range(number_of_entries):
        image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_header[5] + (key * 0x04))  # Move to Each Index Key Entry (+ Index Header, Index Key)

        index_key = (read_struct(image_file, INDEX_KEY_STRUCTURE)[0] & 0xFFFF)  # Return Lower 2 Byte
        image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key)  # Move to Index Entry (+ Index Header)
        
        index_entry = read_struct(image_file, INDEX_ENTRY_STRUCTURE)
        
        # Compair Current Table Type
        if (table_type == "Container Table"):  # Table Type is Container Table
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)

            page_reference = read_struct(image_file, PAGE_REFERENCE_STRUCTURE)
            read_index(image_file, page_reference[0], cluster_size, "Container Table Key-Value", container_table_key_dic, None)
    
        elif (table_type == "Container Table Key-Value"):  # Table Type is Container Table Key-Value
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)
            container_table = read_struct(image_file, CONTAINER_TABLE_STRUCTURE)

            container_table_key_dic[container_table[0]] = {  # Entry Key
                "number_of_start_cluster": container_table[10]  # Number of Start Cluster
            }

        elif (table_type == "Object ID Table"):  # Table Type is Object ID Table
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Key (+ Index Header, Index Entry)
            object_id_table_key = read_struct(image_file, OBJECT_ID_TABLE_KEY_STRUCTURE)
            
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)
            object_id_table_value = read_struct(image_file, OBJECT_ID_TABLE_VALUE_STRUCTURE)  # Jump to Index Entry's Page Reference Area
            page_reference = read_struct(image_file, PAGE_REFERENCE_STRUCTURE)
        
            object_id_table_lcn_dic[object_id_table_key[1]] = {  # Object ID of Object ID Table Entry
                "LCN": page_reference[0]  # LCN of Object ID Table Entry
            }
        
        elif (table_type == "Parent Child Table"):  # Table Type is Parent Child Table
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key)  # Move to Index Entry (+ Index Header)
            parent_child_table_key = read_struct(image_file, PARENT_CHILD_TABLE_STRUCTURE)

            parent_directory_object_id = parent_child_table_key[3]
            child_directory_object_id = parent_child_table_key[5]
            
            # Convert Object ID to LCN form Object ID Table LCN Dictionary
            parent_directory_lcn = int(object_id_table_lcn_dic[parent_directory_object_id]["LCN"])
            child_directory_lcn = int(object_id_table_lcn_dic[child_directory_object_id]["LCN"])

            # Convert LCN to VCN
            parent_directory_vcn = lcn_to_vcn(cluster_size, container_size, parent_directory_lcn, container_table_key_dic)
            child_directory_vcn = lcn_to_vcn(cluster_size, container_size, child_directory_lcn, container_table_key_dic)

            # Save Root Directory VCN
            if (int(parent_directory_object_id) == 0x600):
                global root_vcn; root_vcn = parent_directory_vcn

            # Save Parent Child Table Dictionary
            if int(parent_directory_object_id) not in master_directory_tree_dic:
                master_directory_tree_dic[int(parent_directory_object_id)] = []
            master_directory_tree_dic[int(parent_directory_object_id)].append((int(child_directory_object_id), int(child_directory_vcn)))

        elif (table_type == "Directory Table"):  # Table Type is Directory Table
            image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Value (+ Index Header, Index Entry)
            index_entry_key = read_struct(image_file, INDEX_KEY_STRUCTURE)

            if (index_entry_key[0] == 0x10030):  # This Index Entry is 'File Table'
                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Key (+ Index Header, Index Entry)
                index_entry_key = read_struct(image_file, FILE_TABLE_NAME_STRUCTURE, int(index_entry[2]))

                # 여기에 File에 대한 세부 Metadata 읽는 로직을 추가해야함.

                # Return Type of Four Variable - | File Name | File LCN | File Object ID |
                lower_file_table_of_current_directory[key] = {'file_name': index_entry_key[2].replace('\x00', '')}

            elif (index_entry_key[0] == 0x20030):  # This Index Entry is 'Directory Table'
                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Key (+ Index Header, Index Entry)
                index_entry_key = read_struct(image_file, DIRECTORY_TABLE_NAME_STRUCTURE, int(index_entry[2]))

                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)
                index_entry_value = read_struct(image_file, DIRECTORY_TABLE_METADATA_STRUCTURE)

                # Return Type of Four Variable - | Directory Name | Directory Object ID | Directory Last Access Time |
                lower_directory_table_of_current_directory[key] = {'directory_name': index_entry_key[1].replace('\x00', ''), 'directory_object_id': index_entry_value[1], 'last_access_time': index_entry_value[5]}
    
    # Return Type of Four Variable - | File Name | File LCN | File Object ID | / | Directory Name | Directory Object ID | Directory Last Access Time |
    return lower_file_table_of_current_directory, lower_directory_table_of_current_directory

def lcn_to_vcn(cluster_size, container_size, lcn, container_table_key_dic):
    clusters_per_container = int(container_size / cluster_size)  # CPC = Clusters Per Container

    clusters_per_container_shift = 0  # CPC Shift = Right shift CPC until it equals 1
    clusters_per_container_temp = clusters_per_container
    while clusters_per_container_temp > 1:
        clusters_per_container_temp >>= 1
        clusters_per_container_shift += 1
    
    entry_key = lcn >> (clusters_per_container_shift + 1)  # Entry Key = Right shift LCN with 'CPC + 1'
    
    # Computed Entry Key Does Not Exist in Container Table Key Dictionary
    if entry_key not in container_table_key_dic:
        sys.exit(f"Entry key '{entry_key}' does not exist in Container Table Key Dictionary.\n")

    return container_table_key_dic[entry_key]['number_of_start_cluster'] + (lcn & (clusters_per_container - 0x01)) # VCN = (Start Cluster) + ((LCN) & (Clusters Per Container - 1))

def read_struct(image_file, structure, read_length=0):
    struct_size = struct.calcsize(structure)
    buffer = image_file.read(struct_size)
    unpacked_data = list(struct.unpack(structure, buffer))

    if structure == FILE_TABLE_NAME_STRUCTURE:
        # Read twice the File Name Length value and decode it using UTF-8
        unpacked_data.append(struct.unpack(f'<{read_length - 0x04}s', image_file.read(read_length - 0x04))[0].decode('utf-8'))
    elif structure == DIRECTORY_TABLE_NAME_STRUCTURE:
        # Read twice the Directory Name Length value and decode it using UTF-8
        unpacked_data.append(struct.unpack(f'<{read_length}s', image_file.read(read_length))[0].decode('utf-8'))
    
    return unpacked_data

def convert_filesystem_time(filetime):
    if (filetime == 'Unknown'):
        return filetime

    FILETIME_EPOCH = datetime(1601, 1, 1)
    seconds_since_epoch = filetime / 10**7
    timestamp_utc = FILETIME_EPOCH + timedelta(seconds=seconds_since_epoch)
    timestamp_kst = timestamp_utc + timedelta(hours=9)

    return timestamp_kst.strftime('%Y-%m-%d %H:%M')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--imagefile", required=True, help="Enter Image File Format By ReFS File System.")
    args = parser.parse_args()

    base_cluster = 0
    with open(args.imagefile, 'rb') as image_file:
        # VBR -> Sector Size, Cluster Size, Container Size
        sector_size, cluster_size, container_size = read_vbr(image_file, base_cluster)
        
        super_block_cluster = 0x1E
        # Super Block -> Check Point Cluster
        check_point_cluster = read_super_block(image_file, super_block_cluster, cluster_size)

        # Check Point -> Object ID Table Cluster, Parent Child Table LCN, Container Table LCN
        object_id_table_lcn, parent_child_table_lcn, container_table_vcn = read_check_point(image_file, check_point_cluster, cluster_size)
        
        # Container Table -> Create Container Table Key Dictionary
        container_table_key_dic = read_container_table(image_file, container_table_vcn, cluster_size)
        # for key, value in container_table_key_dic.items():
            # print(f"Key: {hex(key)}, Number of Start Cluster: {hex(value["number_of_start_cluster"])}")

        # Object ID Table -> Object ID Table Object ID Dictionary
        object_id_table_vcn = lcn_to_vcn(cluster_size, container_size, object_id_table_lcn, container_table_key_dic)
        object_id_table_lcn_dic = read_object_id_table(image_file, object_id_table_vcn, cluster_size, container_table_key_dic)
        # for key, value in object_id_table_lcn_dic.items():
            # print(f"Key: {hex(key)}, LCN: {hex(value["LCN"])}")
        
        # Parent Child Table -> Itinerate Parent Child Table -> Create All of Directory Tree in File System.
        parent_child_table_vcn = lcn_to_vcn(cluster_size, container_size, parent_child_table_lcn, container_table_key_dic)
        read_parent_child_table(image_file, parent_child_table_vcn, cluster_size, container_table_key_dic, object_id_table_lcn_dic)

        # Read Directory Tree in File System based on User Input.
        traversing_directory_hierarchy(image_file, base_cluster, cluster_size, container_table_key_dic, object_id_table_lcn_dic)
