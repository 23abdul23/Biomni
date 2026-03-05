"""File handling tools for reading and inspecting user-provided biological data files.

Provides functions to read CSV/TSV files, Excel spreadsheets, PDF documents,
DOCX documents, and common bioinformatics text formats (FASTA, FASTQ, VCF, GFF, BED, etc.)
without modifying the original data.
"""

import os


def _safe_path(file_path: str) -> str:
    """Resolve and validate a file path, returning the absolute path."""
    resolved = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"File not found: {resolved}")
    return resolved


def _human_size(nbytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


# ---------------------------------------------------------------------------
# 1. Inspect / detect file type
# ---------------------------------------------------------------------------

def inspect_file(file_path: str) -> str:
    """Inspect a file and return a summary of its type, size, and a preview of its contents.

    This function detects the file type based on extension, reports basic metadata
    (size, modification time, encoding guess), and returns a short content preview.
    It does **not** modify or move the file.

    Parameters
    ----------
    - file_path (str): Path to the file to inspect.

    Returns
    -------
    - str: A formatted summary string describing the file.
    """
    import datetime

    path = _safe_path(file_path)
    stat = os.stat(path)
    ext = os.path.splitext(path)[1].lower()

    steps = []
    steps.append(f"=== File Inspection Report ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Full path: {path}")
    steps.append(f"Size: {_human_size(stat.st_size)}")
    steps.append(f"Last modified: {datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()}")
    steps.append(f"Extension: {ext if ext else '(none)'}")

    # Categorize by extension
    tabular_exts = {".csv", ".tsv", ".tab", ".txt"}
    excel_exts = {".xls", ".xlsx", ".xlsm", ".xlsb"}
    bio_text_exts = {".fasta", ".fa", ".fna", ".fastq", ".fq", ".vcf",
                     ".gff", ".gff3", ".gtf", ".bed", ".sam", ".pdb",
                     ".mol", ".sdf", ".gbk", ".gb", ".embl", ".obo"}
    pdf_exts = {".pdf"}
    doc_exts = {".doc", ".docx"}
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".bmp"}

    if ext in tabular_exts:
        steps.append("Detected type: Tabular / delimited text")
    elif ext in excel_exts:
        steps.append("Detected type: Excel spreadsheet")
    elif ext in bio_text_exts:
        steps.append("Detected type: Bioinformatics text format")
    elif ext in pdf_exts:
        steps.append("Detected type: PDF document")
    elif ext in doc_exts:
        steps.append("Detected type: Word document")
    elif ext in image_exts:
        steps.append("Detected type: Image file")
    else:
        steps.append(f"Detected type: Unknown ({ext})")

    # Try to read a short text preview for text-based files
    if ext not in pdf_exts | doc_exts | excel_exts | image_exts:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                preview_lines = [f.readline() for _ in range(10)]
            preview = "".join(preview_lines).rstrip()
            steps.append(f"\n--- First 10 lines preview ---\n{preview}")
        except Exception:
            steps.append("(Could not read text preview)")

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 2. CSV / TSV reader
# ---------------------------------------------------------------------------

