from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from pathlib import Path
import os
import json
import csv
import datetime
from functools import partial

def filter(transaction):
    if "InternalTransfer" in transaction.description:
        return True
    if "Payment" in transaction.description:
        return True
    if "CashAdvance" in transaction.description:
        return True

def destroy_widgets(frame):
    for w in frame.winfo_children():
        w.destroy()

class Transaction:
    def __init__(self, row):
        def to_float(s):
            if s == "":
                return 0
            else:
                return float(s)
        self.transNum = row[0]
        d = row[1].split("/")
        self.date = datetime.date(int(d[2]), int(d[0]), int(d[1]))
        self.description, self.memo = row[2:4]
        self.debit, self.credit, self.balance = [abs(to_float(s)) for s in row[4:7]]
        self.checkNum = row[7]
        self.fees = to_float(row[8])

class Application(Tk):
    def __init__(self):
        super().__init__()
        self.minsize(600, 400)
        self.title("Spending Analysis Tool")
        self.startFrame = StartWindow(self)
        self.analysisFrame = AnalysisWindow(self)
        self.catgFrame = CategorizationWindow(self)
        self.startFrame.load()
        self.mainloop()

class StartWindow(Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.header = Label(self, text="Upload spending data")
        self.select = Button(self, text="Select file", width=25, command=self.select_csv)
        self.uploadButton = Button(self, text="Upload selected file(s)", width=25, command=self.upload_csv)
        self.selectedFilesFrame = Frame(self)
        self.selectedFiles = []
    
    def load(self):
        self.grid()
        self.header.grid(row=0, column=0, columnspan=2)
        self.select.grid(row=1, column=0)
        destroy_widgets(self.selectedFilesFrame)
        self.selectedFilesFrame.grid(row=2, column=0, columnspan=2)
    
    def select_csv(self):
        self.uploadButton.grid(row=1, column=1)
        csvFile = filedialog.askopenfilename()
        self.selectedFiles.append(csvFile)
        Label(self.selectedFilesFrame, text=csvFile).grid()
    
    def upload_csv(self):
        self.grid_forget()
        self.root.analysisFrame.load(self.selectedFiles)

class AnalysisWindow(Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.header = Label(self, text="Analysis results")
        self.backButton = Button(self, text="Back", command=self.return_to_start_window)
        self.uncatgButton = Button(self)
    
    def load(self, csvFiles):
        self.grid()
        self.backButton.grid(row=0, column=0)
        self.header.grid(row=1, column=0, columnspan=2)
        a = self.analyze_csv(csvFiles)
        self.display_analysis(a)

    def analyze_csv(self, csvFiles):
        # load and configure data
        with open(Path("categories.json"), "r") as f:
            superCategories = json.load(f)
            self.categories = {}
            for cats in superCategories.values():
                for k in cats.keys():
                    self.categories[k] = cats[k]
        if os.path.isfile(Path("keywords.json")):
            with open(Path("keywords.json"), "r") as f:
                self.keywords = json.load(f)
        else:
            self.keywords = {c: [] for c in self.categories.keys()}

        categorizedTransactions = {i: {c: [] for c in self.categories.keys()} for i in range(1,13)}  # month : { category : [transactions] }
        uncategorizedTransactions = []
        for file in csvFiles:
            with open(Path(file), "r") as f:
                data = csv.reader(f)
                for row in data:
                    t = Transaction(row)
                    if filter(t):  # remove irrelevant transactions like credit card payments and corrections
                        continue
                    m = t.date.month
                    c = None
                    for cat in self.keywords.keys():
                        for k in self.keywords[cat]:
                            if k in t.memo:
                                c = cat
                                categorizedTransactions[m][c].append(t)
                                break
                        if c:
                            break
                    if c == None:
                        uncategorizedTransactions.append(t)
        return categorizedTransactions, uncategorizedTransactions
    
    def display_analysis(self, analysis):
        data, u = analysis
        self.uncatgButton.config(text="View "+str(len(u))+" uncategorized transactions", command=partial(self.root.catgFrame.load, u, self.keywords))
        self.uncatgButton.grid(row=0, column=1)
        # graphical summary of transaction data
        # add here
    
    def return_to_start_window(self):
        self.grid_forget()
        self.root.startFrame.load()

class CategorizationWindow(Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root

    def load(self, uncategorizedTransactions, keywords):
        # in case not already empty, clear frame
        self.root.analysisFrame.grid_forget()
        destroy_widgets(self)
        self.grid()

        Label(self, text="Date").grid(column=0, row=1)
        Label(self, text="Amount").grid(column=1, row=1)
        Label(self, text="Memo").grid(column=2, row=1)
        Label(self, text="Keyword").grid(column=3, row=1)
        Label(self, text="Category").grid(column=4, row=1)

        self.rowCount = 0

        def update_keywords(k, c):
            k = k.get()
            if c and k and c in keywords.keys():
                keywords[c].append(k)

        def load_rows():
            j = 0
            while self.rowCount < len(uncategorizedTransactions) and j<10:
                i = self.rowCount
                t = uncategorizedTransactions[i]
                Label(self, text=str(t.date)).grid(column=0, row=i+2)
                Label(self, text=str(t.debit-t.credit)).grid(column=1, row=i+2)
                Label(self, text=t.memo).grid(column=2, row=i+2)
                # set up key value entry field
                k = Entry(self, width=50)
                k.grid(column=3, row=i+2)
                # set up dropdown menu for selecting category
                cval = StringVar()
                c = OptionMenu(self, cval, *list(keywords.keys()), command=partial(update_keywords, k))
                c.grid(column=4, row=i+2)
                self.rowCount += 1
                j += 1

        Button(self, text="Back", command=self.return_to_analysis_window).grid(row=0, column=0)
        Button(self, text="Load more", command=load_rows).grid(row=0, column=1)
        Button(self, text="Save", command=partial(self.save_keywords, uncategorizedTransactions, keywords)).grid(row=0, column=2)
        load_rows()

    def reanalyze_uncategorized(self, uncategorizedTransactions, keywords):
        with open(Path("keywords.json"), "r") as f:
            keywords = json.load(f)
        i = 0
        while i < len(uncategorizedTransactions):
            t = uncategorizedTransactions[i]
            m = t.date.month
            c = None
            for cat in keywords.keys():
                for k in keywords[cat]:
                    if k in t.memo:
                        c = cat
                        del uncategorizedTransactions[i]
                        i -= 1
                        break
                if c:
                    break
            i += 1
        return uncategorizedTransactions, keywords
    
    def save_keywords(self, uncategorizedTransactions, keywords):
        with open(Path("keywords.json"), "w") as f:
            json.dump(keywords, f)
        u,k = self.reanalyze_uncategorized(uncategorizedTransactions, keywords)
        self.load(u,k)
    
    def return_to_analysis_window(self):
        self.grid_forget()
        self.root.analysisFrame.load(self.root.startFrame.selectedFiles)

Application()
