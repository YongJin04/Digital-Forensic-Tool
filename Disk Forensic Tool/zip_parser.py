import sys
import struct

def end_central_directory(file_path):
    print("\n # End of central directory record")
    
    def find_end_of_central_directory(f, file_size):
        max_end_size = min(65536 + 22, file_size) 
        for i in range(max_end_size, 3, -1):
            f.seek(file_size - i)
            if f.read(4) == b'\x50\x4B\x05\x06':  # Search EOCD Signature (Signature == 0x50 4B 05 06)
                return file_size - i  # Return Offset of EOCD
        return None

    with open(file_path, 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()
        eocd_pos = find_end_of_central_directory(f, file_size)  # Search EOCD Signature
        
        if eocd_pos is not None:
            f.seek(eocd_pos)
            data = f.read(22)
            signature, disk_num, disk_start, num_records_disk, total_records, size_cd, offset_cd, comment_len = struct.unpack('<4sHHHHIIH', data)  # Unpack EOCD Structure
            
            # Print EOCD Information
            print(f'File signature (Magic Number): {" ".join([f"{x:02X}" for x in signature])}')
            print(f'Disk Start Number: {disk_num}')
            print(f'Disk # w/cd: {disk_start}')
            print(f'Disk Entry: {num_records_disk}')
            print(f'Total Entry: {total_records}')
            print(f'Size of Central Directory: {size_cd}')
            print(f'Central Header Offset: {offset_cd}')
            print(f'Comment Length: {comment_len}')

            return offset_cd  # Return Offset of Central Directory

def central_directory(file_path, central_header_offset):
    print("\n # Central Directory")
    with open(file_path, 'rb') as f:
        f.seek(central_header_offset)  # Access Central Directory Area
        
        header_format = '<4sHHHHHIIIHHHHHIIH'  # Unpack Central Directory Structure
        header_size = struct.calcsize(header_format)
        data = f.read(header_size)
        fields = struct.unpack(header_format, data)
        
        # Print Central Directory Information
        print("Central Directory File Header:")
        print(f"File signature (Magic Number): {' '.join([f'{x:02X}' for x in fields[0]])}")
        print(f"Version made by: {fields[1]}")
        print(f"Version needed to extract (minimum): {fields[2]}")
        print(f"Flags: {fields[3]}")
        print(f"Compression method: {fields[4]}")
        print(f"Moditime: {fields[5]}")
        print(f"Modidate: {fields[6]}")
        print(f"CRC-32 CheckSum: {fields[7]}")
        print(f"Compressed Size: {fields[8]}")
        print(f"Uncompressed Size: {fields[9]}")
        print(f"File Name Length: {fields[10]}")
        print(f"Extra Field Length: {fields[11]}")
        print(f"File Comment Length: {fields[12]}")
        print(f"Disk Start Number: {fields[13]}")
        print(f"Internal Attribute: {fields[14]}")
        print(f"External Attribute: {fields[15]}")
        print(f"Local Header: {fields[16]}")

        # Print Filename as long as Possible
        if fields[9] > 0:  # Check Filename is Available
            filename = f.read(fields[9]).decode('utf-8')
            print(f"Filename: {filename}")

        return fields[13]  # Return Offset of File Entry

def file_entry(file_path, file_entry_offset):
    print("\n # Central Directory")
    with open(file_path, 'rb') as f:
        f.seek(file_entry_offset)  # Access File Entry Area
        
        header_format = '<4sHHHHHIIIHH'  # Unpack File Entry Structure
        header_size = struct.calcsize(header_format)
        data = f.read(header_size)
        fields = struct.unpack(header_format, data)
        
        # Print File Entry Information
        print("Central Directory File Header:")
        print(f"File signature (Magic Number): {' '.join([f'{x:02X}' for x in fields[0]])}")
        print(f"Version needed to extract: {fields[1]}")
        print(f"Flags: {fields[2]}")
        print(f"Compression method: {fields[3]}")
        print(f"Moditime: {fields[4]}")
        print(f"Modidate: {fields[5]}")
        print(f"CRC-32 CheckSum: {fields[6]}")
        print(f"Compressed Size: {fields[7]}")
        print(f"Uncompressed Size: {fields[8]}")
        print(f"File Name Length: {fields[9]}")
        print(f"Extra Field Length: {fields[10]}")

        # Print Filename as long as Possible
        if fields[9] > 0:  # Check Filename is Available
            filename = f.read(fields[9]).decode('utf-8')
            print(f"Filename: {filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:  # Get ZIP File Path
        print("Usage: python script.py <zip_file>")
        sys.exit(1)
    else :
        central_header_offset = end_central_directory(sys.argv[1])  # Read End of Central Directory Area
        if central_header_offset is not None:
            file_entry_offset = central_directory(sys.argv[1], central_header_offset)  # Read Central Directory Area
            if file_entry_offset is not None:
                file_entry(sys.argv[1], file_entry_offset)  # Read File Entry Area