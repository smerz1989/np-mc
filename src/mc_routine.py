#!/usr/bin/python
import sys
import numpy as np
import string
from math import *
import random as rnd
from subprocess import call
from mc_library_rev3 import *
import time
from lammps import lammps
import read_lmp_rev6 as rdlmp
import itertools as itt
from ctypes import *
from scipy.stats import rv_discrete


def atom2xyz(filename,atoms):
	xyzfile = open(filename,'a')
	xyzfile.write(str(atoms.shape[0])+'\n\n')
	for atom in atoms:
		xyzfile.write(str(atom[2])+'\t'+str(atom[4])+'\t'+str(atom[5])+'\t'+str(atom[6])+'\n')

def initializeMols(atoms,bonds):
	ch3ID = 3
	sulfurID = 4
	oxygenID = 5

	ddtsulfurs = [atom[0] for atom in atoms if (atom[2]==sulfurID and (atom[1] in ddtMols))]
	meohsulfurs = [atom[0] for atom in atoms if (atom[2]==sulfurID and (atom[1] in meohMols))]

	ddts = np.empty([ddtMols.shape[0],13])
	meohs = np.empty([meohMols.shape[0],5])

	for idx,(ddtsulfur,meohsulfur) in enumerate(itt.izip_longest(ddtsulfurs,meohsulfurs)):
		if(not (ddtsulfur==None)):
			ddts[idx,:] = rdlmp.getMoleculeAtoms(bonds,ddtsulfur)
		if(not (meohsulfur==None)):
			meohs[idx,:] = rdlmp.getMoleculeAtoms(bonds,meohsulfur)
	return (ddts,meohs)

def calc_dih_angle(dih_atoms):
	b1 = dih_atoms[1,4:7]-dih_atoms[0,4:7]
	b2 = dih_atoms[2,4:7]-dih_atoms[1,4:7]
	b3 = dih_atoms[3,4:7]-dih_atoms[2,4:7]
	b4 = np.cross(b1,b2)
	b5 = np.cross(b2,b4)
	#b2norm = b2/np.linalg.norm(b2)
	#n1 = np.cross(b1,b2)/np.linalg.norm(np.cross(b1,b2))
	#n2 = np.cross(b2,b3)/np.linalg.norm(np.cross(b2,b3))
	#m1 = np.cross(n1,b2norm)
	#angle = atan2(np.dot(m1,n2),np.dot(n1,n2))
	#return angle if angle>0 else 2*pi+angle
	angle =  atan2(np.dot(b3,b4),np.dot(b3,b5)*sqrt(np.dot(b2,b2)))
	norm_angle = angle if angle>0 else 2*pi+angle
	return norm_angle

def rotate_dihedral(dih_atoms,angle,atoms2rotate):
	b2 = dih_atoms[2,4:7]-dih_atoms[1,4:7]
	b3 = dih_atoms[3,4:7]-dih_atoms[2,4:7]

	rot_axis = b2/np.linalg.norm(b2)
	init_vector = b3
	
	#n1 = np.cross((dih_atoms[1,4:7]-dih_atoms[0,4:7]),rot_axis)
	#n2 = np.cross((dih_atoms[3,4:7]-dih_atoms[2,4:7]),rot_axis)

	#init_angle = np.arccos(np.dot((n1/np.linalg.norm(n1)),(n2/np.linalg.norm(n2))))
	init_angle = calc_dih_angle(dih_atoms)

	rot_angle = -angle+init_angle
	#print "Initial angle is "+str(init_angle)+" desired angle is "+str(angle)+" therefore rotating "+str(rot_angle)
	skewmat = np.array([[0,-rot_axis[2],rot_axis[1]],[rot_axis[2],0,-rot_axis[0]],[-rot_axis[1],rot_axis[0],0]])
	rot_matrix = np.identity(3)+sin(rot_angle)*skewmat+(2*sin(rot_angle/2)**2)*np.linalg.matrix_power(skewmat,2)
	
	#print "\nDihedral atoms looks like this "+str(dih_atoms[:,4:7])+"\n"
	for atom in atoms2rotate:	
		atom[4:7] = atom[4:7] - dih_atoms[1,4:7]
		atom[4:7] = np.transpose(np.dot(rot_matrix,np.transpose(atom[4:7])))+dih_atoms[1,4:7]
	#print "\nNow dihedral atoms looks like this "+str(dih_atoms[:,4:7])+"\n"
	return atoms2rotate

