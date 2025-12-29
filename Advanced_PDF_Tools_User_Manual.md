# Advanced PDF Tools - User Manual

This application is a comprehensive suite for modifying and extracting data from PDF documents. It consists of three main modules:
1.  **Coordinate Finder**: To identify the precise location (x, y coordinates) of text.
2.  **Replacer**: To replace text or fonts across multiple pages.
3.  **PDF to Excel**: To batch extract specific data fields from multiple PDFs into CSV/Excel.

---

## 1. Coordinate Finder
**Purpose**: Helps you find the exact bounding box coordinates `(x0, y0, x1, y1)` of specific text. These coordinates are essential for using the *Replacer* or *PDF to Excel* tools.

### How to Use
1.  **Input PDF**: Browse and select your source PDF.
2.  **Output CSV**: Choose where to save the results.
3.  **Configuration**:
    *   **Find**: Enter the text you want to locate (e.g., "Invoice Date").
    *   **Pages**: Specify pages (e.g., `1`, `1-5`, or `*` for all).
    *   **Match Mode**:
        *   `Partial`: Matches if the text *contains* your search term (e.g., search "Date" finds "Invoice Date").
        *   `Exact`: Matches only if the text is exactly equal.
4.  **Remove Duplicates** (Checkbox):
    *   Check this if you want to ignore multiple occurrences of the same text that are stacked on top of each other (common in some PDF generators).
5.  **Run Finder**: Click to execute.

### Example
*   **Goal**: Find where "Total Amount" appears to extract the value next to it.
*   **Setup**:
    *   Find: `Total Amount`
    *   Match Mode: `Partial`
*   **Result (CSV)**:
    *   `Search_Term`: Total Amount
    *   `Page`: 1
    *   `x0, y0, x1, y1`: `450.5, 700.2, 520.5, 712.0`
    *   *You can now use these coordinates in the Replacer or Extractor.*

---

## 2. Replacer
**Purpose**: Replace text content or change fonts within a defined area.

### How to Use
1.  **Map Files**: Select Input PDF and Output PDF path.
2.  **Font Setup**:
    *   **Scan Windows Fonts**: Loads your system fonts.
    *   **Add Font File**: Load a specific `.ttf` or `.otf` file.
    *   *Note*: You must select a font for the replacement text.
3.  **Add Rows**:
    *   **Find**: Text to look for (optional if using coordinates).
    *   **Replace**: The new text you want to insert.
    *   **Coordinates**: `x0, y0, x1, y1` (from Finder). *Highly recommended* to target specific areas.
    *   **Font**: Select the font to use for the new text.
    *   **Lift Font**: (Optional) If "Find" text is detected, "lift" (copy) its font style for the replacement.
4.  **Run Replacer**.

### Example
*   **Goal**: Replace the old company name "OldCorp" with "NewCorp" in the footer.
*   **Setup**:
    *   Find: `OldCorp`
    *   Replace: `NewCorp`
    *   Coordinates: `50, 800, 500, 850` (Footer area)
    *   Font: `Arial-Bold`

---

## 3. PDF to Excel (Data Extraction)
**Purpose**: Bulk extract specific fields (like Dates, Invoice #s, Totals) from hundreds of PDFs into a structured CSV file.

### How to Use
1.  **Input Files**:
    *   **Add Files/Folder**: Select the PDFs you want to process.
    *   **Pages**: Default is `*` (all), or specify `1` to only extract from the first page.
2.  **Define Attributes** (Columns in Excel):
    *   **Attribute Name**: Column header (e.g., "inv_date").
    *   **Coordinates**: `x0, y0, x1, y1` box where this data is located.
3.  **Output Options**:
    *   **Master CSV**: Combines all files into one single sheet (e.g., `Extraction_Results.csv`).
    *   **Individual CSVs**: Creates one CSV per PDF file.
4.  **Advanced Settings**:
    *   **Strict Include**: Only extracts text if the *entire word* is inside the box. Useful for tight layouts where nearby text touches the box.
    *   **Remove Duplicates**: Cleans up cases where the PDF has invisible layered text (e.g., "Text\nText").
    *   **Formulas**: Automatically handles text starting with `=`, `+`, `-` to prevent Excel errors.

### Example scenario
You have 100 invoices. You want to extract the **Invoice Number** and **Total**.
1.  **Use Finder** on one sample PDF to get coordinates:
    *   Invoice # box: `400, 50, 500, 70`
    *   Total box: `400, 700, 500, 720`
2.  **Configure PDF to Excel**:
    *   Row 1: Name=`InvoiceNum`, Coords=`400, 50, 500, 70`
    *   Row 2: Name=`Total`, Coords=`400, 700, 500, 720`
3.  **Run**:
    *   Result: A CSV with 100 rows, columns "Source", "InvoiceNum", "Total".

---

## Tips
*   **Log Files**: If "Generate Report" is checked, detailed logs are saved in `Advanced PDF tools logs`.
*   **Auto-Save**: Your configurations are automatically saved to `Advanced PDF tools configs`.
*   **Coordinates**: PDF coordinates usually start from bottom-left or top-left depending on the standard. This tool uses **PyMuPDF standard (Top-Left is 0,0)**.
