import struct
import sys

def MBR_partition_parser(file_path, boot_code_size, sector_size):
    with open(file_path, 'rb') as f:
        f.seek(boot_code_size, 0)  # Jump Partition Table Area

        partition_table_format = '<B3sB3sII'  # Format of Partition Table Entry
        partition_table_size = struct.calcsize(partition_table_format)

        number_of_partition = 1
        current_sector = 0
        while(True):
            partition_data = f.read(partition_table_size)

            if partition_data == bytes([0] * partition_table_size): return  # Empty Partition Table Entry

            fields = struct.unpack(partition_table_format, partition_data)
            print_partition_data(number_of_partition, fields, current_sector, sector_size)

            if (fields[2] == 0x07):
                NTFS_parser(file_path, sector_size, current_sector + int(fields[4]))
            elif (fields[2] in (0x0B, 0x0C)):
                FAT32_parser(file_path, sector_size, int(fields[4]))
            elif (fields[2] == 0x05):
                number_of_partition += 1
                current_sector += int(fields[4])
                f.seek(current_sector * sector_size + boot_code_size, 0)
                continue

            number_of_partition += 1

def print_partition_data(number_of_partition, fields, current_sector, sector_size):
    print(f"\n\n\n========== Partition {number_of_partition} ==========")
    print(f"Boot Flag : {True if fields[0] == 0x80 else False} ")
    print(f"Starting CHS Address : {''.join(f'{byte:02x}' for byte in fields[1])} (Hex Little Endian)")  # Print Hex Value & Continuous
    print(f"Partition Type : {fields[2]:02x} ({partition_type(fields[2])})")
    print(f"Ending CHS Address : {''.join(f'{byte:02x}' for byte in fields[3])} (Hex Little Endian)")
    print(f"Starting LBA : {current_sector + int(fields[4])}")
    print(f"Size in Sector : {fields[5]}")

def partition_type(value):
    if value == 0x07:
        file_system = "NTFS"  # Suppose NTFS
    elif value in (0x0B, 0x0C):
        file_system = "FAT32"
    elif value == 0x05:
        file_system = "Extended Partition"
    else:
        file_system = "Unknown"

    return file_system

def NTFS_parser(file_path, sector_size, current_sector):
    with open(file_path, 'rb') as f1:
        # Print NTFS BPB 
        f1.seek(current_sector * sector_size, 0)  # Jump NTFS Area

        NTFS_BPB_format = '<3s8sHB26sQQQ'  # Format of NTFS BPB 
        NTFS_BPB_size = struct.calcsize(NTFS_BPB_format)
        NTFS_data = f1.read(NTFS_BPB_size)

        fields = struct.unpack(NTFS_BPB_format, NTFS_data)

        print("\n========= NTFS File System =========")
        print(f"Jump Boot Code : {' '.join(f'{byte:02x}' for byte in fields[0])} (Hex)")
        print(f"OEM ID : {fields[1]} / {' '.join(f'{byte:02x}' for byte in fields[1])} (String / Hex)")  # Print Hex Value & Continuous
        print(f"Bytes Per Sector : {fields[2]}")
        print(f"Sectors per Cluster : {fields[3]}")
        print(f"Total Sector Count : {fields[5]}")
        print(f"Starting for $MFT : {int(current_sector / int(fields[3])) + int(fields[6])} / {current_sector + (int(fields[6]) * int(fields[3]))} (Cluster / Sector)")
        print(f"Starting for $MFTMirr : {int(current_sector / int(fields[3])) + int(fields[7])} / {current_sector + (int(fields[7]) * int(fields[3]))} (Cluster / Sector)")

def FAT32_parser(file_path, sector_size, current_sector):
    with open(file_path, 'rb') as f2:
        # Print FAT32 BPB 
        f2.seek(current_sector * sector_size, 0)  # Jump FTA32 Area

        FAT32_BPB_format = '<3s8sHBH8sH6sI8sI'  # Format of FAT32 BPB 
        FAT32_BPB_size = struct.calcsize(FAT32_BPB_format)
        FAT32_data = f2.read(FAT32_BPB_size)

        fields = struct.unpack(FAT32_BPB_format, FAT32_data)

        print("\n========= FAT32 File System =========")
        print("# Reserved Area")
        print(f"Jump Boot Code : {' '.join(f'{byte:02x}' for byte in fields[0])} (Hex)")
        print(f"OEM ID : {fields[1]} / {' '.join(f'{byte:02x}' for byte in fields[1])} (String / Hex)")  # Print Hex Value & Continuous
        print(f"Bytes Per Sector : {fields[2]}")
        print(f"Sectors per Cluster : {fields[3]}")
        print(f"Reserved Sector Count : ")
        print(f"Sectors per Track")
        print(f"Total Sector Count : {fields[5]}")
        print(f"Root Directory Offset : (Cluster)")
        
        # Print FAT32 FSINFO 
        f2.seek((current_sector + 1) * sector_size, 0)  # Jump FTA32 FSINFO Area
        
        FAT32_FSINFO_format = '<4s480s4sII'  # Format of FAT32 FSINFO 
        FAT32_FSINFO_size = struct.calcsize(FAT32_FSINFO_format)
        FAT32_data = f2.read(FAT32_FSINFO_size)

        fields = struct.unpack(FAT32_FSINFO_format, FAT32_data)

        print("\n# Reserved Area")
        print(f"Signature : {fields[0]} (String)")
        print(f"Signature : {fields[2]} (String)")
        print(f"Num of Free Cluster : {fields[3]}")
        print(f"Next Free Cluster : {fields[4]}")

        # Print FAT32 FAT Area 
        f2.seek((current_sector + 1) * sector_size, 0)  # Jump FTA32 FAT Aera

        FAT32_FAT_format = '<'  # Format of FAT32 FAT Area 
        FAT32_FAT_size = struct.calcsize(FAT32_FAT_format)
        FAT32_data = f2.read(FAT32_FAT_size)

        fields = struct.unpack(FAT32_FAT_format, FAT32_data)
        
        print("\n# FAT Area")
        
        
if __name__ == "__main__":
    sector_size = 512  # Define Sector Size (512 Byte)
    boot_code_size = 446  # Define Boot Code Size (446 Byte)

    if '-f' in sys.argv:
        file_path_index = sys.argv.index('-f') + 1   # Find index of '-f'
        if file_path_index < len(sys.argv):
            MBR_partition_parser(sys.argv[file_path_index], boot_code_size, sector_size)
    else:
        print("Command : python 'MBR_parser.py' -f 'Image File Path'")
        sys.exit(1)