def update_coords(atoms,lmp):
	coords = lmp.gather_atoms("x",1,3)
	for idx in xrange(atoms.shape[0]):
		coords[idx*3]=atoms[idx,4]
		coords[idx*3+1]=atoms[idx,5]
		coords[idx*3+2]=atoms[idx,6]
	lmp.scatter_atoms("x",1,3,coords)

def delete_chain(mol,delindex,lmp,delete=True):
	if(delete):	
		atoms2del = mol[delindex:].astype(int)
		lmp.command("group restOfchain id "+(" ".join([str(atom) for atom in atoms2del])))
		lmp.command("neigh_modify exclude group restOfchain all")
		lmp.command("delete_bonds restOfchain multi any")
		lmp.command("group restOfchain delete")
	else:
		lmp.command("neigh_modify exclude none")
		lmp.command("group beginOfchain id "+(" ".join([str(atom) for atom in mol[0:(delindex+1)].astype(int)])))
		if(delindex<(mol.shape[0]-1)):	
			lmp.command("group restOfchain id "+(" ".join([str(atom) for atom in mol[(delindex+1):].astype(int)])))
			lmp.command("neigh_modify exclude group restOfchain all")
		lmp.command("delete_bonds beginOfchain multi undo")
                lmp.command("group beginOfchain delete")
		if(delindex<(mol.shape[0]-1)):
			lmp.command("group restOfchain delete")

def regrow_chain(atoms,mol,beta,lmp,dih_cdf,startindex,numtrials,keep_original=False):
	totalstart = time.time()
	delete_chain(mol,startindex,lmp,delete=True)
	weight1=1
	actual_trials = numtrials-1 if keep_original else numtrials
	mol_id = int(atoms[np.where((atoms[:,0]==mol[0]))][0,1])
	lmp.command("group cbmc_mol molecule "+str(mol_id))
	lmp.command("group all_else subtract all cbmc_mol")
	for idx in xrange(startindex,len(mol)):
		start = time.time()
		delete_chain(mol,idx,lmp,delete=False)
		lmp.command("neigh_modify exclude group all_else all_else")
		lmp.command("run 1 post no")
		energy = lmp.extract_compute("pair_pe",0,0)
		if(idx>2):
			probs = np.empty((numtrials))
			positions = np.empty((numtrials,(mol.shape[0]-idx),3))
			dih_atoms = atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[(idx-3):(idx+1)]]).flatten()]
			original_pos = np.copy(atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[idx:]]).flatten(),4:7])
			chosen_pos = 0
			atoms2rotate = atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[idx:]]).flatten()]
			print "Starting angle is "+str(calc_dih_angle(dih_atoms))+" and starting energy is "+str(energy)+"\n\n"
			if(keep_original):
				lmp.command("run 1 post no")
				delta_pe = lmp.extract_compute("pair_pe",0,0)-energy
				print "Angle is original, pe is "+str(lmp.extract_compute("pair_pe",0,0))+" delpe is "+str(delta_pe)+"\n"
				probs[numtrials-1] = exp(-beta*delta_pe) if -beta*delta_pe<700 else float('inf')
			finish = time.time()
			#print "Initialization time is "+str(finish-start)
			start = time.time()
			for i in xrange(actual_trials):
				chosen_index = np.searchsorted(dih_cdf[:,1],rnd.uniform(0,1))
				angle = dih_cdf[chosen_index,0]
				print "Chosen angle is "+str(angle)
				positions[i,:,:] = rotate_dihedral(dih_atoms,angle,atoms2rotate)[:,4:7]
				for count,position in enumerate(positions[i]):
					atoms[np.where(atoms[:,0]==mol[idx+count])[0],4:7] = position
				dih_atoms = atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[(idx-3):(idx+1)]]).flatten()]
				update_coords(atoms,lmp)
				#print "Rotate atoms in cbmc are: "+str(atoms2rotate[:,4:7])
				lmp.command("run 1 post no")
				delta_pe = lmp.extract_compute("pair_pe",0,0)-energy
				print "Angle is now "+str(calc_dih_angle(dih_atoms))+" pe is "+str(lmp.extract_compute("pair_pe",0,0))+" delpe is "+str(delta_pe)+"\n"
				probs[i] = exp(-beta*(delta_pe)) if -beta*(delta_pe)<700 else float('inf')
				for count,position in enumerate(original_pos):
					atoms[np.where(atoms[:,0]==mol[idx+count])[0],4:7] = position
				dih_atoms = atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[(idx-3):(idx+1)]]).flatten()]
				#print "Should be back to starting angle "+str(calc_dih_angle(dih_atoms))
			finish = time.time()
			#print "Evaluating trials takes "+str(finish-start)
			print "Probabilities are "+str(probs)
			if(keep_original):
				for count,position in enumerate(original_pos):
                                        atoms[np.where(atoms[:,0]==mol[idx+count])[0],4:7] = position
			else:
				angle_cdf = np.cumsum(probs)/np.sum(probs)
				chosen_pos = np.searchsorted(angle_cdf,rnd.uniform(0,1))
				for count,position in enumerate(positions[chosen_pos][0]):
					atoms[np.where(atoms[:,0]==mol[idx+count])[0],4:7] = position
			update_coords(atoms,lmp)
			#lmp.command("run 1 post no")
		stepweight=np.sum(probs) if idx>2 else 1
		weight1*=stepweight
	lmp.command("neigh_modify exclude none")
	totalfinish = time.time()
	print "Total regrow time is "+str(totalfinish-totalstart)
	return (weight1,atoms[np.array([np.where(atoms[:,0]==atom)[0] for atom in mol[idx:]]).flatten(),4:7])
			