def read_csv_file(
    file_path: str,
    delimiter: str = ",",
    preview_rows: int = 20,
    show_stats: bool = True,
) -> str:
    """Read a CSV or TSV file and return a structured summary without modifying the data.

    Provides column names, data types, shape, missing-value counts, and an optional
    statistical summary. Returns a preview of the first ``preview_rows`` rows.

    Parameters
    ----------
    - file_path (str): Path to the CSV/TSV file.
    - delimiter (str): Column delimiter (default ``","``; use ``"\\t"`` for TSV).
    - preview_rows (int): Number of rows to include in the preview (default 20).
    - show_stats (bool): Whether to include descriptive statistics (default True).

    Returns
    -------
    - str: A formatted report of the file contents.
    """
    import pandas as pd

    path = _safe_path(file_path)
    steps = []

    try:
        df = pd.read_csv(path, sep=delimiter, engine="python")
    except Exception as e:
        return f"Error reading CSV file: {e}"

    rows, cols = df.shape
    steps.append(f"=== CSV File Summary ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Shape: {rows} rows × {cols} columns")
    steps.append(f"Columns: {', '.join(df.columns.tolist())}")

    # Data types
    steps.append("\n--- Column Data Types ---")
    for col in df.columns:
        steps.append(f"  {col}: {df[col].dtype}")

    # Missing values
    missing = df.isnull().sum()
    if missing.any():
        steps.append("\n--- Missing Values ---")
        for col in missing[missing > 0].index:
            steps.append(f"  {col}: {missing[col]} missing ({missing[col]/rows*100:.1f}%)")
    else:
        steps.append("\nNo missing values detected.")

    # Descriptive statistics
    if show_stats:
        steps.append("\n--- Descriptive Statistics ---")
        steps.append(df.describe(include="all").to_string())

    # Preview rows
    n = min(preview_rows, rows)
    steps.append(f"\n--- First {n} Rows ---")
    steps.append(df.head(n).to_string(index=False))

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 3. Excel reader
# ---------------------------------------------------------------------------

def read_excel_file(
    file_path: str,
    sheet_name: str = None,
    preview_rows: int = 20,
    show_stats: bool = True,
) -> str:
    """Read an Excel file (.xls/.xlsx) and return a structured summary without modifying the data.

    If ``sheet_name`` is not specified, reads the first sheet and lists all available
    sheet names.

    Parameters
    ----------
    - file_path (str): Path to the Excel file.
    - sheet_name (str): Name of the sheet to read (default: first sheet).
    - preview_rows (int): Number of rows to include in the preview (default 20).
    - show_stats (bool): Whether to include descriptive statistics (default True).

    Returns
    -------
    - str: A formatted report of the file contents.
    """
    import pandas as pd

    path = _safe_path(file_path)
    steps = []

    try:
        xls = pd.ExcelFile(path)
        sheet_names = xls.sheet_names
        target_sheet = sheet_name if sheet_name else sheet_names[0]
        df = pd.read_excel(xls, sheet_name=target_sheet)
    except Exception as e:
        return f"Error reading Excel file: {e}"

    rows, cols = df.shape
    steps.append(f"=== Excel File Summary ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Available sheets: {', '.join(sheet_names)}")
    steps.append(f"Reading sheet: {target_sheet}")
    steps.append(f"Shape: {rows} rows × {cols} columns")
    steps.append(f"Columns: {', '.join(df.columns.astype(str).tolist())}")

    # Data types
    steps.append("\n--- Column Data Types ---")
    for col in df.columns:
        steps.append(f"  {col}: {df[col].dtype}")

    # Missing values
    missing = df.isnull().sum()
    if missing.any():
        steps.append("\n--- Missing Values ---")
        for col in missing[missing > 0].index:
            steps.append(f"  {col}: {missing[col]} missing ({missing[col]/rows*100:.1f}%)")
    else:
        steps.append("\nNo missing values detected.")

    # Statistics
    if show_stats:
        steps.append("\n--- Descriptive Statistics ---")
        steps.append(df.describe(include="all").to_string())

    n = min(preview_rows, rows)
    steps.append(f"\n--- First {n} Rows ---")
    steps.append(df.head(n).to_string(index=False))

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 4. PDF reader
# ---------------------------------------------------------------------------

