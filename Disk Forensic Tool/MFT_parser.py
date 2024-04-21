import struct
import math
import sys
import os

def partition_parser(filePath, dirPath, bootCodeSize, sectorSize):
    with open(filePath, 'rb') as f:
        f.seek(bootCodeSize, 0)  # Move Partition Table Area

        numberOfPartition = 0
        currentSector = 0

        partitionTableEntryFormat = '<B3sB3sII'  # Format of Partition Table Entry

        while True:
            fieldSize, fieldData, fields = read_struct(f, partitionTableEntryFormat)

            if fieldData == bytes([0] * fieldSize): break  # Empty Partition Table Entry
            else:
                numberOfPartition += 1

                match fields[2]:
                    case 0x05:  # Partition Type : Extended Partition
                        # print(f"\nPartition {numberOfPartition} : Extended System")
                        currentSector += int(fields[4])  # Update Next Partition Sector
                        f.seek(currentSector * sectorSize + bootCodeSize, 0)  # Move Next Partition Table Entry
                        pass
                    case 0x07:  # Partition Type : NTFS File System
                        print(f"\n\n\nPartition {numberOfPartition} : NTFS File System")
                        NTFS_BPB_parser(filePath, dirPath, currentSector + int(fields[4]), sectorSize)
                        pass
                    case 0x0B | 0x0C:  # Partition Type : FAT32 File System
                        # print(f"\nPartition {numberOfPartition} : FAT32 File System")
                        pass  # 추가적인 로직이 필요하면 여기에 추가하세요.



def NTFS_BPB_parser(filePath, dirPath, currentSector, sectorSize):
    with open(filePath, 'rb') as f1:
        f1.seek(currentSector * sectorSize, 0)  # Move NTFS VBR Area

        NTFSBPBFormat = '<3s8sHBH5sB10s8sQQQB3sB3sQ4s'  # Format of NTFS BPB '<3s8sHBH / 5sB10s / 8sQ / QQ / B3sB3sQ / 4s'
        _, _, NTFSBPBFields = read_struct(f1, NTFSBPBFormat)

        SPC = int(NTFSBPBFields[3])  # Sector Per Cluster
        clusterOfMFT = int(NTFSBPBFields[10])  # Start Cluster of MFT Area
        sectorOfMFT = currentSector + (clusterOfMFT * SPC)  # Start Sector of MFT Area

        MTF_parser(filePath, dirPath, sectorOfMFT, currentSector, sectorSize, SPC)



