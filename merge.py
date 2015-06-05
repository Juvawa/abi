# coding=utf-8

from bibtexparser import load, loads, dump, dumps
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from pybtex.database import Person
from normalize import normalize_title
import errno
import re
import unicodedata
import latexcodec
import normalize
from glob import glob
from fuzzywuzzy.fuzz import ratio

import logging
import logging.config

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

def merge_name_record(record1, record2):
    result = []
    if record1 == record2:
        return record1
    else:
        for i in range(len(record1)):
            if len(record1[i]) >= len(record2[i]):
                result.append(record1[i])
            elif len(record1[i]) <= len(record2[i]):
                result.append(record2[i])
            else:
                pass

        return result

def merge_name(name1, name2):
    if (name1.first() == name2.first() or name1.first()[0][0] == name2.first()[0][0]) and \
        (name1.middle() == name2.middle() or name1.middle()[0][0] == name2.middle()[0][0]) and\
        name1.last() == name2.last():
        first = ' '.join(merge_name_record(name1.first(), name2.first()))
        middle = ' '.join(merge_name_record(name1.middle(), name2.middle()))
        result = Person(first=first, middle=middle, last=' '.join(name1.last()))
    else:
        return -1

    return result

def merge_names(name1, name2):

    result = -1
    if  len(name1.first()) == len(name2.first()) and \
        len(name1.middle()) == len(name2.middle()) and \
        len(name1.last()) == len(name2.last()):
        result = merge_name(name1, name2)

    return result

def not_intersection(union, intersection):
    return list(set(union) - set(intersection))

def intersect(a, b):
    """ return the intersection of two lists """
    return list(set(a) & set(b))

def get_union(a, b):
    """ return the union of two lists """
    return list(set(a) | set(b))

def add_field(entries, field, to_add):
    entries[field] = str(to_add)
    return entries

def split_name_to_person_list(author):
    authors = author.split(' and ')
    a = []
    for author in authors:
        a.append(Person(author))
    return a

def merge_author(author1, author2):
    merged = []
    authors1 = split_name_to_person_list(author1)
    authors2 = split_name_to_person_list(author2)
    for author1 in authors1:
        for author2 in authors2:
            result = merge_names(author1, author2)
            if result != -1:
               merged.append(result) 
            #print merged

    return ' and '.join(unicode(person) for person in merged)

def merge_keywords(keywords1, keywords2):
    return set(keywords1 + keywords2)

def merge(entry1, entry2):
    #print "merging %s and %s" % (entry1, entry2)
    db = BibDatabase()
    entries = {}
    keys1 = entry1.keys()
    keys2 = entry2.keys()
    intersection = intersect(keys1, keys2)
    union = get_union(keys1, keys2)
    not_intersect = not_intersection(union, intersection)

    #The two entries have the same keys, so everything needs to be merged
    if not not_intersect:
        #print "Same entries"
        #print keys1, keys2
        for key in keys1:
            if key == 'author' or key == 'editor':
                author = merge_author(entry1[key], entry2[key])
                entries = add_field(entries, key, author)
            elif key == 'keywords' or key == 'topics':
                entries = add_field(entries, key, merge_keywords(entry1[key], entry2[key]))
            elif key == 'month':
                entries = add_field(entries, key, entry1[key])
            elif len(entry1[key]) == len(entry2[key]) or len(entry1[key]) < len(entry2[key]):
                entries = add_field(entries, key, entry1[key])
            else:
                entries = add_field(entries, key, entry2[key])
    else:
        #All the keys in the two entries aren't the same, so some need to be merged
        #some can just be written
        #print "Entries are not the same!"
        #print keys1, keys2
        for key in intersection:
            if key == 'author' or key == 'editor':
                entries = add_field(entries, key, merge_author(entry1[key], entry2[key]))
            elif key == 'keywords' or key == 'topics':
                entries = add_field(entries, key, merge_keywords(entry1[key], entry2[key]))
            elif key == 'month':
                entries = add_field(entries, key, entry1[key])
            elif len(entry1[key]) == len(entry2[key]) or len(entry1[key]) < len(entry2[key]):
                entries = add_field(entries, key, entry1[key])
            else:
                entries = add_field(entries, key, entry2[key])
        for key in not_intersect:
            if key in keys1:
                entries = add_field(entries, key, entry1[key])
            elif key in keys2:
                entries = add_field(entries, key, entry2[key])
    
    db.entries = [entries]
    return db
