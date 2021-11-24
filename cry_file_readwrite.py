#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 19 18:28:28 2021

@authors: brunocamino
"""

class Crystal_input:
    #This creates a crystal_input object
    
    def __init__(self,input_name):
        import sys
        
        self.name = input_name
        try: 
            if input_name[-3:] != 'd12':
                input_name = input_name+'.d12'
            file = open(input_name, 'r')
            data = file.readlines()
            file.close()
        except:
            print('EXITING: a .d12 file needs to be specified')
            sys.exit(1)
        
        end_index = [i for i, s in enumerate(data) if 'END' in s]
        
        self.geom_block = []
        #self.optgeom_block = []
        self.bs_block = []
        self.func_block = []
        self.scf_block = []
        

        if len(end_index) == 4:
            self.geom_block = data[:end_index[0]+1]
            #self.optgeom_block = []
            self.bs_block = data[end_index[0]+1:end_index[1]+1]
            self.func_block = data[end_index[1]+1:end_index[2]+1]
            #The following loop ensures that keyword+values (such as TOLINTEG 7 7 7 7 14
            #are written as a list)
            for i in range(end_index[2]+1,end_index[-1]):
                if data[i+1][0].isnumeric():
                    self.scf_block.append([data[i],data[i+1]])
                else:
                    if data[i][0].isalpha():
                        self.scf_block.append(data[i])
                    else:
                        pass
            self.scf_block.append('ENDSCF\n') #The loop cannot go over the last element
            #This is the old one, remove if not needed: self.scf_block = data[end_index[2]+1:]
        elif len(end_index) == 5:
            self.geom_block = data[:end_index[1]+1]
            #self.optgeom_block = data[end_index[0]+1:end_index[1]+1]
            self.bs_block = data[end_index[1]+1:end_index[2]+1]
            self.func_block = data[end_index[2]+1:end_index[3]+1]
            #The following loop ensures that keyword+values (such as TOLINTEG 7 7 7 7 14
            #are written as a list)
            for i in range(end_index[3]+1,end_index[-1]):
                if data[i+1][0].isnumeric():
                    self.scf_block.append([data[i],data[i+1]])
                else:
                    if data[i][0].isalpha():
                        self.scf_block.append(data[i])
                    else:
                        pass
            self.scf_block.append('ENDSCF\n') #The loop cannot go over the last element
            
            

       
'''TESTING
mgo = crystal_input('data/mgo.d12')     
#print(mgo.name)
print(mgo.scf_block)
#mgo.scf_block.remove('DIIS\n')
#print(mgo.scf_block)'''

class Crystal_output:
#This class reads a CRYSTAL output and generates an object
    
    def __init__(self,output_name):
        
        import sys
        import re
        
        self.name = output_name
        #Check if the file exists
        try: 
            if output_name[-3:] != 'out' and  output_name[-4:] != 'outp':
                output_name = output_name+'.out'
            file = open(output_name, 'r')
            self.data = file.readlines()
            file.close()
        except:
            print('EXITING: a .out file needs to be specified')
            sys.exit(1)

        #Check the calculation converged
        self.converged = False
        
        for i,line in enumerate(self.data[::-1]):
            if re.match(r'^ EEEEEEEEEE TERMINATION',line):
                self.converged = True
                #This is the end of output
                self.eoo = len(self.data)-1-i
                break

        
        if self.converged == False:
            self.eoo = len(self.data)
            print('WARNING: the calculation did not converge. Proceed with care!')

            
        
        
    def final_energy(self): 
        
        import re
        
        self.energy = None
        for line in self.data[self.eoo::-1]:
            if re.match(r'\s\W OPT END - CONVERGED',line) != None:
                self.energy = float(line.split()[7])*27.2114
            elif re.match(r'^ == SCF ENDED',line) != None:
                self.energy =  float(line.split()[8])*27.2114 
        
        if self.energy == None:
            print('WARNING: no final energy found in the output file. energy = None')
        
        return self.energy

    
    def fermi_energy(self):

        import re
        
        self.efermi = None
        
        for i,line in enumerate(self.data[len(self.data)::-1]):     
            #This is in case the .out is from a DOSS calculation
            if re.match(r'^ TTTTTTTTTTTTTTTTTTTTTTTTTTTTTT BAND',self.data[len(self.data)-(i+4)]) != None:
                for j,line1 in enumerate(self.data[len(self.data)-i::-1]):
                    if re.match(r'^ ENERGY RANGE ',line1):
                        self.efermi = float(line1.split()[7])*27.2114  
                        #Define from what type of calcualtion the Fermi energy was exctracted
                        self.efermi_from = 'band'
                        break
            #This is in case the .out is from a DOSS calculation  
            if re.match(r'^ TTTTTTTTTTTTTTTTTTTTTTTTTTTTTT DOSS',self.data[len(self.data)-(i+4)]) != None:
                for j,line1 in enumerate(self.data[len(self.data)-i::-1]):
                    if re.match(r'^ N. OF SCF CYCLES ',line1):
                        self.efermi = float(line1.split()[7])*27.2114  
                        #Define from what type of calcualtion the Fermi energy was exctracted
                        self.efermi_from = 'doss'
                        break
            #This is in case the .out is from a sp/optgeom calculation
            #For non metals think about top valence band
            else:      
                for j,line1 in enumerate(self.data[:i:-1]):
                    if re.match(r'^   FERMI ENERGY:',line1) != None:
                        self.efermi = float(line1.split()[2])*27.2114
                        self.efermi_from = 'scf'
                        break
        
        if self.efermi == None:
            print('WARNING: no Fermi energy found in the output file. efermi = None')

        return self.efermi
            
    def primitive_lattice(self,initial=True):
        #Initial = False reads the last lattice vectors. Useful in case of optgeom
        import re
        import numpy as np
        
        lattice = []
        if initial == True:
            for i,line in enumerate(self.data):
                if re.match(r'^ DIRECT LATTICE VECTORS CARTESIAN',line):
                    for j in range(i+2,i+5):
                        lattice_line = [float(n) for n in self.data[j].split()]
                        lattice.append(lattice_line)
                    self.primitive_vectors = np.array(lattice)
                    break
        elif initial == False:
            for i,line in enumerate(self.data[::-1]):                
                if re.match(r'^ DIRECT LATTICE VECTORS CARTESIAN',line):
                    for j in range(len(self.data)-i+1,len(self.data)-i+4):
                        print(self.data[j])
                        lattice_line = [float(n) for n in self.data[j].split()]
                        lattice.append(lattice_line)
                    self.primitive_vectors = np.array(lattice)
                    break
        
        if lattice == []:
            print('WARNING: no lattice vectors found in the output file. lattice = []')
        
        return self.primitive_vectors
    
    def reciprocal_lattice(self,initial=True):
        import re
        import numpy as np
        
        lattice = []
        if initial == True:
            for i,line in enumerate(self.data):
                if re.match(r'^ DIRECT LATTICE VECTORS COMPON. \(A.U.\)',line):
                    for j in range(i+2,i+5):
                        lattice_line = [float(n)/0.52917721067121 for n in self.data[j].split()[3:]]
                        lattice.append(lattice_line)
                    self.reciprocal_vectors = np.array(lattice)
                    return self.reciprocal_vectors
        elif initial == False:
            for i,line in enumerate(self.data[::-1]):
                if re.match(r'^ DIRECT LATTICE VECTORS COMPON. \(A.U.\)',line):
                    for j in range(len(self.data)-i+1,len(self.data)-i+4):
                        lattice_line = [float(n)/0.52917721067121 for n in self.data[j].split()[3:]]
                        lattice.append(lattice_line)
                    self.reciprocal_vectors = np.array(lattice)
                    return self.reciprocal_vectors
            

    def band_gap(self):#,spin_pol=False):
        import re
        import numpy as np
        
        self.spin_pol = False
        for line in self.data:
            if re.match(r'^ SPIN POLARIZED',line):
                self.spin_pol = True
                break
                
  
        for i, line in enumerate(self.data[len(self.data)::-1]):
            if self.spin_pol == False:
                if re.match(r'^\s\w+\s\w+ BAND GAP',line):
                    self.band_gap = float(line.split()[4])
                    return self.band_gap
                elif re.match(r'^\s\w+ ENERGY BAND GAP',line):
                    self.band_gap = float(line.split()[4])
                    return self.band_gap
                elif re.match(r'^ POSSIBLY CONDUCTING STATE',line):
                    self.band_gap = False
                    return self.band_gap 
            else:
                #This might need some more work
                band_gap_spin = []
                if re.match(r'\s+ BETA \s+ ELECTRONS',line):
                    band_gap_spin.append(float(self.data[len(self.data)-i-3].split()[4]))
                    band_gap_spin.append(float(self.data[len(self.data)-i+3].split()[4]))
                    self.band_gap = np.array(band_gap_spin)
                    return self.band_gap
        if band_gap_spin == []:
            print('DEV WARNING: check this output and the band gap function in code_io')
                #elif re.match(r'^\s\w+ ENERGY BAND GAP',line1) != None:
                    #band_gap = [float(data[len(data)-i-j-7].split()[4]),float(line1.split()[4])]

    def extract_last_geom(self,write_gui_file=False,print_cart=False):
        import re
        #from visualisation_tools import out2cif
        from mendeleev import element
        import numpy as np
        import sys
        
        self.opt_converged = False
        for line in self.data:
            if re.match(r'^  FINAL OPTIMIZED GEOMETRY',line):
                self.opt_converged = True
                break
        
        for i,line in enumerate(self.data):
            if re.match(r' TRANSFORMATION MATRIX PRIMITIVE-CRYSTALLOGRAPHIC CELL',line):
                trans_matrix_flat = [float(x) for x in self.data[i+1].split()]
                break
        self.trans_matrix = []
        for i in range(0,len(trans_matrix_flat),3):
            self.trans_matrix.append(trans_matrix_flat[i:i+3])
        self.trans_matrix = np.array(self.trans_matrix)
            
            
            
        for i,line in enumerate(self.data[len(self.data)::-1]):
            if re.match(r'^ T = ATOM BELONGING TO THE ASYMMETRIC UNIT',line):
                self.n_atoms = int(self.data[len(self.data)-i-3].split()[0])
                self.atom_positions = [] 
                self.atom_symbols = []
                self.atom_numbers = []
                for j in range(self.n_atoms):
                    atom_line = self.data[len(self.data)-i-2-int(self.n_atoms)+j].split()[3:]
                    self.atom_symbols.append(str(atom_line[0]) )
                    self.atom_positions.append([float(x) for x in atom_line[1:]])
                a,b,c,alpha,beta,gamma = self.data[len(self.data)-i-2-int(self.n_atoms)-5].split()
                #DELout2cif(file_name,a,b,c,alpha,beta,gamma,atom_positions)
                #DELout_name = str(file_name[:-4]+'.cif')
                for atom in self.atom_symbols:    
                    self.atom_numbers.append(element(atom.capitalize()).atomic_number)
                
                
                #Write the gui file 
                #This is a duplication from write_gui, but the input is different
                #It requires both the output and gui files with the same name and in the same directory
                if self.name[-3:] == 'out':
                    gui_file = self.name[:-4]+'.gui'
            
                elif self.name[-4:] == 'outp':
                    gui_file = self.name[:-5]+'.gui'
                else:
                    gui_file = self.name+'.gui'
                
                try:   
                    file = open(gui_file, 'r')
                    gui_data = file.readlines()
                    file.close()
                except:
                    print('EXITING: a .gui file with the same name as the input need to be present in the directory.')
                    sys.exit(1)
                    
                #Replace the lattice vectors with the optimised ones
                for i,vector in enumerate(self.primitive_lattice(initial=False).tolist()):
                    gui_data[i+1]= ' '.join([str(x) for x in vector])+'\n'

                n_symmops = int(gui_data[4])
                for i in range(len(self.atom_numbers)):
                    gui_data[i+n_symmops*4+6] = '{} {}\n'.format(self.atom_numbers[i],' '.join(str(x) for x in self.atom_positions[i][:]))
                
                with open(gui_file[:-4]+'_last.gui','w') as file:
                    for line in gui_data:
                        file.writelines(line)
                    
                    
                
                #THIS WRITES A GUI WITH WRONG SYMMOPS - MULTIPLY BY THE TRANSFORMATION MATRIX
                #I am leaving it here in case in the future I want to do some more work on this
                #Write the gui file 
                #This is a duplication from write_gui, but the input is different
                '''if self.name[-3:] == 'out':
                    gui_file = self.name[:-4]+'_last.gui'
            
                elif self.name[-4:] == 'outp':
                    gui_file = self.name[:-5]+'_last.gui'
                else:
                    gui_file = self.name+'_last.gui'
                
                with open(gui_file, 'w') as file:    

                    #First line (FIND WHAT THE FIRST LINE IS)
                    file.writelines('3   5   6\n')
                    
                    #Cell vectors
                    for vector in self.primitive_lattice():
                        file.writelines(' '.join(str(n) for n in vector)+'\n')
                    
                    #Get the symmops
                    self.symm_ops() 
                    
                    #N symm ops
                    file.writelines('{}\n'.format(self.n_symmpos))
                    
                    #symm ops
                    symmops_flat_list = [item for sublist in self.symmops for item in sublist]
                    for i in range(0,self.n_symmpos*12,3):
                        file.writelines('{}\n'.format(' '.join(symmops_flat_list[i:i+3])))
                    
                    #Multiply by the trans matrix
                    rot_ops = []
                    
                        
                    
                    #N atoms
                    file.writelines('{}\n'.format(self.n_atoms))
                    
                    #atom number + coordinates cart
                    for i in range(self.n_atoms):
                        file.writelines('{} {}\n'.format(self.atom_numbers[i],' '.join(str(x) for x in self.atom_positions[i])))
                    
                    #space group + n symm ops
                    #I need to change this
                    self.space_group = 225
                    file.writelines('{} {}'.format(self.space_group,self.n_symmpos))
                return self.atom_positions'''
                #Write the gui file
                
                '''print('File %s written' % (out_name))
                
                if print_cart == True:
                    print('\n Cartesian coordinates:\n')
                    atoms[:,0] = atomic_numbers
                    if float(a) < 500:
                        atoms[:,1] = atoms[:,1].astype('float')*float(a)
                    if float(b) < 500:
                        atoms[:,2] = atoms[:,2].astype('float')*float(b)
                    if float(c) < 500:
                        atoms[:,3] = atoms[:,3].astype('float')*float(c)
                    
                    for i in atoms:
                        print(' '.join(i))
                return None'''
        
    def symm_ops(self):
        import re
        import numpy as np
        
        symmops = []

        for i,line in enumerate(self.data):
            if re.match(r'^ \*\*\*\*   \d+ SYMMOPS - TRANSLATORS IN FRACTIONAL UNITS',line):
                self.n_symmpos = int(line.split()[1])
                for j in range(0,self.n_symmpos):
                    symmops.append(self.data[i+3+j].split()[2:])
                self.symmops = np.array(symmops)
                
                return self.symmops
                
                
                
                
            
'''###TESTING
a = Crystal_output('data/mgo_optgeom.out')
print('final_energy\n',a.final_energy())
print('fermi\n',a.fermi_energy())
print('primitive\n',a.primitive_lattice(initial=False))
print('band_gap\n',a.band_gap())
print('spin\n',a.spin_pol)
print('reciprocal\n',a.reciprocal_lattice())
print('last geom\n',a.extract_last_geom())
#print('symmops\n',a.symm_ops())'''
