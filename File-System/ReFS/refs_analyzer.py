import argparse
import struct
import sys

VBR_HEADER_STRUCTURE = '<3s8s5sIHHQIIBBHIQQQ'  # Size : 0x48 / <3s8s5s IHHQ IIBBHI QQ Q
SUPER_BLOCK_STRUCTURE = '<16sQQIIII16s16s16s16sQQ'  # Size : 0x80 / <16s QQ IIII 16s 16s 16s 16s QQ
CHECK_POINT_STRUCTURE = '<IIIIQQ16s16sIIIIIIIIIIIIII'  # Size : 0xC8 / <IIII QQ 16s 16s IIII IIII IIII II
CONTAINER_TABLE_STRUCTURE = '<QQ16s16s16s16s16s16s16s16sQII'  # Size : 0xA0 / <QQ 16s 16s 16s 16s 16s 16s 16s 16s QII
OBJECT_ID_TABLE_KEY_STRUCTURE = '<QQ'  # Size : 0x10 / <QQ
OBJECT_ID_TABLE_VALUE_STRUCTURE = '<IIIIIIII'  # Size : 0x20 / <IIII IIII
PARENT_CHILD_TABLE_STRUCTURE = '<I12sQQQQ'  # Size : 0x30 / <I12s QQ QQ

PAGE_HEADER_STRUCTURE = '<IIIIQQQQQQQQ'  # Size : 0x50 / <IIII QQ QQ QQ QQ
PAGE_REFERENCE_STRUCTURE = '<QQQQHBBHHQ'  # Size : 0x30 / <QQ QQ HBBHHQ

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
    
    read_index(image_file, base_cluster, cluster_size, "Parent Child Table", container_table_key_dic, object_id_table_lcn_dic)

def read_index(image_file, base_cluster, cluster_size, table_type, container_table_key_dic, object_id_table_lcn_dic):
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE))  # Move to Index Root

    index_root = read_struct(image_file, INDEX_ROOT_STRUCTURE)
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0])  # Move to Index Header

    index_header = read_struct(image_file, INDEX_HEADER_STRUCTURE)
    number_of_entries = index_header[6]
    image_file.seek(base_cluster * cluster_size + struct.calcsize(PAGE_HEADER_STRUCTURE) + index_root[0] + index_header[5])  # Move to Index Key (+ Index Header)

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

            print(f"Parent Directory Object ID / VCN : {hex(parent_directory_object_id)} / {hex(parent_directory_vcn)}\nChild Directory Object ID / VCN : {hex(child_directory_object_id)} / {hex(child_directory_vcn)}\n")

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

def read_struct(image_file, structure):
    struct_size = struct.calcsize(structure)
    buffer = image_file.read(struct_size)
    unpacked_data = struct.unpack(structure, buffer)

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
        
    # Parent Child Table -> Itinerate Parent Child Table -> Create Directory Tree with Directory and File Metadata.
        parent_child_table_vcn = lcn_to_vcn(cluster_size, container_size, parent_child_table_lcn, container_table_key_dic)
        read_parent_child_table(image_file, parent_child_table_vcn, cluster_size, container_table_key_dic, object_id_table_lcn_dic)
