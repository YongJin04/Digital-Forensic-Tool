import argparse
import struct
import time
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

FILE_TABLE_METADATA_STRUCTURE = '<QQ'  # Size : 0x10 / <QB
FILE_TABLE_NAME_STRUCTURE = '<QB'  # Size : 0x0A / <QQ (+ File Name Field)
STRUCTURE = '<'  # Size : 0x / <

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
    visit_object_id = 0x600
    current_directory_tree_dic = {}
    
    while True:
        # os.system('cls' if os.name == 'nt' else 'clear')

        current_directory_tree_dic = build_current_tree(master_directory_tree_dic, current_directory_tree_dic, visit_object_id)
        
        visit_object_id_lcn = object_id_table_lcn_dic[visit_object_id]["LCN"]
        visit_object_id_vcn = lcn_to_vcn(cluster_size, container_size, visit_object_id_lcn, container_table_key_dic)
        lower_file_table_of_current_directory_dic = read_currnet_directory_table(image_file, visit_object_id_vcn, cluster_size, container_table_key_dic, object_id_table_lcn_dic, visit_object_id)
        
        current_directory_tree_dic = add_file_table_of_current_directory_tree_dic(current_directory_tree_dic, lower_file_table_of_current_directory_dic)
        
        print(f"{lower_file_table_of_current_directory_dic}\n{current_directory_tree_dic}")
        
        print_current_tree(current_directory_tree_dic)
        
        visit_object_id = input(f'\nEnter visited object id (hex) or "exit" to quit : ')
        
        if visit_object_id.lower() == 'exit':
            print(f"\nExiting the program.")
            break
        
        visit_object_id = int(visit_object_id, 16)

def read_currnet_directory_table(image_file, base_cluster, cluster_size, container_table_key_dic, object_id_table_lcn_dic, directory_object_id = 0x600):
    image_file.seek(base_cluster * cluster_size)

    page_header = read_struct(image_file, PAGE_HEADER_STRUCTURE)

    if (hex(page_header[0]) != "0x2b42534d"):  # Compair page header signature "MSB+"
        if (page_header[11] != directory_object_id):  # Compair page header to Reference Object ID
            sys.exit(f"This is not a table corresponding to the reference Object ID.\n")
        else:
            sys.exit(f"This block is not Table.\n")
    
    # Return Type of Four Variable - | File Name | File LCN | File Object ID |
    return read_index(image_file, base_cluster, cluster_size, "Directory Table", container_table_key_dic, object_id_table_lcn_dic)

def read_index(image_file, base_cluster, cluster_size, table_type, container_table_key_dic, object_id_table_lcn_dic):
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE))  # Move to Index Root

    index_root = read_struct(image_file, INDEX_ROOT_STRUCTURE)
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0])  # Move to Index Header

    index_header = read_struct(image_file, INDEX_HEADER_STRUCTURE)
    number_of_entries = index_header[6]
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_header[5])  # Move to Index Key (+ Index Header)

    lower_file_table_of_current_directory = {}
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

            if (index_entry_key[0] == 0x80000020):  # This Index Entry is 'File Table'
                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Key (+ Index Header, Index Entry)
                index_entry_key = read_struct(image_file, FILE_TABLE_METADATA_STRUCTURE)

                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)
                index_entry_value = read_struct(image_file, FILE_TABLE_NAME_STRUCTURE)

                # Return Type of Four Variable - | File Name | File LCN | File Object ID |
                lower_file_table_of_current_directory[key] = {'file_name': index_entry_value[2], 'file_lcn': hex(index_entry_key[1]), 'file_object_id': hex(index_entry_key[1])}

            elif (index_entry_key[0] == 0x20030):  # This Index Entry is 'Directory Table'
                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[1])  # Move to Index Entry Key (+ Index Header, Index Entry)
                index_entry_key = read_struct(image_file, DIRECTORY_TABLE_NAME_STRUCTURE, int(index_entry[2]))

                image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_key + index_entry[4])  # Move to Index Entry Value (+ Index Header, Index Entry)
                index_entry_value = read_struct(image_file, DIRECTORY_TABLE_METADATA_STRUCTURE)
    
    # Return Type of Four Variable - | File Name | File LCN | File Object ID |
    return lower_file_table_of_current_directory

