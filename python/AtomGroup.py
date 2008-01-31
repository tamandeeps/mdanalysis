"""AtomGroup Hierarchy

Class Hierarchy:
    AtomGroup ->
"""

import numpy

class Atom(object):
    """A single atom definition

Data: number, segid, resid, resname, name, type

Methods:
    a = Atom()
"""
    __slots__ = ("number", "id", "name", "type", "resname", "resid", "segid", "mass", "charge", "residue", "segment", "bonds", "__universe")

    def __init__(self, number, name, type, resname, resid, segid, mass, charge):
        self.number = number
        self.name = name
        self.type = type
        self.resname = resname
        self.resid = resid
        self.segid = segid
        self.mass = mass
        self.charge = charge
    def __repr__(self):
        return "< Atom " + repr(self.number+1) + ": name " + repr(self.name) +" of type " + \
               repr(self.type) + " of resname " + repr(self.resname) + ", resid " +repr(self.resid) + " and segid " +repr(self.segid)+'>'
    def __cmp__(self, other):
        return cmp(self.number, other.number)
    def __eq__(self, other):
        return self.number == other.number
    def __hash__(self):
        return hash(self.number)
    def __add__(self, other):
        if not (isinstance(other, Atom) or isinstance(other, AtomGroup)):
            raise TypeError('Can only concatenate Atoms (not "'+repr(other.__class__.__name__)+'") to AtomGroup')
        if isinstance(other, Atom): return AtomGroup([self, other])
        else: return AtomGroup([self]+other.atoms)

    def pos():
        def fget(self):
            return self.universe.coord[self.number] # PDB numbering starts at 0
        return locals()
    pos = property(**pos())

    def universe():
        doc = "a pointer back to the Universe"
        def fget(self):
            if not self.__universe == None: return self.__universe
            else: raise AttributeError("Atom "+repr(self.number)+" is not assigned to a Universe")
        def fset(self, universe):
            self.__universe = universe
        return locals()
    universe = property(**universe())

class NameError(Exception):
    pass

