#!/home/snm8xf/anaconda/bin/python
import read_lmp_rev6 as rdlmp
import numpy as np
from math import *
#import matplotlib.pyplot as plt
import sys
import random as rnd
import networkx as nwkx

def getDist(atom1,atom2):
	dist = sqrt((atom1[0,4]-atom2[0,4])**2+(atom1[0,5]-atom2[0,5])**2+(atom1[0,6]-atom2[0,6])**2)

def getNN(atoms,atom,cutoff):
	atoms[:,3] = np.sqrt((atom[0,4]-atoms[:,4])**2+(atom[0,5]-atoms[:,5])**2+(atom[0,6]-atoms[:,6])**2)
	nns = atoms[np.where((atoms[:,3]<=cutoff))[0]]
	#print "Nearest neighbors of atom "+str(atom[0,1])+" are "+str(atoms[:,1][np.where((atoms[:,3]<=cutoff))[0]])
	return nns

def maxCluster(clusters,atoms):
	maxsize=0
	maxcluster=-1
	for cluster in clusters:
		size=atoms[(atoms[:,7]==cluster)].shape[0]
		#print "Size of cluster "+str(cluster)+" is "+str(size)
		if(size>maxsize):
			maxsize=size
			maxcluster=cluster
	#print "The determined max size is "+str(maxsize)+" of cluster "+str(maxcluster)
	return maxcluster	

def changeCluster(newcluster,oldcluster,atoms):
	#print "New cluster contained: "+str(atoms[:,1][np.where((atoms[:,7]==newcluster))[0]])
	#print "Old cluster contained: "+str(atoms[:,1][np.where((atoms[:,7]==oldcluster))[0]])
	atoms[:,7][np.where((atoms[:,7]==oldcluster))[0]]=newcluster
	#print "New cluster contains: "+str(atoms[:,1][np.where((atoms[:,7]==newcluster))[0]])

def createGraph(atoms,cutoff):
	DG = nwkx.DiGraph()
	DG.add_nodes_from(atoms[:,1])
	for mol in atoms[:,1]:
		nns = getNN(atoms,atoms[(atoms[:,1]==mol)],cutoff)
		connections = [(mol,x,getDist(atoms[(atoms[:,1]==x)],atoms[(atoms[:,1]==mol)])) for x in nns[:,1] if x!=mol]
		DG.add_weighted_edges_from(connections)
	return DG	

if __name__ == "__main__":
	ch3Id = 3
	filename=sys.argv[1]
	cluster_xyzfile = open("cluster.xyz",mode='w')
	atoms = rdlmp.readAtoms(filename)
	distCrit=float(sys.argv[2])
	
	#Find CH3 atoms
	ch3s = atoms[(atoms[:,2]==ch3Id)]
	label_init = np.full((ch3s.shape[0],1),-1)
	
	#Append blank cluster labels
	newch3s = np.append(ch3s,label_init,axis=1)
	clusternumber=1

	directed_graph = createGraph(newch3s,distCrit)	

	indegree=0
	outdegree=0
	print "Number of clusters is "+str(nwkx.number_strongly_connected_components(directed_graph))
	print "Average cluster size is "+str(float(newch3s.shape[0])/float(nwkx.number_strongly_connected_components(directed_graph)))
	sorted_clusters = sorted(nwkx.strongly_connected_components(directed_graph),key=len,reverse=True)
	sizes = [len(x) for x in sorted_clusters]
	print "Median cluster size is "+str(np.median(sizes))
	print "Max cluster size is "+str(np.amax(sizes))
	
	cluster_xyzfile.write(str(newch3s.shape[0])+"\n\n")
	cluster_num=0
	for cluster in sorted_clusters:
		cluster_num+=1
		for mol in cluster:
			curatom = newch3s[(newch3s[:,1]==mol)]
			cluster_xyzfile.write(str(cluster_num)+"\t"+str(curatom[0,4])+"\t"+str(curatom[0,5])+"\t"+str(curatom[0,6])+"\n")




