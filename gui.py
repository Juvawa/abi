from Tkinter import *
from main import dir_to_file_list, main
from bibtexparser.bibdatabase import BibDatabase
import ConfigParser
import os
import bibtexparser
import subprocess

def whichSelected():
    print "At %s of %d" % (select.curselection(), len(files))
    print type(select.curselection())
    write_selected_to_file(select.curselection())
    #return int(select.curselection()[0])

def write_selected_to_file(selected):
    db = BibDatabase()
    result = []
    for item in selected:
        path = str(bib_dir) + str(files[item])
        with open(path, 'r') as f:
            db = bibtexparser.load(f)
            result.append(db.entries[0])
    db.entries = result
    print db.entries
    with open(website_dir, 'w') as f:
        bibtexparser.dump(db, f)

    subprocess.call(['bib2html', '-f', website_dir])



def makeWindow () :
    global select
    win = Tk()
    win.geometry('{}x{}'.format(1250, 1000))

    frame1 = Frame(win)
    frame1.pack()

    Label(frame1, text="Select the BibTex entries you want to publish on website").grid(row=0, column=0, sticky=W)

    frame2 = Frame(win)       # Row of buttons
    frame2.pack()
    b1 = Button(frame2,text="Search for new entries",command=main)
    b2 = Button(frame2,text="Save selection to file",command=whichSelected)
    b1.pack(side=LEFT); b2.pack(side=LEFT)

    frame3 = Frame(win)       # select of names
    frame3.pack(fill='both', expand=True)
    scroll = Scrollbar(frame3, orient=VERTICAL)
    select = Listbox(frame3, yscrollcommand=scroll.set, height=6, selectmode = "multiple" )
    scroll.config (command=select.yview)
    scroll.pack(side=RIGHT, fill=Y)
    select.pack(side=LEFT,  fill=BOTH, expand=1)
    return win

win = makeWindow()
config = ConfigParser.ConfigParser()
config.read('settings.conf')
bib_dir = config.get('bibtex', 'shared_directory')
website_dir = config.get('general', 'website_bib')
files = []
count = 0
for f in os.listdir(bib_dir):
    if f.endswith(".bib"):
        files.append(f)
        select.insert(count, f)
        count += 1

win.mainloop()