class AtomGroup(object):
    """A group of atoms

Currently contains a list of atoms from the main system that correspond to this group.

Data: atoms - a list of references to the corresponding atoms in Universe.atoms
      AtomGroups are immutable

Methods:
    ag = universe.selectAtoms("...")
    ag.indices() - return indices into main atom array
    ag.masses() - array of masses
    ag.totalMass() - total mass
    ag.charges() - array of charges
    ag.totalCharge() - total charge
    ag.centerOfGeometry() - center of geometry
    ag.centerOfMass() - center of mass
    ag.radiusOfGyration() - radius of gyration
    ag.principleAxis() - returns the principle axis of rotation
    c = ag.coordinates() - return array of coordinates
"""
    def atoms():
        doc = "a list of references to atoms in Universe corresponding to a specifies subset"
        def fget(self):
            return self.__atoms
        return locals()
    atoms = property(**atoms())
    
    def _atoms():
        def fget(self):
            import warnings
            warnings.warn("Usage of '_atoms' is deprecated. Use 'atoms' instead.", category=DeprecationWarning, stacklevel=2)
            return self.__atoms
        return locals()
    _atoms = property(**_atoms())

    def __init__(self, atoms):
        if len(atoms) < 1: raise Exception("No atoms defined for AtomGroup")
        # __atoms property is effectively readonly
        self.__atoms = atoms
        # If the number of atoms is very large, create a dictionary cache for lookup
        if len(atoms) > 10000:
            self._atom_cache = dict([(x,None) for x in atoms])
    def __len__(self):
        import warnings
        warnings.warn("To prevent confusion with AtomGroup subclasses you should use numberOfAtoms() instead", category=Warning, stacklevel=2)
        return self.numberOfAtoms()
    def __getitem__(self, item):
        if (numpy.dtype(type(item)) is numpy.dtype(int)) or (type(item) is slice):
            return self.atoms[item]
        else: return super(AtomGroup, self).__getitem__(item)
    def __getattr__(self, name):
        # There can be more than one atom with the same name
        atomlist = [atom for atom in self.atoms if name == atom.name]
        if len(atomlist) == 0: raise NameError("No atoms with name "+name)
        elif len(atomlist) == 1: return atomlist[0]
        else: return AtomGroup(atomlist)
    def __iter__(self):
        return iter(self.atoms)
    def __contains__(self, other):
        if hasattr(self, "_atom_cache"):
            return other in self._atom_cache
        else: return other in self.atoms
    def __add__(self, other):
        if not (isinstance(other, Atom) or isinstance(other, AtomGroup)):
            raise TypeError('Can only concatenate AtomGroup (not "'+repr(other.__class__.__name__)+'") to AtomGroup')
        if isinstance(other, AtomGroup): return AtomGroup(self.atoms + other.atoms)
        else: return AtomGroup(self.atoms+[other])
    def __repr__(self):
        return '<'+self.__class__.__name__+' with '+repr(self.numberOfAtoms())+' atoms>'
    def numberOfAtoms(self):
        return len(self.atoms)
    def indices(self):
        if not hasattr(self,'_cached_indices'):
            self._cached_indices = numpy.array([atom.number for atom in self.atoms])
        return self._cached_indices
    def masses(self):
        if not hasattr(self, "_cached_masses"):
            self._cached_masses = numpy.array([atom.mass for atom in self.atoms])
        return self._cached_masses
    def totalMass(self):
        return numpy.sum(self.masses())
    def charges(self):
        return numpy.array([atom.charge for atom in self.atoms])
    def totalCharge(self):
        return numpy.sum(self.charges())
    def centerOfGeometry(self):
        return numpy.sum(self.coordinates())/self.numberOfAtoms()
    def centerOfMass(self):
        return numpy.sum(self.coordinates()*self.masses()[:,numpy.newaxis])/self.totalMass()
    def radiusOfGyration(self):
        masses = self.masses()
        recenteredpos = self.coordinates() - self.centerOfMass()
        rog_sq = numpy.sum(masses*numpy.add.reduce(numpy.power(recenteredpos, 2), axis=1))/self.totalMass()
        return numpy.sqrt(rog_sq)
    def momentOfInertia(self):
        # Convert to local coordinates
        recenteredpos = self.coordinates() - self.centerOfMass()
        masses = self.masses()
        values = zip(masses, recenteredpos)
        # Create the inertia tensor
        # m_i = mass of atom i
        # (x_i, y_i, z_i) = pos of atom i
        # Ixx = sum(m_i*(y_i^2+z_i^2)); Iyy = sum(m_i*(x_i^2+z_i^2)); Izz = sum(m_i*(x_i^2+y_i^2))
        # Ixy = Iyx = -1*sum(m_i*x_i*y_i)
        # Ixz = Izx = -1*sum(m_i*x_i*z_i)
        # Iyz = Izy = -1*sum(m_i*y_i*z_i)
        Ixx = reduce(lambda t,a: t+a[0]*(a[1][1]*a[1][1]+a[1][2]*a[1][2]), values, 0.)
        Iyy = reduce(lambda t,a: t+a[0]*(a[1][0]*a[1][0]+a[1][2]*a[1][2]), values, 0.)
        Izz = reduce(lambda t,a: t+a[0]*(a[1][0]*a[1][0]+a[1][1]*a[1][1]), values, 0.)
        Ixy = Iyx = -1*reduce(lambda t,a: t+a[0]*a[1][0]*a[1][1], values, 0.)
        Ixz = Izx = -1*reduce(lambda t,a: t+a[0]*a[1][0]*a[1][2], values, 0.)
        Iyz = Izy = -1*reduce(lambda t,a: t+a[0]*a[1][1]*a[1][2], values, 0.)
        return numpy.array([[Ixx, Ixy, Ixz],[Iyx, Iyy, Iyz],[Izx, Izy, Izz]])
    def principleAxes(self):
        from numpy.linalg import eig
        eigenval, eigenvec = eig(self.momentOfInertia())
        # Sort
        indices = numpy.argsort(eigenval)
        return numpy.take(eigenvec, indices) 
    def coordinates(self, ts=None):
        if ts == None:
            ts = self.atoms[0].universe.coord
        return ts[self.indices()]

class Residue(AtomGroup):
    """A group of atoms corresponding to a residue

Data: type, name

Methods:
    r = Residue()
    r['name'] or r[id]
    r.name
"""
    __cache = {}
    def __init__(self, name, id, atoms):
        super(Residue, self).__init__(atoms)
        self.name = name
        self.id = id
        self.segment = None
        for i, a in enumerate(atoms):
            a.id = i
            a.residue = self
        # Should I cache the positions of atoms within a residue?
        if not Residue.__cache.has_key(name):
            Residue.__cache[name] = dict([(a.name, i) for i, a in enumerate(self.atoms)])
    def __getitem__(self, item):
        if (type(item) is int) or (type(item) is slice):
            return self.atoms[item]
        else: return self.__getattr__(item)
    def __getattr__(self, name):
        # There can only be one atom with a certain name
        # Use the cache
        #for atom in self.atoms:
        #    if (name == atom.name): return atom
        try:
            index = Residue.__cache[self.name][name]
            return self.atoms[index]
        except KeyError: raise NameError("No atom in residue "+self.name+" with name "+name)
    def __repr__(self):
        return '<'+self.__class__.__name__+' '+repr(self.name)+', '+repr(self.id)+'>'

