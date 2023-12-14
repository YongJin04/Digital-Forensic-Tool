import hashlib
import sys
import argparse

def hash_file(filename, algorithm):
    """ Function to compute the hash of a file """
    hash_obj = hashlib.new(algorithm)
    with open(filename, 'rb') as file:
        while chunk := file.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def main():
    parser = argparse.ArgumentParser(description='File Hash Calculator')
    parser.add_argument('-f', '--file', required=True, help='File to calculate the hash for')
    args = parser.parse_args()

    file_name = args.file

    # Calculate and print the hash values for each algorithm
    print(f"File: {file_name}")
    print(f"SHA-1: {hash_file(file_name, 'sha1')}")
    print(f"SHA-256: {hash_file(file_name, 'sha256')}")
    print(f"MD5: {hash_file(file_name, 'md5')}")

if __name__ == "__main__":
    main()
