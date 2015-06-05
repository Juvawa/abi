# coding=utf-8

from bibtexparser import load, loads, dump, dumps
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from pybtex.database import Person
from merge import merge, add_field
import ConfigParser
import logging
import logging.config
import glob
import os
from normalize import normalize_title, normalize_year, space_to_underscore, normalize_author
import subprocess
import re
from fuzzywuzzy import process
from time import time, sleep
import gscholar as gs
import random

logger = logging.getLogger(__name__)

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s %(funcName)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'ERROR',
            'formatter': 'standard',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'ERROR',
            'formatter': 'standard',
            'propagate': True
        }
    }
})

writer = BibTexWriter()
writer.contents = ['comments', 'entries']
writer.indent = '  '
writer.order_entries_by = ('ENTRYTYPE', 'author', 'year')

def create_id(t, year, title):
	return str(t) + "_" + str(year) + "_" + str(space_to_underscore(title))

def pdf(pdf_files, shared_pdf, bibtex_folder, bibtex_files, gscholar):
	print "gettings pdf " + str(pdf_files)
	for pdf in pdf_files:
		txt = re.sub("\W", " ", gs.convert_pdf_to_txt(pdf)).lower()
		words = txt.strip().split()[:15]
		words = " ".join(words)		
		print words
		if gscholar == True:
			bib = loads(gs.pdflookup(pdf, all, gs.FORMAT_BIBTEX)[0])
			keys = bib.entries[0].keys()
			matching = [s for s in keys if "pdf" in s]
			if len(matching) - 1 <= 0:
				key = 'pdf'
			else:
				key = 'pdf' + str(len(matching))
			#link = os.symlink(pdf, str(shared_pdf) + str(pdf.split('/')[-1]))
			bib.entries = [add_field(bib.entries[0], key, bib)]
			#print bib.entries
			bibtex(bib.entries, bibtex_folder, bib)
			sleep(random.uniform(1, 2))
		else:
			print "Im in else"
			best_match = process.extractBests(words, bibtex_files, limit=1)
			print best_match
			if best_match:
				bib = best_match[0][0]
				score = best_match[0][1]
				if score > 60:
					with open(bib, 'r') as f:
						db = load(f)
					entries = db.entries[0]
					keys = entries.keys()
					matching = [s for s in keys if "pdf" in s]
					if len(matching) - 1 <= 0:
						key = 'pdf'
					else:
						key = 'pdf' + str(len(matching))
					entries = add_field(entries, key, bib)
					with open(bib, 'w') as f:
						f.write(writer._entry_to_bibtex(entries))

# BibTex controll function, decides if BibTex needs to be merged
# or if it can just be written
def bibtex(entries, db_folder, current_file):
	failed = False
	for i, entry in enumerate(entries):
		keys = entry.keys()
		#Make sure the values don't have unicode characters, normalize them
		for key in keys:
			entry[key] = str(entry[key].encode('ascii', 'replace'))
		#Normalize author to the Name class
		if 'author' in keys and not 'author_norm' in keys:
			authors = entry['author'].split(' and ')
			a = []
			for author in authors:
				#print author
				try:
					a.append(Person(author))
				except:
					print "Author field does not respect the BibTex convention"
					continue
			entry['author'] = ' and '.join(unicode(person) for person in a)
		else:
			entry['author'] = "undefined"
		#Normalize editor to the Name class
		if 'editor' in keys and not 'editor_norm' in keys:
			editors = entry['editor'].split(' and ')
			a = []
			for editor in editors:
				#print editor
				try:
					a.append(Person(editor))
				except:
					print "editor field does not respect the BibTex convention"
					continue
			entry['editor'] = ' and '.join(unicode(person) for person in a)
		else:
			entry['editor'] = "undefined"
		if 'title' in keys and not 'title_norm' in keys:
			title_norm = normalize_title(str(entry['title']))
			entry['title_norm'] = str(title_norm)
		else:
			title_norm = "undefined"
			entry['title'] = "undefined"
		if 'year' in keys and not 'year_norm' in keys and len(entry['year']) > 0:
			year_norm = normalize_year(str(entry['year']))
			entry['year_norm'] = str(year_norm)
		else:
			year_norm = "undefined"
			entry['year'] = "undefined"
		if 'id' in keys:
			citationkey = str(create_id(entry['type'], year_norm, title_norm))
			entry['id'] = str(citationkey)
		else:
			print "No citationkey found, faulty entry, will be skipped"
			continue
		if failed:
			filename = str(create_id(entry['type'], year_norm, title_norm)) + "_FAILED.bib"
		else: 
			filename = str(create_id(entry['type'], year_norm, title_norm)) + ".bib"
		path = str(db_folder) + str(filename)
		exists = os.path.exists(path)
		if exists == False:
			#print "NEWFILE " + str(path)
			try:
				with open(path, 'w+') as f:
					f.write(writer._entry_to_bibtex(entry))
			except:
				print "There must be something wrong, please check: "
				print current_file
				print "Can't write this file " + str(path)
		else:
			#print "MERGING"
			with open(path, 'r') as f:
				simular = load(f).entries
				if len(simular) > 0:
					#print "merging"
					db = merge(entry, simular[0])
			with open(path, 'w') as f:
				if len(db.entries) > 0:
					f.write(writer._entry_to_bibtex(db.entries[0]))
			if len(simular) == 0:
				with open(path, 'w') as f:
					f.write(writer._entry_to_bibtex(entry))

# Recursively search all subdirectory for files of given type t
def dir_to_file_list(dirs, t):
	for d in dirs:
		files = [os.path.join(dirpath, f)
    				for dirpath, dirnames, files in os.walk(d)
    				for f in files if f.endswith(t)]

	return files

def main():
	config = ConfigParser.ConfigParser()
	config.read('settings.conf')
	bibtex_files = dir_to_file_list(config.get('bibtex', 'directories').split(','), '.bib')
	shared_bib = config.get('bibtex', 'shared_directory')
	for bib in bibtex_files:
		with open(bib, 'r') as bibtex_file:
			print bibtex_file
			db = load(bibtex_file)
			bibtex(db.entries, shared_bib, bibtex_file)

	gscholar = config.get('general','google_scholar')
	pdf_files = dir_to_file_list(config.get('pdf', 'directories').split(','), '.pdf')
	bibtex_files_shared = dir_to_file_list(shared_bib.split(','), '.bib')
	print pdf_files
	shared_pdf = config.get('pdf', 'shared_directory')
	pdf(pdf_files, shared_pdf, shared_bib, bibtex_files_shared, gscholar)
	

if __name__ == '__main__':
	start = time()
	main()
	end = time()
	print end-start
