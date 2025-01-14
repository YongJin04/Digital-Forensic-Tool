# ReFS Analyzer

ReFS Analyzer is a Python-based tool designed for analyzing and navigating file systems based on the Resilient File System (ReFS).
It provides functionality to parse and interpret key data structures in an ReFS-formatted disk image, enabling forensic analysis and data extraction.

## Features

- **VBR Parsing**: Extracts and interprets Volume Boot Record (VBR) information.
- **Super Block Analysis**: Locates and validates the Super Block for ReFS metadata.
- **Check Point Parsing**: Retrieves critical metadata references, such as object tables and container tables.
- **Container Table Parsing**: Decodes and maps container table entries.
- **Object ID Table Analysis**: Maps object IDs to logical cluster numbers (LCNs).
- **Parent-Child Relationship Mapping**: Builds a hierarchical directory tree using parent-child relationships in the ReFS structure.
- **File and Directory Traversal**: Allows interactive navigation through the file and directory structure.
- **Forensic Insights**: Displays file metadata, including logical size, access time, and file signatures.

## Installation

### Prerequisites

- Python 3.8+
- `argparse` module (pre-installed with Python)

### Clone the Repository

```bash
git https://github.com/YongJin04/Digital-Forensic-Tool.git
cd File-System/ReFS
```

## Usage
- There is a test E01 ReFS image file compressed in 7z format.

### Command-line Arguments

- `-f, --imagefile` (required): Path to the ReFS disk image file to analyze.

### Example

```bash
python refs_analyzer.py -f /path/to/refs/imagefile.img
```
![root_1](https://github.com/user-attachments/assets/3b3605b7-7f2b-4baa-b46b-b0c964c2e3d4)

Upon running the script, you can navigate the directory structure interactively. Use the `..` command to move up a directory.

## Key Components

### Data Structures

The tool defines a variety of data structures for parsing ReFS metadata:

- **VBR_HEADER_STRUCTURE**: For reading the Volume Boot Record.
- **SUPER_BLOCK_STRUCTURE**: For locating and validating the Super Block.
- **CHECK_POINT_STRUCTURE**: For extracting metadata references.
- **PAGE_HEADER_STRUCTURE**: For reading and validating page headers.
- **INDEX_ROOT_STRUCTURE**: For processing index roots.

### Functions

- `read_vbr`: Reads and interprets the VBR to determine sector and cluster sizes.
- `read_super_block`: Parses the Super Block to locate the primary checkpoint.
- `read_check_point`: Decodes metadata references from the checkpoint.
- `read_container_table`: Processes the container table for mapping clusters.
- `read_object_id_table`: Maps object IDs to their respective clusters.
- `traversing_directory_hierarchy`: Provides an interactive interface for navigating the directory tree.

### Example Outputs
#### Root Directory

```plaintext
Type Name                       LogicalSize LastWriteTime         Signature (VCN)
---- -------------------------- ----------- -------------------- -------------------
d    $RECYCLE.BIN                              2025-01-14 20:20
d    System Volume Information                 2025-01-14 20:19
d    User Saved Directory                      2025-01-14 20:30
d    Unknown (Object ID :0x520)                Unknown
f    test.py                      4580        2025-01-14 20:19   0x6f706d69 (0x162000)

.\Root>
```
![root_0](https://github.com/user-attachments/assets/6d360728-4ea5-4554-835f-ce96be541aee)

#### Navigating to "User Saved Directory"

```plaintext
Type Name                       LogicalSize LastWriteTime         Signature (VCN)
---- -------------------------- ----------- -------------------- -------------------
d    Test Directory                           2025-01-14 20:30
f    best_of_the_best.png         192977      2025-01-14 20:20   0x474e5089 (0x160c04)
f    df_m@ster.jpg                27427       2025-01-14 20:20   0xe0ffd8ff (0x163600)
f    document.docx                14727       2025-01-14 20:20   0x4034b50 (0x160c00)

.\Root\User Saved Directory>
```
![user_saved_directory_0](https://github.com/user-attachments/assets/6fbfda96-e7cc-486f-9a78-a674110c952a)


#### Navigating to "Test Directory"

```plaintext
Type Name                       LogicalSize LastWriteTime         Signature (VCN)
---- -------------------------- ----------- -------------------- -------------------
f    data_field.pptx              412388      2025-01-14 20:30   0x4034b50 (0x160001)

.\Root\User Saved Directory\Test Directory>
```
![test_directory_0](https://github.com/user-attachments/assets/5176fc61-ede1-4272-aafc-46ba745229ad)


#### $RECYCLE.BIN Directory

```plaintext
Type Name                       LogicalSize LastWriteTime         Signature (VCN)
---- -------------------------- ----------- -------------------- -------------------
d    S-1-5-21-1436322987-1572358248-3682947794-1001        2025-01-14 20:19

.\Root\$RECYCLE.BIN>
```

#### System Volume Information Directory

```plaintext
Type Name                       LogicalSize LastWriteTime         Signature (VCN)
---- -------------------------- ----------- -------------------- -------------------
d    AadRecoveryPasswordDelete               2025-01-14 20:19
d    ClientRecoveryPasswordRotation          2025-01-14 20:19
d    FveDecryptedVolumeFolder                2025-01-14 20:19
f    IndexerVolumeGuid            76         2025-01-14 20:14   0x44007b (0x163200)
f    WPSettings.dat               12         2025-01-14 20:14   0xc (0x160000)

.\Root\System Volume Information>
```

## Output

- **File Metadata**: Displays information about files and directories, including:
  - Type (File/Directory)
  - Name
  - Logical Size
  - Last Write Time
  - File Signature (if applicable)

## Contributing

Contributions are welcome! Please fork the repository and create a pull request for review.

## Disclaimer

This tool is provided "as is" for educational and forensic purposes. The authors are not responsible for any misuse or damage caused by this tool.

## Contact

For questions or suggestions, please reach out to [yj20040813@gachon.ac.kr] or open an issue on GitHub.

---

