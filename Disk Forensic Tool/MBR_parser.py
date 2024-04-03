import struct
import sys

def primary_partition_parser(file_path):
    with open(file_path, 'rb') as f:
        f.seek(446)

        partition_table_format = '<B3sB3sII'
        partition_table_size = struct.calcsize(partition_table_format)

        for i in range(1, 5):  # 4번 파티션 부터 0x05일 경우 코드 추가
            partition_data = f.read(partition_table_size)

            if partition_data == bytes([0] * partition_table_size): return  # Empty Partition Table

            fields = struct.unpack(partition_table_format, partition_data)
            print_partition_data(i, fields, 0)

            if ((i == 4) and (fields[2] == 0x05)):
                i += 1
                extended_partition_parser(file_path, i, int(fields[4]))

def print_partition_data(i, fields, current_sector):
    print(f"\n========== Partition {i} ==========")
    print(f"Boot Flag : {True if fields[0] == 0x80 else False} ")
    print(f"Starting CHS Address : {''.join(f'{byte:02x}' for byte in fields[1])}")  # Print Hex Value & Continuous
    print(f"Partition Type : {fields[2]:02x} ({partition_type(fields[2])})")
    print(f"Ending CHS Address : {''.join(f'{byte:02x}' for byte in fields[3])}")
    print(f"Starting LBA : {int(fields[4]) + current_sector}")
    print(f"Size in Sector : {fields[5]}")

def partition_type(value):
    if value == 0x07:
        file_system = "NTFS or exFAT"
    elif value in (0x0B, 0x0C):
        file_system = "FAT32"
    elif value == 0x05:
        file_system = "Extended Partition"
    else:
        file_system = "Unknown"

    return file_system

def extended_partition_parser(file_path, i, extended_partition_sector):
    with open(file_path, 'rb') as f:
        f.seek(extended_partition_sector * 512 + 446)
        
        partition_table_format = '<B3sB3sII'
        partition_table_size = struct.calcsize(partition_table_format)

        for j in range(1, 3):
            partition_data = f.read(partition_table_size)

            if partition_data == bytes([0] * partition_table_size): return  # Empty Partition Table

            fields = struct.unpack(partition_table_format, partition_data)
            print_partition_data(i, fields, extended_partition_sector)

            if ((i % 2 == 0) and (fields[2] == 0x05)):  # Non-Exist Extended Partition Table
                i += 1
                extended_partition_parser(file_path, i, int(fields[4]))
            i += 1

if __name__ == "__main__":
    if len(sys.argv) == 2:
        primary_partition_parser(sys.argv[1])
    else:
        print("Argument Error.")
        sys.exit(1)