class ResidueGroup(AtomGroup):
    """ A group of residues

Data: residues

Methods:
    rg = ResidueGroup()
"""
    def __init__(self, residues):
        self._residues = residues
        atoms = []
        for res in residues:
            atoms.extend(res.atoms)
        super(ResidueGroup, self).__init__(atoms)
    def __iter__(self):
        return iter(self._residues)
    def __len__(self):
        return len(self._residues)
    def __getitem__(self, item):
        if (type(item) is int) or (type(item) is slice):
            return self._residues[item]
        else: raise NotImplementedError()
    def __getattr__(self, attr):
        atomlist = [atom for atom in self.atoms if atom.name == attr]
        return AtomGroup(atomlist)
    def __repr__(self):
        return '<'+self.__class__.__name__+' '+repr(self._residues)+'>'

class Segment(ResidueGroup):
    """ A group of residues corresponding to one segment of the PSF

Data: name

Methods:
    s = Segment()

"""
    def __init__(self, name, residues):
        super(Segment, self).__init__(residues)
        self.name = name
        for res in self._residues:
            res.segment = self
            for atom in res:
                atom.segment = self
    def __getattr__(self, attr):
        if attr[0] == 'r':
            resnum = int(attr[1:])
            return self[resnum]
        else:
            # There can be multiple residues with the same name
            r = []
            for res in self._residues:
                if (res.name == attr): r.append(res)
            if (len(r) == 0): return super(Segment, self).__getattr__(attr)
            elif (len(r) == 1): return r[0]
            else: return ResidueGroup(r)
    def __repr__(self):
        return '<'+self.__class__.__name__+' '+repr(self.name)+'>'

class Universe(object):
    """Contains all the information decribing the system
       Built from a psf file

Data: bonds, angles, dihedrals, impropers, donors, acceptors

Methods:
   m = Universe(psffile, dcdfile) - read system from file(s)

See also:
"""
    def __init__(self, psffilename, dcdfilename=None):
        self.__dcd = None
        import PSFParser
        struc = PSFParser.parse(psffilename)
        #for data in struc.keys():
        #    setattr(self, data, struc[data])
        self.atoms = AtomGroup(struc["_atoms"])
        segments = PSFParser.build_segments(self.atoms)
        # Because of weird python rules, attribute names cannot start with a digit
        for seg in segments.keys():
            if seg[0].isdigit():
                newsegname = 's'+seg
                segments[newsegname] = segments[seg]
                del segments[seg]
        self.__dict__.update(segments)
        
        #PSFParser.build_bondlists(self.atoms, self._bonds)
        # Let atoms access the universe
        for a in self.atoms: a.universe = self
        if dcdfilename is not None: self.load_new_dcd(dcdfilename)
    def load_new_dcd(self, dcdfilename):
        from DCD import DCDReader
        self.dcd = DCDReader(dcdfilename)
        # Make sure that they both have the same number of atoms
        if (self.dcd.numatoms != self.atoms.numberOfAtoms()):
            raise Exception("The psf and dcd files don't have the same number of atoms!")
    def selectAtoms(self, sel, *othersel):
        # XXX This uses the outdated selection parser
        # You should be able to do everything else using classes in AtomGroup
        import Selection
        atomgrp = Selection.Parser.parse(sel).apply(self)
        if len(othersel) == 0: return atomgrp
        else:
            # Generate a selection for each selection string
            atomselections = [atomgrp]
            for sel in othersel:
                #atomgrp = atomgrp + Selection.Parser.parse(sel).apply(self)
                atomselections.append(Selection.Parser.parse(sel).apply(self))
            return tuple(atomselections)
    def __repr__(self):
        return '<'+self.__class__.__name__+' with '+repr(len(self.atoms))+' atoms>'

    # Properties
    def dimensions():
        def fget(self): return self.coord.dimensions
        return locals()
    dimensions = property(**dimensions())
    
    def coord():
        doc = "Reference to current coordinates of universe"
        def fget(self): return self.dcd.ts
        return locals()
    coord = property(**coord())

    def dcd():
        doc = "Reference to DCDReader object containing trajectory data"
        def fget(self):
            if not self.__dcd == None: return self.__dcd
            else: raise AttributeError("No trajectory loaded into Universe")
        def fset(self, value):
            del self.__dcd
            self.__dcd = value
        return locals()
    dcd = property(**dcd())

    def _dcd():
        doc = "Old reference to DCDReader object containing trajectory data"
        def fget(self):
            import warnings
            warnings.warn("Usage of '_dcd' is deprecated. Use 'dcd' instead.", category=DeprecationWarning, stacklevel=2)
            if not self.__dcd == None: return self.__dcd
            else: raise AttributeError("No trajectory loaded into Universe")
        return locals()
    _dcd = property(**_dcd())