def build_current_tree(master_directory_tree_dic, current_directory_tree_dic, visit_object_id=0x600):
    def in_current_tree(visit_object_id):
        if visit_object_id in current_directory_tree_dic:
            return True
        for child_list in current_directory_tree_dic.values():
            if isinstance(child_list, list) and any(child_directory_object_id == visit_object_id for child_directory_object_id, _, _ in child_list):
                return True
        return False

    def find_path(root_object_id, visit_object_id):
        if root_object_id == visit_object_id:
            return [root_object_id]
        for (child, _) in master_directory_tree_dic.get(root_object_id, []):
            sub = find_path(child, visit_object_id)
            if sub:
                return [root_object_id] + sub
        return None

    if (not visit_object_id) or (visit_object_id == 0x600):
        current_directory_tree_dic.clear()
        if 0x600 in master_directory_tree_dic:
            current_directory_tree_dic[0x600] = [(c, v, False) for (c, v) in master_directory_tree_dic[0x600]]
        current_directory_tree_dic['root_marked'] = True
        return current_directory_tree_dic

    if not in_current_tree(visit_object_id):
        print(f'Enter only the Currently Displayed Object ID Information.\n')

        def find_marked_object_id(current_directory_tree_dic):
            if 'root_marked' in current_directory_tree_dic and current_directory_tree_dic['root_marked']:
                for key, children in current_directory_tree_dic.items():
                    if key == 'root_marked':
                        continue
                    return key

            for key, children in current_directory_tree_dic.items():
                if key == 'root_marked':
                    continue
                for (child_id, vcn, marked) in children:
                    if marked:
                        return child_id

            return None
        
        true_object_id = find_marked_object_id(current_directory_tree_dic)
        current_directory_tree_dic = build_current_tree(master_directory_tree_dic, current_directory_tree_dic, true_object_id)
        return current_directory_tree_dic

    path = find_path(0x600, visit_object_id)
    if not path:
        return current_directory_tree_dic

    new_dic = {}
    for i in range(len(path) - 1):
        node = path[i]
        next_node = path[i+1]
        for (child_id, vcn) in master_directory_tree_dic.get(node, []):
            if child_id == next_node:
                new_dic[node] = [(child_id, vcn, False)]
                break

    last = path[-1]
    new_dic[last] = [(child_id, vcn, False) for (child_id, vcn) in master_directory_tree_dic.get(last, [])]

    if len(path) >= 2:
        parent_of_last = path[-2]
        tmp = []
        for (c, v, marked) in new_dic[parent_of_last]:
            if c == last:
                tmp.append((c, v, True))
            else:
                tmp.append((c, v, False))
        new_dic[parent_of_last] = tmp

    return new_dic

def add_file_table_of_current_directory_tree_dic(current_directory_tree_dic, lower_file_table_of_current_directory_dic):
    if 'root_marked' in current_directory_tree_dic and current_directory_tree_dic['root_marked']:
        if 0x600 not in current_directory_tree_dic:
            current_directory_tree_dic[0x600] = []
        for key, val in lower_file_table_of_current_directory_dic.items():
            file_name = val['file_name']
            file_lcn = val['file_lcn']
            file_object_id = val['file_object_id']
            current_directory_tree_dic[0x600].append((file_name, file_lcn, file_object_id))
    for parent_id, children in list(current_directory_tree_dic.items()):
        if parent_id == 'root_marked':
            continue
        for (child_id, vcn, marked) in children:
            if not isinstance(child_id, int):
                continue
            if marked:
                if child_id in current_directory_tree_dic:
                    for _, val in lower_file_table_of_current_directory_dic.items():
                        file_name = val['file_name']
                        file_lcn = val['file_lcn']
                        file_object_id = val['file_object_id']
                        current_directory_tree_dic[child_id].append((file_name, file_lcn, file_object_id))
                else:
                    current_directory_tree_dic[child_id] = []
                    for _, val in lower_file_table_of_current_directory_dic.items():
                        file_name = val['file_name']
                        file_lcn = val['file_lcn']
                        file_object_id = val['file_object_id']
                        current_directory_tree_dic[child_id].append((file_name, file_lcn, file_object_id))
    return current_directory_tree_dic

def print_current_tree(current_directory_tree_dic):
    def print_tree(dic, node, prefix="", is_last=True):
        children = dic.get(node, [])
        for i, entry in enumerate(children):
            is_last_child = (i == len(children) - 1)
            connector = "└─" if is_last_child else "├─"
            if len(entry) == 3:
                first, second, third = entry
                if isinstance(third, bool):
                    child_id, vcn, marked = first, second, third
                    mark_str = " <-" if marked else ""
                    child_id_str = hex(child_id) if isinstance(child_id, int) else str(child_id)
                    vcn_str = hex(vcn) if isinstance(vcn, int) else str(vcn)
                    print(f"{prefix}{connector} {child_id_str}, {vcn_str}{mark_str}")
                    print_tree(dic, child_id, prefix + ("   " if is_last_child else "│  "), is_last_child)
                else:
                    file_name, file_lcn, file_object_id = first, second, third
                    print(f"{prefix}{connector} {file_name}, {file_lcn}, {file_object_id}")

    if 'root_marked' in current_directory_tree_dic and current_directory_tree_dic['root_marked']:
        print(f"{hex(0x600)}, {hex(root_vcn)} <-")
    else:
        print(f"{hex(0x600)}, {hex(root_vcn)}")
    if 0x600 in current_directory_tree_dic:
        print_tree(current_directory_tree_dic, 0x600)

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
        unpacked_data.append(struct.unpack(f'<{unpacked_data[1] * 0x02}s', image_file.read(unpacked_data[1] * 0x02))[0].decode('utf-8'))
    elif structure == DIRECTORY_TABLE_NAME_STRUCTURE:
        # Read twice the Directory Name Length value and decode it using UTF-8
        unpacked_data.append(struct.unpack(f'<{read_length}s', image_file.read(read_length))[0].decode('utf-8'))
    
    return unpacked_data

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