def cbmc(atoms,mol,beta,lmp,dih_cdf,startindex):
	molId = atoms[atoms[:,0]==mol[0]][0,1]
	#print "Mol id is "+str(molId)
	numtrials = 5
	#startindex = rnd.choice(range(1,len(mol)))
	atoms2del = mol[startindex:].astype(int)
	#print "Atoms to delete are "+str(atoms2del)
	#delete_chain(mol,startindex,lmp,delete=True)
	#lmp.command("run 1 post no")
	#initial_energy = lmp.extract_compute("thermo_pe",0,0)
	#energy = initial_energy
	(weight0,new_positions) = regrow_chain(atoms,mol,beta,lmp,dih_cdf,startindex,numtrials,keep_original=True)
	(weight1,new_positions) = regrow_chain(atoms,mol,beta,lmp,dih_cdf,startindex,numtrials)
	acceptance_prob = weight1/weight0 if weight0>0 else float('inf')
	print "Weight1 is "+str(weight1)+" weight0 is "+str(weight0)
	if(rnd.uniform(0,1)>acceptance_prob):
		return False
	else:
		return True

if __name__ == "__main__":
	T=298
	kb = 0.0019872041
	beta = 1/(kb*T)
	tries = 200000
	agID = 1
	ch2ID = 2
	ch3ID = 3
	sulfurID = 4
	oxygenID = 5
	hydrogenID = 6

	centerRotation = [40.9,40.9,40.9]
	rotationtype = 'align'

	potentialfile = open('Potential_Energy.txt','w')
	potentialfile.write('Step\tPotential (kcal/mol)\n')

	acceptancefile = open('Acceptance_Rates.txt','w')
	acceptancefile.write('Step\t#Swaps\tRate\t#Rotations\tRate\t#CBMC\tRate\n')

	dih_potential = np.loadtxt("dih_potential_1",skiprows=1)
	dih_cdf = np.cumsum(np.exp(-beta*dih_potential[:,1]))
	dih_cdf_norm = dih_cdf/dih_cdf[dih_cdf.shape[0]-1]
	dih_cdf_norm = np.hstack((dih_potential[:,0].reshape((dih_cdf.shape[0],1)),dih_cdf_norm.reshape((dih_cdf.shape[0],1))))
	max_angle = 0.34906585
	inputfile = 'addmolecule_184_rand.lmp'
	(atoms,bonds,angles,dihedrals) = rdlmp.readAll(inputfile)
	natoms = atoms.shape[0]
	molIDs = atoms[np.where(atoms[:,2]==sulfurID)][:,1]
	ddtMols = atoms[np.where(atoms[:,2]==ch3ID)][:,1]
	meohMols = atoms[np.where(atoms[:,2]==oxygenID)][:,1]

	(ddts,meohs) = initializeMols(atoms,bonds)

	lmp = lammps("",["-echo","none","-screen","lammps.out"])
	#lmp = lammps("",["-echo","none"])
	lmp.file("ddt_me_200.lmi")
	lmp.command("compute pair_pe all pe pair")
	pe = lmp.extract_compute("thermo_pe",0,0)

	lmp.command("neigh_modify exclude type 1 1")
	coords = lmp.gather_atoms("x",1,3)
	atoms = atoms[atoms[:,0].argsort()]
	loop_start = time.time()
	swaps=0
	swaps_accepted=0
	rotates=0
	rotates_accepted=0
	cbmcs=0
	cbmcs_accepted=0
	for i in xrange(tries):
		#iter_start = time.time()
		pe_old = pe
		atoms_old = np.copy(atoms)
		coord_old = coords
		move = rnd.choice(['swap'])
		if((i+1)%100==0):
			acceptancefile.write(str(i)+'\t'+str(swaps)+'\t'+str(float(swaps_accepted)/float(swaps))+'\t'+str(rotates)+'\t'+str(float(rotates_accepted)/float(rotates))+'\t'+str(cbmcs)+'\t'+str(float(cbmcs_accepted)/float(cbmcs))+'\n')
			swaps=0
			swaps_accepted=0
			rotates=0
			rotates_accepted=0
			cbmcs=0
			cbmcs_accepted=0
		if(move=='swap'):
			swaps+=1
			print "swapping"
			ddtmol = rnd.choice(ddts)
			meohmol = rnd.choice(meohs)
			ddtmol_id = atoms[(atoms[:,0]==ddtmol[0])][:,1]
			meohmol_id = atoms[(atoms[:,0]==meohmol[0])][:,1]
			#ddtmol_id = rnd.choice(ddtMols)
			#meohmol_id = rnd.choice(meohMols)
			swapMolecules(ddtmol_id,meohmol_id,atoms,centerRotation,rotationtype)
			ddt_accepted = cbmc(atoms,ddtmol,beta,lmp,dih_cdf_norm,3)
			meoh_accepted = cbmc(atoms,meohmol,beta,lmp,dih_cdf_norm,3)
			
		elif(move=='rotate'):
			rotates+=1
			print "rotating"
			molId = rnd.choice(molIDs)
			randomRotate(atoms,molId,max_angle)
		elif(move=='cbmc'):
			cbmcs+=1
			print "\n\nCBMC Move\n\n"
			mols = rnd.choice((ddts,meohs))
			mol = rnd.choice(mols)
			startindex = rnd.choice(np.arange(1,len(mol)))
			accepted = cbmc(atoms,mol,beta,lmp,dih_cdf_norm,startindex)
			if(accepted):
				cbmcs_accepted+=1
				print "Move accepted"
				pe = lmp.extract_compute("thermo_pe",0,0)
				print "\nOn loop "+str(i)+"\n"
				continue
			else:
				print "Move rejected"
				pe = pe_old
				atoms = atoms_old
				print "\nOn loop "+str(i)+"\n"
				continue
		#for idx in xrange(natoms):
		#	coords[idx*3]=atoms[idx,4]
		#	coords[idx*3+1]=atoms[idx,5]
		#	coords[idx*3+2]=atoms[idx,6]
		#lmp.scatter_atoms("x",1,3,coords)
		update_coords(atoms,lmp)
		lmp.command("run 1 pre no post no")
		pe = lmp.extract_compute("thermo_pe",0,0)
		print "On loop: "+str(i)
		lmp.command("write_dump all xyz ddt_me_200.xyz modify append yes")
		print "Delta PE is "+str(pe-pe_old)
		if((pe<=pe_old) or (exp(-beta*(pe-pe_old))>rnd.uniform(0,1))):
			print "Move accepted"
			if(move=='rotate'):
				rotates_accepted+=1
			else:
				swaps_accepted+=1
		else:
			print "Move rejected"
			atoms = atoms_old
			pe = pe_old
		potentialfile.write(str(i)+'\t'+str(pe)+'\n')
		#raw_input("continue?")
		#iter_end = time.time()
		if(((i+1)%100)==0):
			iter_end = time.time()
			print "Total time is "+str(iter_end-loop_start)+" average iteration time is "+str((iter_end-loop_start)/(i+1.0))
	lmp.close()
	loop_end=time.time()-loop_start
