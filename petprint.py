import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz  # PyMuPDF
import win32print  # For printing

def browse_directory():
    """Opens a file dialog to select a directory."""
    directory = filedialog.askdirectory()
    if directory:
        directory_var.set(directory)
        update_pdf_list(directory)

def update_pdf_list(directory):
    """Updates the list of PDFs in the selected directory."""
    for widget in pdf_list_frame.winfo_children():
        widget.destroy()

    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_path = os.path.join(directory, file)

            try:
                doc = fitz.open(pdf_path)
                num_pages = len(doc)
                doc.close()
            except Exception as e:
                num_pages = "Error"

            var = tk.BooleanVar()
            checkboxes[file] = var
            page_var = tk.StringVar()
            page_entries[file] = page_var

            pdf_frame = ttk.Frame(pdf_list_frame)

            checkbox = ttk.Checkbutton(pdf_frame, variable=var)
            checkbox.pack(side=tk.LEFT)

            label = ttk.Label(pdf_frame, text=f"{file} ({num_pages} pages)")
            label.pack(side=tk.LEFT, padx=5)

            page_entry = ttk.Entry(pdf_frame, textvariable=page_var, width=15)
            page_entry.pack(side=tk.RIGHT)

            pdf_frame.pack(fill=tk.X, pady=2)

def print_selected_pdfs():
    """Prints the selected PDFs with the specified page ranges."""
    directory = directory_var.get()
    if not directory:
        messagebox.showerror("Error", "Please select a directory.")
        return

    for file in os.listdir(directory):
        if file in checkboxes and checkboxes[file].get():
            pdf_path = os.path.join(directory, file)
            page_range = page_entries[file].get()

            try:
                if not os.path.exists(pdf_path):
                    continue

                doc = fitz.open(pdf_path)
                pages = parse_page_range(page_range, len(doc))

                for page in pages:
                    print_page(doc, page)

                doc.close()
            except Exception as e:
                messagebox.showerror("Error", f"Error printing {file}: {e}")

    messagebox.showinfo("Info", "Printing completed.")

def parse_page_range(page_range, total_pages):
    """Parses the page range and returns a list of pages to print."""
    if not page_range:
        return list(range(1, total_pages + 1))

    pages = []
    try:
        for part in page_range.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
    except ValueError:
        raise ValueError("Invalid page range format.")

    return [p for p in pages if 1 <= p <= total_pages]

def print_page(doc, page_number):
    """Prints a single page from a PDF."""
    printer_name = win32print.GetDefaultPrinter()
    page = doc[page_number - 1]

    # Save the page as a temporary file
    temp_path = os.path.join(os.getenv('TEMP'), f"temp_page_{page_number}.pdf")
    page_doc = fitz.open()
    page_doc.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)
    page_doc.save(temp_path)
    page_doc.close()

    # Use win32print to send the file to the printer
    with open(temp_path, "rb") as temp_file:
        raw_data = temp_file.read()
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            job = win32print.StartDocPrinter(hprinter, 1, (temp_path, None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, raw_data)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

    # Remove the temporary file
    os.remove(temp_path)

# GUI setup
root = tk.Tk()
root.title("PDF Printer")

# Directory selection
directory_frame = ttk.Frame(root)
directory_frame.pack(fill=tk.X, padx=10, pady=10)

directory_label = ttk.Label(directory_frame, text="Directory:")
directory_label.pack(side=tk.LEFT, padx=5)

directory_var = tk.StringVar()
directory_entry = ttk.Entry(directory_frame, textvariable=directory_var, width=50)
directory_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

browse_button = ttk.Button(directory_frame, text="Browse", command=browse_directory)
browse_button.pack(side=tk.LEFT, padx=5)

# PDF list
pdf_list_frame = ttk.Frame(root)
pdf_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

checkboxes = {}
page_entries = {}

# Print button
print_button = ttk.Button(root, text="Print Selected PDFs", command=print_selected_pdfs)
print_button.pack(pady=10)

root.mainloop()