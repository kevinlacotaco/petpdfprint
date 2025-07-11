# Created by Mickey (https://github.com/mickeystix)
# Free to use, edit, copy, whatever, I don't care - whatever license lets you do that, that's the one that covers this, sure, why not?

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox # For GUI
import tkinter.font as tkFont
import fitz  # PyMuPDF
import cups 
import tempfile

from typing import Callable

class ScrollableFrame(ttk.Frame):
    def __init__(self, master, *args, **kw):
        ttk.Frame.__init__(self, master, *args, **kw)

        vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=False)
        canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                           yscrollcommand=vscrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscrollbar.config(command=canvas.yview)

        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        self.content = ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=self.content,
                                           anchor='nw')

        def _configure_interior(event: None):
            size = (self.content.winfo_reqwidth(), self.content.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if self.content.winfo_reqwidth() != canvas.winfo_width():
                canvas.config(width=self.content.winfo_reqwidth())
        self.content.bind('<Configure>', _configure_interior)

        def _configure_canvas(event: None):
            if self.content.winfo_reqwidth() != canvas.winfo_width():
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)


class BrowseBar(tk.Frame):
    def __init__(self, master, cb: Callable[[str], None]):
        self.cur_directory = None
        self.selected_dir_cb = cb

        # Directory selection
        directory_frame = ttk.Frame(master)
        directory_frame.grid(row=0, column=0, sticky="NEW")

        directory_label = ttk.Label(directory_frame, text="Directory:")
        directory_label.pack(side=tk.LEFT, padx=5)

        directory_var = tk.StringVar()
        directory_entry = ttk.Entry(directory_frame, textvariable=directory_var, width=50)
        directory_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        browse_button = ttk.Button(directory_frame, text="Browse", command=self.browse_directory)
        browse_button.pack(side=tk.LEFT, padx=5)

    def browse_directory(self):
        """Opens a file dialog to select a directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.cur_directory = directory
            self.selected_dir_cb(directory)

class ActionBar(tk.Frame):
    def __init__(self, master, get_pdf_list: Callable[..., dict[str, str]]):
        action_frame = tk.Frame(master)
        action_frame.grid(row=2, column=0, sticky="NEW")

        self._get_pdf_list = get_pdf_list

        # Print button
        print_button = ttk.Button(action_frame, text="Print Selected PDFs", command=self.print_selected_pdfs)
        print_button.pack(pady=10, side=tk.BOTTOM, )
    
    def print_page(self, doc, page_number) -> None:
        """Prints a single page from a PDF."""
        conn = cups.Connection()
        printers = conn.getPrinters()

        firstPrinter = list(printers.keys())[0]

        # Save the page as a temporary file, otherwise it gets weird about file access
        with tempfile.NamedTemporaryFile() as fp:
            page_doc = fitz.open()
            page_doc.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)
            page_doc.save(fp.name)
            page_doc.close()

            try:
                conn.printFile(firstPrinter, fp.name, f"{doc}-{page_number}", {})
            except Exception as e:
                messagebox.showerror("Unable to print", e) 


    def print_selected_pdfs(self) -> None:
        """Prints the selected PDFs with the specified page ranges."""
        to_print: dict[str, list[int]] = self._get_pdf_list()

        if len(to_print.keys()) == 0:
            messagebox.showerror("Error", "Please select a pdfs.")
            return

        for path, pages in to_print.items():
            try:
                if not os.path.exists(path):
                    continue

                doc = fitz.open(path)

                for page in pages:
                    self.print_page(doc, page)

                doc.close()
            except Exception as e:
                messagebox.showerror("Error", f"Error printing {path}: {e}")

        messagebox.showinfo("Info", "Printing completed.")

class PdfList(tk.Frame):
    def __init__(self, master):
        container = ttk.Frame(master)
        self.master = master
        self.pdfConfigurations: dict[str, tuple[tk.StringVar, tk.StringVar, int]] = dict();

        container.grid(row=1, column=0, sticky="NSEW")

        # PDF list
        self.pdf_list_frame = ScrollableFrame(container)
        self.pdf_list_frame.config(border=True, borderwidth=3)

        self.pdf_list_frame.pack(fill="both", expand=True)

    def parse_page_entry(self, page_range: str, total_pages: int) -> list[int]:
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


    def get_selected_pdfs(self) -> dict[str, list[int]]:
        selected_pdfs: dict[str, list[int]] = dict()
        for file, [enabled, pageEntry, total_pages] in self.pdfConfigurations.items():
            if enabled.get() == 'on':
                selected_pdfs[file] = self.parse_page_entry(pageEntry.get(), total_pages)

        return selected_pdfs

    def update_listing(self, directory: str) -> None:
        """Updates the list of PDFs in the selected directory."""
        for widget in self.pdf_list_frame.interior.winfo_children():
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

                var = tk.StringVar(master=self.master, name=f"{file}-value", value="off")
                
                page_var = tk.StringVar()

                self.pdfConfigurations[pdf_path] = [var, page_var, num_pages]

                pdf_frame = ttk.Frame(self.pdf_list_frame.interior)
                pdf_frame.columnconfigure(1, weight=1)

                checkbox = ttk.Checkbutton(pdf_frame, variable=var, offvalue="off", onvalue="on")
 
                checkbox.grid(column=0, row=0)

                file_label = ttk.Label(pdf_frame, text=file, justify='left', anchor='w')

                file_label.grid(column=1, row=0, sticky='NSEW')

                def fitLabel(event):
                    label = event.widget
                    if not hasattr(label, "original_text"):
                        # preserve the original text so we can restore
                        # it if the widget grows.
                        label.original_text = label.cget("text")

                    font = tkFont.nametofont("TkDefaultFont")
                    text = label.original_text
                    max_width = event.width
                    actual_width = font.measure(text)
                    if actual_width <= max_width:
                        # the original text fits; no need to add ellipsis
                        label.configure(text=text)
                    else:
                        # the original text won't fit. Keep shrinking
                        # until it does
                        while actual_width > max_width and len(text) > 1:
                            text = text[:-1]
                            actual_width = font.measure(text + "...")
                        label.configure(text=text+"...")

                #file_label.bind("<Configure>", fitLabel)
                
                page_label = ttk.Label(pdf_frame, text=f"({num_pages} pages)")
                page_label.grid(column=2, row=0)

                page_entry = ttk.Entry(pdf_frame, textvariable=page_var, width=15)
                page_entry.grid(column=3, row=0)

                pdf_frame.pack(fill=tk.X, pady=2)



class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.browse_bar = BrowseBar(self, lambda dir:
                                    self.pdf_list.update_listing(dir) )
        self.pdf_list = PdfList(self)
        self.action_bar = ActionBar(self, lambda: 
                                    self.pdf_list.get_selected_pdfs())

if __name__ == "__main__":
    root = tk.Tk()
    root.title("PetPDFPrint")

    MainApplication(root).pack(side="top", fill="both", expand=True)
    root.mainloop()