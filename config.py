#!/usr/bin/env python
from configparser import ConfigParser
import sys

# create a parser
parser = ConfigParser()

def config(filename='ruct.ini', section='location'):
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db

def save(option, value, filename='ruct.ini', section='location'):
    # read config file
    parser.read(filename)
    parser.items(section)
    if isinstance(option, list):
        if isinstance(value, list) and len(option) == len(value):
            for o in option:
                parser.set(section, o, str(value[option.index(o)]))
        else: 
            raise ValueError("If option is a list, value must be a list with the same length")
    else:
        parser.set(section, option, value)
    with open (filename, 'w') as file:
        parser.write(file)
