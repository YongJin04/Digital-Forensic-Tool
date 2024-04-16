import struct
import sys
import os

def partition_parser(filePath, bootCodeSize, sectorSize):
    with open(filePath, 'rb') as f:
        f.seek(bootCodeSize, 0)  # Move Partition Table Area

        numberOfPartition = 0
        currentSector = 0

        partitionTableEntryFormat = '<B3sB3sII'  # Format of Partition Table Entry

        while(True):
            fieldSize, fieldData, fields = read_struct(f, partitionTableEntryFormat)

            if (fieldData == bytes([0] * fieldSize)): break  # Empty Partition Table Entry
            else:
                numberOfPartition += 1

                match fields[2]:
                    case 0x05:  # Partition Type : Extended Partition
                        # print(f"\nPartition {numberOfPartition} : Extended System")
                        currentSector += int(fields[4])  # Update Next Partition Sector
                        f.seek(currentSector * sectorSize + bootCodeSize, 0)  # Move Next Partition Table Entry
                    case 0x07:  # Partition Type : NTFS File System
                        print(f"\nPartition {numberOfPartition} : NTFS File System")
                        NTFS_parser(filePath, numberOfPartition, currentSector + int(fields[4]), sectorSize)
                    case 0x0B | 0x0C:  # Partition Type : FAT32 File System
                        # print(f"\nPartition {numberOfPartition} : FAT32 File System")

def NTFS_parser(filePath, numberOfPartition, currentSector, sectorSize):
    with open(filePath, 'rb') as f1:
        f1.seek(currentSector * sectorSize, 0)  # Move NTFS VBR Area

        NTFSBPBFormat = '<3s8sHBH5sB10s8sQQQB3sB3sQ4s'  # Format of NTFS BPB '<3s8sHBH / 5sB10s / 8sQ / QQ / B3sB3sQ / 4s'
        fields = read_struct(f1, NTFSBPBFormat)

        SPC = int(fields[3])  # Sector Per Cluster
        clusterOfMFT = int(fields[10])  # Start Cluster of MFT Area
        sectorOfMFT = currentSector + (clusterOfMFT * SPC)  # Start Sector of MFT Area

        MTF_parser(filePath, numberOfPartition, sectorOfMFT, currentSector, sectorSize, SPC)