def MTF_parser(filePath, dirPath, sectorOfMFT, currentSector, sectorSize, SPC):
    with open(filePath, 'rb') as f:
        f.seek(sectorOfMFT * sectorSize, 0)  # Move MFT Area
        
        f.seek(320, 1)  # Read $MFT Entry's Data Length
        runLengthLength, runOffsetLength = read_runlist(int.from_bytes(f.read(1), byteorder='little'))
        dataLength = int.from_bytes(f.read(runLengthLength), byteorder='little')
        f.seek(1024 - (320 + runLengthLength + 1), 1)

        for i in range(2, (dataLength * 4)):  # Read MFT Entry by First MFT Entry($MFT)'s Data Length

            # MFT Entry Header
            MFTHeaderFormat = '<4sHHQHHHHIIQHHI'  # Format of MFT Entry Header '<4sHHQ / HHHHII / QHHI'
            MFTHeaderSize, _, MFTHeaderFields = read_struct(f, MFTHeaderFormat)

            if ((MFTHeaderFields[0] == b"FILE") and (MFTHeaderFields[7] == 0x00)):  # MFT Entry Signature : FILE / MFT Entry Flag : Deleted File
                print(f"\nDeletion MFT Entry Number : {MFTHeaderFields[13]}")

                fileName = ''
                fileData = bytes()
                sizeOfRemainMFTEntry = MFTHeaderFields[6]

                f.seek(int(MFTHeaderFields[6]) - MFTHeaderSize, 1)  # Move Attribute Area (Move Size = Offset of Attribute Area - Common Attribute Header Size)

                # Attribute Area
                while(True):
                    # Common Attribute Header
                    commonAttributeFormat = '<IIBBHHH'  # Format of Common Attribute Header
                    commonAttributeSize, _, commonAttributeFields = read_struct(f, commonAttributeFormat)

                    if (commonAttributeFields[0] == 0xFFFFFFFF):  # End Point of All Attribute Content
                            f.seek(MFTHeaderFields[9] - sizeOfRemainMFTEntry - commonAttributeSize, 1)  # Move Next MFT Entry (Move Size = MFT Entry Size - (Used MFT Entry Size - Common Attrinbute Header Size))
                            break
                    else:
                        sizeOfRemainMFTEntry += commonAttributeFields[1]

                        match commonAttributeFields[0]:
                            case 0x30:  # Attribute Content Type : $FILE_NAME (0x30)
                                if (commonAttributeFields[2] == 0x00):  # Resident Attribute Header
                                    residentAttributeFormat = '<IHBB8s'  # Format of Resident Attribute '<QQ / QQ / QQ / QII / B'
                                    _, _, residentAttributeFields = read_struct(f, residentAttributeFormat)
                                    f.seek(-(0x20 - residentAttributeFields[1]), 1)  # Resident Attribute Header의 크기가 0x08이면 다시 0x08 뒤로 이동, 0x10이면 이동하지 않음 -> 그래야 Attribute 영역임

                                    filenameAttributeFormat = '<QQQQQQQIIH'  # Format of $FILE_NAME Attribute '<QQ / QQ / QQ / QII / B'
                                    _, _, filenameAttributeFields = read_struct(f, filenameAttributeFormat)
                                    fileName = (f.read(int(filenameAttributeFields[9]) * 2)).decode('utf-16le')
                                                                
                                    fileNameRemain = round_up((int(filenameAttributeFields[9]) * 2) + 2) - ((int(filenameAttributeFields[9]) * 2) + 2)  # 남은 파일 이름 영역 계산
                                    f.seek((fileNameRemain), 1)  # 남은 파일 이름 영역 이동 / Move Next Attribute Content
                                else:
                                    print(f"Number of MFT : {MFTHeaderFields[13]} \n Error : Common Attrinute Header Flag is '0x01' Value.")
                                    quit(1)
                                pass
                                
                            case 0x80:  # Attribute Content Type : $DATA (0x80)
                                if (commonAttributeFields[2] == 0x00):  # Resident Attribute Header
                                    residentAttributeFormat = '<IHBB8s'  # Format of Resident Attribute '<QQ / QQ / QQ / QII / B'
                                    _, _, residentAttributeFields = read_struct(f, residentAttributeFormat)
                                    f.seek(-(0x20 - residentAttributeFields[1]), 1)  # Resident Attribute Header의 크기가 0x08이면 다시 0x08 뒤로 이동, 0x10이면 이동하지 않음 -> 그래야 Attribute 영역임

                                    fileData = f.read(int(residentAttributeFields[0]))

                                    file_recovery(dirPath, fileName, fileData)  # Recover Deleted File

                                    f.seek((round_up(residentAttributeFields[0]) - residentAttributeFields[0]), 1)  # Move Next Attribute

                                elif (commonAttributeFields[2] == 0x01):  # Non Resident Attribute Header
                                    nonResidentAttributeFormat = '<QQHH4sQQQQ'  # Format of Non Resident Attribute'<QQ / HH4sQ / QQ / Q'
                                    _, _, nonResidentAttributeFields = read_struct(f, nonResidentAttributeFormat)
                                    f.seek(-(0x48 - nonResidentAttributeFields[2]), 1)  # Resident Attribute Header의 크기가 0x08이면 다시 0x08 뒤로 이동, 0x10이면 이동하지 않음 -> 그래야 Attribute 영역임

                                    contentSize = 0
                                    while(True):
                                        _, _, runListFields = read_struct(f, '<B')

                                        if ((runListFields[0] == 0xFF) or (runListFields[0] == 0x00)):  # 운이 좋게 딱끝난 경우 / 공간이 남게 끝난 경우, 이후의 Attribute가 존재할 수 있으므로, 하위 4bit 즉 RunLength가 0x00이면 다음으로 넘어감
                                            f.seek(round_up(contentSize) - (contentSize) - 1, 1)  # Move Next Attribute ('<B'로 1바이트 읽은 거 때문에 1 더 뺌)
                                               
                                            file_recovery(dirPath, fileName, fileData)  # Recover Deleted File
                                            break
                                        else:
                                            runLengthLength, runOffsetLength = read_runlist(runListFields[0])

                                            contentSize += runLengthLength + runOffsetLength + 1

                                            dataLength = int.from_bytes(f.read(runLengthLength), byteorder ='little')
                                            dataOffset = int.from_bytes(f.read(runOffsetLength), byteorder ='little')

                                            fileData += extract_file_data(filePath, currentSector, dataLength, dataOffset, sectorSize, SPC)  # Extract Deleted File Data
                                
                                pass

                            case _:  # Not Importnat Attribute Content Type
                                f.seek(commonAttributeFields[1] - commonAttributeSize, 1)  # Move Next Attribute Content (Move Size = Current Attribute Content Size - Common Attribute Header Size)
                                pass

            else:
                f.seek(0x400 - MFTHeaderSize, 1)  # Move Next MFT Entry (Move Size = MFT Entry Size - MFT Entry Header Size)



def read_struct(f, fieldFormat):
    fieldSize = struct.calcsize(fieldFormat)  # Calculate Format Size
    fieldData = f.read(fieldSize)  # Read Field Data
    return fieldSize, fieldData, struct.unpack(fieldFormat, fieldData)



def read_runlist(byte):
    runOffsetLength = (byte >> 4) & 0x0F  # Extract Top 4 bits
    runLengthLength = byte & 0x0F  # Extract Lower 4 bits
    return runLengthLength, runOffsetLength



def round_up(x):
    return math.ceil(x / 8) * 8



def extract_file_data(filePath, partitionSector, dataLength, dataOffset, sectorSize, SPC):
    with open(filePath, 'rb') as f3:
        f3.seek((partitionSector + dataOffset * SPC) * sectorSize, 0)  # Move File Data Sector

        # print(f"Data Start Offset : {partitionSector + dataOffset * SPC}")
        # print(f"Data Length : {dataLength * SPC}")

        return bytes(f3.read((dataLength * SPC) * sectorSize))  # Read File Data Cluster



def file_recovery(dirPath, fileName, fileData):
    outputFilePath = os.path.join(dirPath, fileName)

    with open(outputFilePath, 'wb') as file:
        file.write(fileData)

    print(f"Recovery '{fileName}' File Data")



if __name__ == "__main__":
    sector_size = 512  # Define Sector Size (512 Byte)
    boot_code_size = 446  # Define Boot Code Size (446 Byte)

    if '-f' in sys.argv:
        input_file_path_index = sys.argv.index('-f') + 1   # Find index of '-f'
        output_dir_path_index = sys.argv.index('-o') + 1   # Find index of '-o'
        if (input_file_path_index < len(sys.argv)) and (output_dir_path_index < len(sys.argv)):
            partition_parser(sys.argv[input_file_path_index], sys.argv[output_dir_path_index], boot_code_size, sector_size)
    else:
        print("Command : python 'NTFS_file_recovery.py' -f 'Image File Path' -o 'Recovery File Directory path'")
        sys.exit(1)