def read_pdf_file(
    file_path: str,
    max_pages: int = 0,
    extract_tables: bool = False,
) -> str:
    """Read a PDF file and extract its text content without modifying the original file.

    Useful for reading research papers, supplementary materials, and reports.
    Optionally extracts tables from the PDF.

    Parameters
    ----------
    - file_path (str): Path to the PDF file.
    - max_pages (int): Maximum number of pages to read (0 = all pages, default 0).
    - extract_tables (bool): Whether to attempt table extraction (default False).

    Returns
    -------
    - str: Extracted text content from the PDF.
    """
    import PyPDF2

    path = _safe_path(file_path)
    steps = []

    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            steps.append(f"=== PDF Document Summary ===")
            steps.append(f"File: {os.path.basename(path)}")
            steps.append(f"Total pages: {total_pages}")

            # Extract metadata
            meta = reader.metadata
            if meta:
                if meta.title:
                    steps.append(f"Title: {meta.title}")
                if meta.author:
                    steps.append(f"Author: {meta.author}")
                if meta.subject:
                    steps.append(f"Subject: {meta.subject}")

            pages_to_read = total_pages if max_pages == 0 else min(max_pages, total_pages)
            steps.append(f"Reading {pages_to_read} of {total_pages} pages...\n")

            for i in range(pages_to_read):
                page = reader.pages[i]
                text = page.extract_text()
                if text and text.strip():
                    steps.append(f"--- Page {i + 1} ---")
                    steps.append(text.strip())
                else:
                    steps.append(f"--- Page {i + 1} --- (no extractable text)")
    except Exception as e:
        return f"Error reading PDF file: {e}"

    # Optional table extraction
    if extract_tables:
        try:
            import tabula
            tables = tabula.read_pdf(path, pages="all", multiple_tables=True)
            if tables:
                steps.append(f"\n=== Extracted Tables ({len(tables)} found) ===")
                for idx, table in enumerate(tables):
                    steps.append(f"\n--- Table {idx + 1} ---")
                    steps.append(table.to_string(index=False))
        except ImportError:
            steps.append("\n(Table extraction requires 'tabula-py'. Install with: pip install tabula-py)")
        except Exception as e:
            steps.append(f"\nTable extraction failed: {e}")

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 5. DOCX reader
# ---------------------------------------------------------------------------

def read_docx_file(file_path: str, include_tables: bool = True) -> str:
    """Read a Word document (.docx) and extract its text content without modifying the file.

    Extracts paragraphs and optionally embedded tables.

    Parameters
    ----------
    - file_path (str): Path to the .docx file.
    - include_tables (bool): Whether to extract tables from the document (default True).

    Returns
    -------
    - str: Extracted text content from the document.
    """
    from docx import Document

    path = _safe_path(file_path)
    steps = []

    try:
        doc = Document(path)
    except Exception as e:
        return f"Error reading DOCX file: {e}"

    steps.append(f"=== Word Document Summary ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Paragraphs: {len(doc.paragraphs)}")
    steps.append(f"Tables: {len(doc.tables)}")

    # Extract metadata from core properties
    try:
        props = doc.core_properties
        if props.title:
            steps.append(f"Title: {props.title}")
        if props.author:
            steps.append(f"Author: {props.author}")
        if props.subject:
            steps.append(f"Subject: {props.subject}")
    except Exception:
        pass

    # Extract paragraphs
    steps.append("\n--- Document Text ---")
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            steps.append(text)

    # Extract tables
    if include_tables and doc.tables:
        steps.append(f"\n--- Embedded Tables ({len(doc.tables)} found) ---")
        for idx, table in enumerate(doc.tables):
            steps.append(f"\nTable {idx + 1}:")
            header_row = table.rows[0]
            headers = [cell.text.strip() for cell in header_row.cells]
            steps.append(" | ".join(headers))
            steps.append("-" * (len(" | ".join(headers))))
            for row in table.rows[1:]:
                row_data = [cell.text.strip() for cell in row.cells]
                steps.append(" | ".join(row_data))

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 6. Bioinformatics text format reader
# ---------------------------------------------------------------------------

