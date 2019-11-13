#!/usr/bin/python
import sys
import numpy as np
import string
from math import *
import random as rnd
from subprocess import call
import itertools as itt

def readAtoms(filename):
    input = open(filename,"r")
    print("reading file {}".format(filename))
    currentId=0
    line = input.readline()
    out = line.find("atoms")
    while(out==-1):
        line = input.readline()
        out = line.find("atoms")
    print(line)
    numwords = line.split()
    numatms = int(numwords[0])
    atoms = np.zeros((numatms,7))
    while(input.readline().find("Atoms")==-1):
        continue
    input.readline()
    line=input.readline
    for j in range(numatms):
        line=input.readline()
        record = line.split()
        for i in range(7):
            if i<3:
                atoms[j,i]=int(record[i])
            else:
                atoms[j,i]=float(record[i])
    return atoms

def readBonds(filename):
    input = open(filename,"r")
    print("reading file {}".format(filename))
    currentId=0
    line = input.readline()
    out = line.find("bonds")
    while(out==-1):
        line = input.readline()
        out = line.find("bonds")
    print(line)
    numwords = line.split()
    numbonds = int(numwords[0])
    bonds = np.zeros((numbonds,4))
    while(input.readline().find("Bonds")==-1):
        continue
    input.readline()
    line=input.readline
    for j in range(numbonds):
        line=input.readline()
        record = line.split()
        for i in range(4):
            bonds[j,i]=int(record[i])
    return bonds

def readAngles(filename):
    input = open(filename,"r")
    print("reading file ".format(filename))
    currentId=0
    line = input.readline()
    out = line.find("angles")
    while(out==-1):
        line = input.readline()
        out = line.find("angles")
    print(line)
    numwords = line.split()
    numangles = int(numwords[0])
    angles = np.zeros((numangles,5))
    while(input.readline().find("Angles")==-1):
        continue
    input.readline()
    line=input.readline
    for j in range(numangles):
        line=input.readline()
        record = line.split()
        for i in range(5):
            angles[j,i]=int(record[i])
    return angles

def readDihedrals(filename):
    input = open(filename,"r")
    print("reading file ".format(filename))
    currentId=0
    line = input.readline()
    out = line.find("dihedrals")
    while(out==-1):
        line = input.readline()
        out = line.find("dihedrals")
    print(line)
    numwords = line.split()
    numdiheds = int(numwords[0])
    diheds = np.zeros((numdiheds,6))
    while(input.readline().find("Dihedrals")==-1):
        continue
    input.readline()
    line=input.readline
    for j in range(numdiheds):
        line=input.readline()
        record = line.split()
        for i in range(6):
            diheds[j,i]=int(record[i])
    return diheds

def readAll(inputfile):
    atoms=readAtoms(inputfile)
    bonds=readBonds(inputfile)
    angles=readAngles(inputfile)
    diheds=readDihedrals(inputfile)
    return (atoms,bonds,angles,diheds)
