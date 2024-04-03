import struct
import sys

def partition_parser(file_path, boot_code_size, sector_size):
    with open(file_path, 'rb') as f:
        f.seek(boot_code_size, whence = 0)  # Jump Boot Code Area

        partition_table_format = '<B3sB3sII'  # Format of Partition Table Entry
        partition_table_size = struct.calcsize(partition_table_format)

        number_of_partition = 1
        current_sector = 0
        while(True):
            partition_data = f.read(partition_table_size)

            if partition_data == bytes([0] * partition_table_size): return  # Empty Partition Table Entry

            fields = struct.unpack(partition_table_format, partition_data)
            print_partition_data(number_of_partition, fields, current_sector, sector_size)

            if (fields[2] == 0x05):
                number_of_partition += 1
                f.seek(int(fields[4]) * sector_size + boot_code_size, whence = 0)
                current_sector = int(fields[4])
                continue

            number_of_partition += 1

def print_partition_data(number_of_partition, fields, current_sector, sector_size):
    print(f"\n========== Partition {number_of_partition} ==========")
    print(f"Boot Flag : {True if fields[0] == 0x80 else False} ")
    print(f"Starting CHS Address : {''.join(f'{byte:02x}' for byte in fields[1])}")  # Print Hex Value & Continuous
    print(f"Partition Type : {fields[2]:02x} ({partition_type(fields[2])})")
    print(f"Ending CHS Address : {''.join(f'{byte:02x}' for byte in fields[3])}")
    print(f"Starting LBA : {current_sector * sector_size + int(fields[4])}")
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

if __name__ == "__main__":
    sector_size = 512  # Define Sector Size (512 Byte)
    boot_code_size = 446  # Define Boot Code Size (446 Byte)

    if '-f' in sys.argv:
        file_path_index = sys.argv.index('-f') + 1   # Find index of '-f'
        if file_path_index < len(sys.argv):
            partition_parser(sys.argv[file_path_index], boot_code_size, sector_size)
    else:
        print("Command : python 'MBR_parser.py' -f 'Image File Path'")
        sys.exit(1)