def read_bio_text_file(
    file_path: str,
    max_records: int = 50,
) -> str:
    """Read common bioinformatics text files and return a structured summary.

    Supports FASTA, FASTQ, VCF, GFF/GTF, BED, SAM, PDB, GenBank, and other
    standard biological data formats. The original file is never modified.

    Parameters
    ----------
    - file_path (str): Path to the bioinformatics text file.
    - max_records (int): Maximum number of records/entries to preview (default 50).

    Returns
    -------
    - str: A formatted summary and preview of the file contents.
    """
    path = _safe_path(file_path)
    ext = os.path.splitext(path)[1].lower()
    steps = []

    steps.append(f"=== Bioinformatics File Summary ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Size: {_human_size(os.path.getsize(path))}")
    steps.append(f"Format: {ext}")

    try:
        # FASTA
        if ext in (".fasta", ".fa", ".fna"):
            steps.append(f"Type: FASTA sequence file\n")
            record_count = 0
            current_header = None
            current_seq_len = 0
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(">"):
                        if current_header is not None and record_count <= max_records:
                            steps.append(f"  {current_header}  (length: {current_seq_len} bp)")
                        current_header = line[1:]
                        current_seq_len = 0
                        record_count += 1
                    else:
                        current_seq_len += len(line)
                # last record
                if current_header is not None and record_count <= max_records:
                    steps.append(f"  {current_header}  (length: {current_seq_len} bp)")
            steps.insert(3, f"Total sequences: {record_count}")

        # FASTQ
        elif ext in (".fastq", ".fq"):
            steps.append(f"Type: FASTQ sequence file\n")
            record_count = 0
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f):
                    if line_num % 4 == 0 and line.startswith("@"):
                        record_count += 1
                        if record_count <= max_records:
                            steps.append(f"  Read: {line.strip()[1:]}")
            steps.insert(3, f"Total reads: {record_count}")

        # VCF
        elif ext == ".vcf":
            steps.append(f"Type: Variant Call Format\n")
            header_lines = []
            variant_count = 0
            preview_variants = []
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("##"):
                        header_lines.append(line.strip())
                    elif line.startswith("#CHROM"):
                        col_headers = line.strip().split("\t")
                        steps.append(f"Columns: {', '.join(col_headers)}")
                        num_samples = max(0, len(col_headers) - 9)
                        steps.append(f"Samples: {num_samples}")
                    else:
                        variant_count += 1
                        if variant_count <= max_records:
                            preview_variants.append(line.strip())
            steps.append(f"Metadata lines: {len(header_lines)}")
            steps.append(f"Total variants: {variant_count}")
            if preview_variants:
                steps.append(f"\n--- First {len(preview_variants)} Variants ---")
                for v in preview_variants:
                    steps.append(f"  {v[:200]}")

        # GFF / GTF
        elif ext in (".gff", ".gff3", ".gtf"):
            steps.append(f"Type: Gene annotation file ({ext.upper()})\n")
            feature_count = 0
            feature_types = {}
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 9:
                        feature_count += 1
                        ftype = parts[2]
                        feature_types[ftype] = feature_types.get(ftype, 0) + 1
            steps.append(f"Total features: {feature_count}")
            steps.append("Feature types:")
            for ftype, count in sorted(feature_types.items(), key=lambda x: -x[1]):
                steps.append(f"  {ftype}: {count}")

        # BED
        elif ext == ".bed":
            steps.append(f"Type: BED genomic intervals\n")
            region_count = 0
            chroms = set()
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("#") or line.startswith("track") or line.startswith("browser"):
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 3:
                        region_count += 1
                        chroms.add(parts[0])
            steps.append(f"Total regions: {region_count}")
            steps.append(f"Chromosomes represented: {len(chroms)}")
            steps.append(f"Chromosomes: {', '.join(sorted(chroms))}")

        # SAM
        elif ext == ".sam":
            steps.append(f"Type: Sequence Alignment Map\n")
            header_lines = 0
            alignment_count = 0
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("@"):
                        header_lines += 1
                    else:
                        alignment_count += 1
            steps.append(f"Header lines: {header_lines}")
            steps.append(f"Alignments: {alignment_count}")

        # GenBank
        elif ext in (".gbk", ".gb"):
            steps.append(f"Type: GenBank flat file\n")
            record_count = 0
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("LOCUS"):
                        record_count += 1
                        if record_count <= max_records:
                            steps.append(f"  {line.strip()}")
            steps.append(f"Total records: {record_count}")

        # PDB
        elif ext == ".pdb":
            steps.append(f"Type: Protein Data Bank structure\n")
            atom_count = 0
            chains = set()
            title = ""
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("TITLE"):
                        title += line[10:].strip() + " "
                    elif line.startswith("ATOM") or line.startswith("HETATM"):
                        atom_count += 1
                        if len(line) > 21:
                            chains.add(line[21])
            if title:
                steps.append(f"Title: {title.strip()}")
            steps.append(f"Atom records: {atom_count}")
            steps.append(f"Chains: {', '.join(sorted(chains))}")

        # Generic text fallback
        else:
            steps.append(f"Type: Generic text file\n")
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_records:
                        break
                    lines.append(line.rstrip())
            steps.append(f"--- First {len(lines)} lines ---")
            for line in lines:
                steps.append(line)

    except Exception as e:
        steps.append(f"Error reading file: {e}")

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 7. Generic text file reader
# ---------------------------------------------------------------------------

