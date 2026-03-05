description = [
    {
        "name": "inspect_file",
        "description": "Inspect a file and return a summary of its type, size, "
        "modification time, and a short content preview. Detects whether the "
        "file is tabular (CSV/TSV), Excel, PDF, Word, bioinformatics format, "
        "or image. Does NOT modify the file.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the file to inspect.",
                "default": None,
            }
        ],
        "optional_parameters": [],
    },
    {
        "name": "read_csv_file",
        "description": "Read a CSV or TSV file and return a structured summary "
        "including column names, data types, shape, missing-value counts, "
        "descriptive statistics, and a row preview. Ideal for gene lists, "
        "sample sheets, expression matrices, and other tabular biological data. "
        "The original file is never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the CSV or TSV file.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "delimiter",
                "type": "str",
                "description": "Column delimiter character. Use ',' for CSV (default) or '\\t' for TSV.",
                "default": ",",
            },
            {
                "name": "preview_rows",
                "type": "int",
                "description": "Number of rows to include in the preview.",
                "default": 20,
            },
            {
                "name": "show_stats",
                "type": "bool",
                "description": "Whether to include descriptive statistics for numeric columns.",
                "default": True,
            },
        ],
    },
    {
        "name": "read_excel_file",
        "description": "Read an Excel file (.xls/.xlsx) and return a structured "
        "summary including sheet names, column names, data types, shape, "
        "missing-value counts, descriptive statistics, and a row preview. "
        "The original file is never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the Excel file.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "sheet_name",
                "type": "str",
                "description": "Name of the sheet to read. If not specified, reads the first sheet.",
                "default": None,
            },
            {
                "name": "preview_rows",
                "type": "int",
                "description": "Number of rows to include in the preview.",
                "default": 20,
            },
            {
                "name": "show_stats",
                "type": "bool",
                "description": "Whether to include descriptive statistics.",
                "default": True,
            },
        ],
    },
    {
        "name": "read_pdf_file",
        "description": "Read a PDF file and extract its text content page by page. "
        "Useful for reading research papers, supplementary materials, and "
        "reports. Extracts metadata (title, author, subject) when available. "
        "Optionally extracts tables. The original file is never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the PDF file.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "max_pages",
                "type": "int",
                "description": "Maximum number of pages to read. 0 means read all pages.",
                "default": 0,
            },
            {
                "name": "extract_tables",
                "type": "bool",
                "description": "Whether to attempt table extraction from the PDF.",
                "default": False,
            },
        ],
    },
    {
        "name": "read_docx_file",
        "description": "Read a Word document (.docx) and extract its text content, "
        "including paragraphs and optionally embedded tables. Extracts "
        "document metadata (title, author, subject). The original file is "
        "never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the .docx file.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "include_tables",
                "type": "bool",
                "description": "Whether to extract tables from the document.",
                "default": True,
            },
        ],
    },
    {
        "name": "read_bio_text_file",
        "description": "Read common bioinformatics text files and return a structured "
        "summary. Supports FASTA, FASTQ, VCF, GFF/GTF, BED, SAM, PDB, "
        "GenBank, and other standard biological data formats. Provides "
        "format-specific statistics (e.g., sequence counts, variant counts, "
        "feature types). The original file is never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the bioinformatics text file (e.g., .fasta, .vcf, .gff, .bed, .sam, .pdb, .gbk).",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "max_records",
                "type": "int",
                "description": "Maximum number of records or entries to preview.",
                "default": 50,
            },
        ],
    },
    {
        "name": "read_text_file",
        "description": "Read a plain text file and return its contents. Suitable for "
        "README files, log files, configuration files, and any other "
        "text-based content. The original file is never modified.",
        "required_parameters": [
            {
                "name": "file_path",
                "type": "str",
                "description": "Path to the text file.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "max_lines",
                "type": "int",
                "description": "Maximum number of lines to read from the file.",
                "default": 200,
            },
        ],
    },
    {
        "name": "list_input_files",
        "description": "List all files in a directory with size and type information. "
        "Useful for discovering available data files before loading them. "
        "Can list recursively to find files in subdirectories. Does not "
        "modify any files or directories.",
        "required_parameters": [
            {
                "name": "directory_path",
                "type": "str",
                "description": "Path to the directory to list.",
                "default": None,
            }
        ],
        "optional_parameters": [
            {
                "name": "recursive",
                "type": "bool",
                "description": "Whether to list files in subdirectories as well.",
                "default": False,
            },
        ],
    },
]