def MTF_parser(filePath, numberOfPartition, sectorOfMFT, currentSector, sectorSize, SPC):
    with open(filePath, 'rb') as f2:
        f2.seek(sectorOfMFT * sectorSize, 0)  # Move MFT Area

        MFTHeaderFormat = '<4sHHQ / HHHHII / QHHI'  # Format of MFT Entry Header '<4sHHQ / HHHHII / QHHI'
        MFTHeaderfieldSize, MFTHeaderfieldData, MFTHeaderfields = read_struct(f2, MFTHeaderFormat)









        f2.seek(320, 1)  # Read $MFT Entry's Data Length

        run_length, run_offset = split_byte(int.from_bytes(f2.read(1), byteorder='little'))
        data_length = int.from_bytes(f2.read(run_length), byteorder='little')
        # print(f"{data_length}")
        f2.seek(1024 - (320 + run_length + 1), 1)

        for i in range(2, data_length * 4):  # Read MFT Entry by First MFT Entry($MFT)'s Data Length
            MFT_entry_header_format = '<4s18sB33s'  # Format of MFT Entry Header 
            MFT_entry_header_size = struct.calcsize(MFT_entry_header_format)
            MFT_entry_header_data = f2.read(MFT_entry_header_size)

            fields = struct.unpack(MFT_entry_header_format, MFT_entry_header_data)

            # print(f"{fields[0]} {fields[2]}")  # MFT Entry First 4 Byte, MFT Entry Flag

            file_name = ''
            file_data = bytes()  # Recovery File Data
            if (fields[0] == b"FILE" and fields[2] == 0):  # MFT Entry Assignment (FILE), MFT Entry Flag == 0 (Deletion Event)
                print(f"\nDeletion MFT Entry Number : {i}")

                current_MFT_entry_size = MFT_entry_header_size  # 56

                while(True):
                    MFT_attr_header_format = '<II'  # Attribute Type, Attribute Size
                    MFT_attr_header_size = struct.calcsize(MFT_attr_header_format)
                    MFT_attr_header_data = f2.read(MFT_attr_header_size)

                    fields = struct.unpack(MFT_attr_header_format, MFT_attr_header_data)

                    if (file_data != bytes()):  # End Point of MFT Entry
                        next_MFT_entry_size = 1024 - (current_MFT_entry_size + 8)

                        f2.seek(next_MFT_entry_size, 1) # Move Next MFT Entry
                        
                        file_recovery(file_name, dir_path, file_data)  # Recovery Deleted File

                        break

                    current_MFT_entry_size += int(fields[1])
                    if (fields[0] == 0x30):  # File Name Attribute
                        MFT_attr_header_format = '<80sH'  # Format of File Name Attribute
                        MFT_attr_header_size = struct.calcsize(MFT_attr_header_format)
                        MFT_attr_header_data = f2.read(MFT_attr_header_size)

                        fields = struct.unpack(MFT_attr_header_format, MFT_attr_header_data)

                        file_name = (f2.read(int(fields[1]) * 2)).decode('utf-16le')  # Extract File Name (Decode UTF-16le)
                        # print(f"File Name : {file_name}")

                        next_attr_size = round_up_to_eight((int(fields[1]) + 1) * 2) - (int(fields[1]) + 1) * 2  # Move Next Attribute

                        f2.seek(next_attr_size, 1)

                    elif (fields[0] == 0x80):  # File Data Attribute
                        f2.seek(56, 1)  # Move Data Attribute Header (개선 방안 고려하기)

                        while(True):
                            MFT_attr_header_format = '<B'  # Read RunList's First Byte
                            MFT_attr_header_size = struct.calcsize(MFT_attr_header_format)
                            MFT_attr_header_data = f2.read(MFT_attr_header_size)

                            fields = struct.unpack(MFT_attr_header_format, MFT_attr_header_data)

                            if fields[0] == 0x00 or fields[0] == 0xFF:  # End Point of RunList (Non Exist RunList)
                                next_attr_size = round_up_to_eight(runlist_size) - (runlist_size) - 1

                                # print(next_attr_size)

                                f2.seek(next_attr_size, 1)  # Move Next Attribute

                                break
                            else:
                                run_length, run_offset = split_byte(int(fields[0]))  # Decode RunList

                                # print(f"{run_length} {run_offset}")
                                runlist_size = run_length + run_offset + 1

                                data_length = int.from_bytes(f2.read(run_length), byteorder='little')  # RunList Data Length (Cluster)
                                data_offset = int.from_bytes(f2.read(run_offset), byteorder='little')  # RunList Data Offset (Cluster)

                                # print(f"{data_length} {data_offset}")

                                file_data += extract_file_data(file_path, partition_sector, data_length, data_offset, sector_size, SPC)  # Extract Deleted File Data
                    else:
                        f2.seek(int(fields[1]) - 8, 1)  # Move Next Attribute
            else:
                f2.seek(1024 - MFT_entry_header_size, 1)  # Move Next MFT Entry

def read_struct(f, fieldFormat):
    fieldSize = struct.calcsize(fieldFormat)  # Calculate Format Size
    fieldData = f.read(fieldSize)  # Read Field Data
    return fieldSize, fieldData, struct.unpack(fieldFormat, fieldData)

def read_runlist(byte):
    runOffsetLength = (byte >> 4) & 0x0F  # Extract Top 4 bits
    runLengthLength = byte & 0x0F  # Extract Lower 4 bits
    return runOffsetLength, runLengthLength

def round_up_to_eight(x):
    return (int(x / 8) + 1) * 8

def extract_file_data(file_path, partition_sector, data_length, data_offset, sector_size, SPC):
    with open(file_path, 'rb') as f3:
        f3.seek((partition_sector + data_offset * SPC) * sector_size, 0)  # Jump File Data Cluster

        # print(f"Start Offset : {partition_sector + data_offset * SPC}")
        # print(f"Data Length : {data_length * SPC}")

        return bytes(f3.read((data_length * SPC) * sector_size))  # Read File Data Cluster

def file_recovery(file_name, dir_path, file_data):
    output_file_path = os.path.join(dir_path, file_name)

    with open(output_file_path, 'wb') as file:  # Create Deleted File
        file.write(file_data)
    print(f"Recovery '{file_name}' File")

if __name__ == "__main__":
    sector_size = 512  # Define Sector Size (512 Byte)
    boot_code_size = 446  # Define Boot Code Size (446 Byte)

    if '-f' in sys.argv:
        input_file_path_index = sys.argv.index('-f') + 1   # Find index of '-f'
        output_dir_path_index = sys.argv.index('-o') + 1   # Find index of '-o'
        if (input_file_path_index < len(sys.argv)) and (output_dir_path_index < len(sys.argv)):
            partition_parser(sys.argv[input_file_path_index], boot_code_size, sector_size)
    else:
        print("Command : python 'NTFS_file_recovery.py' -f 'Image File Path' -o 'Recovery File Directory path'")
        sys.exit(1)