def read_text_file(file_path: str, max_lines: int = 200) -> str:
    """Read a plain text file and return its contents up to a specified number of lines.

    Suitable for README files, log files, configuration files, and any other
    text-based content. The original file is never modified.

    Parameters
    ----------
    - file_path (str): Path to the text file.
    - max_lines (int): Maximum number of lines to read (default 200).

    Returns
    -------
    - str: The text content of the file (truncated if necessary).
    """
    path = _safe_path(file_path)
    steps = []

    steps.append(f"=== Text File Contents ===")
    steps.append(f"File: {os.path.basename(path)}")
    steps.append(f"Size: {_human_size(os.path.getsize(path))}")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.rstrip())
        total_read = len(lines)
        steps.append(f"Lines shown: {total_read}" + (f" (truncated at {max_lines})" if total_read == max_lines else ""))
        steps.append("")
        steps.extend(lines)
    except Exception as e:
        steps.append(f"Error reading file: {e}")

    return "\n".join(steps)


# ---------------------------------------------------------------------------
# 8. Directory listing
# ---------------------------------------------------------------------------

def list_input_files(directory_path: str, recursive: bool = False) -> str:
    """List all files in a directory, optionally recursively, with size and type information.

    Useful for discovering available data files before loading them.
    Does not modify any files or directories.

    Parameters
    ----------
    - directory_path (str): Path to the directory to list.
    - recursive (bool): Whether to list files in subdirectories (default False).

    Returns
    -------
    - str: A formatted listing of all files found.
    """
    dir_path = os.path.abspath(os.path.expanduser(directory_path))
    if not os.path.isdir(dir_path):
        return f"Error: Directory not found: {dir_path}"

    steps = []
    steps.append(f"=== Directory Listing ===")
    steps.append(f"Directory: {dir_path}")

    file_list = []
    if recursive:
        for root, dirs, files in os.walk(dir_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, dir_path)
                size = os.path.getsize(fpath)
                file_list.append((rel_path, size))
    else:
        for entry in os.listdir(dir_path):
            fpath = os.path.join(dir_path, entry)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                file_list.append((entry, size))
            elif os.path.isdir(fpath):
                file_list.append((entry + "/", -1))

    steps.append(f"Total items: {len(file_list)}\n")

    for name, size in sorted(file_list):
        if size < 0:
            steps.append(f"  [DIR]  {name}")
        else:
            ext = os.path.splitext(name)[1].lower()
            steps.append(f"  {_human_size(size):>10}  {name}")

    return "\n".join(steps)
