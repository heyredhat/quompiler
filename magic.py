import sys
import math
import cmath
import mpmath
import sympy
import scipy
import operator
import itertools
import functools
import qutip as qt
import numpy as np
import datetime

##################################################################################################################

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def dim_spin(n):
    return (n-1.)/2.

def spin_dim(s):
    return 2*s + 1

def factors(n):    
    return set(functools.reduce(list.__add__, 
                ([i, n//i] for i in range(1, int(pow(n, 0.5) + 1)) if n % i == 0)))

def prime_factors(n):
    i = 2
    factors = []
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)
    return factors

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0: 
       return v
    return v / norm

def evolver(state, operator, dt=0.01, inverse=False):
    unitary = (-2*math.pi*1j*operator*dt).expm()
    if inverse:
        unitary = unitary.dag()
    return unitary*state

def xyz_radial(direction):
    direction = np.array(direction)
    length = np.sqrt(np.sum(direction**2))
    return [normalize(direction).tolist(), length]

##################################################################################################################

def sph_xyz(theta, phi):
    return [math.sin(theta)*math.cos(phi),\
            math.sin(theta)*math.sin(phi),\
            math.cos(theta)]

def c_xyz(c):
    if c == float('inf'):
        return [0,0,1]
    #c = np.conjugate(c)
    x = c.real
    y = c.imag
    return [(2*x)/(1.+(x**2)+(y**2)),\
            (2*y)/(1.+(x**2)+(y**2)),\
            (-1.+(x**2)+(y**2))/(1.+(x**2)+(y**2))]

def xyz_c(xyz):
    x, y, z = xyz
    if z == 1:
        return float('Inf')
    else:
        #return np.conjugate(x/(1-z) + 1j*y/(1-z))
        return x/(1-z) + 1j*y/(1-z)

def combos(a,b):
    f = math.factorial
    return f(a) / f(b) / f(a-b)

def polynomial_v(coefficients):
    spin = (len(coefficients)-1.)/2.
    terms = []
    i = 0
    for m in np.arange(-1*spin, spin+1, 1):
        term = 1./(math.sqrt(math.factorial(2*spin)/(math.factorial(spin-m)*math.factorial(spin+m))))*coefficients[i]
        terms.append(complex(term))
        i += 1
    return np.array(terms[::-1])

def v_polynomial(v):
    components = v.tolist()
    spin = (len(components)-1.)/2.
    terms = []
    i = 0
    for m in np.arange(-1*spin, spin+1, 1):
        term = math.sqrt(math.factorial(2*spin)/(math.factorial(spin-m)*math.factorial(spin+m)))*components[i]
        terms.append(complex(term))
        i += 1
    return terms[::-1]

def C_polynomial(roots):
    zeros2 = roots.count(complex(0,0))
    if zeros2 == len(roots):
        return [complex(1,0)] + [complex(0,0)]*(zeros2) 
    zeros = roots.count(float('Inf'))
    roots = [root for root in roots if root != float('Inf')]
    if len(roots) == 0:
        return [complex(0,0)]*zeros + [complex(1,0)]
    else:
        s = sympy.symbols("s")
        polynomial = sympy.Poly(functools.reduce(lambda a, b: a*b, [s-root for root in roots]), domain="CC")
        if zeros2 > 0:
            return [complex(0,0)]*(zeros) + [complex(c) for c in polynomial.coeffs()] + [complex(0,0)]*(zeros2) 
        else:
            return [complex(0,0)]*(zeros) + [complex(c) for c in polynomial.coeffs()]

def polynomial_C(polynomial):
    zeros = 0
    for i in range(len(polynomial)):
        if polynomial[i] == 0:
            zeros +=1
        else:
            break
    poles = [float('Inf') for i in range(zeros)]
    try:
        roots = [complex(root) for root in mpmath.polyroots(polynomial)]
    except:
        try:
            roots = [complex(root) for root in np.roots(polynomial)]
        except:
            print(polynomial)
            roots = [float('Inf') for i in range(len(polynomial)-zeros)]
    return poles+roots

def C_v(roots):
    return polynomial_v(C_polynomial(roots))

def v_C(v):
    return polynomial_C(v_polynomial(v))

def v_SurfaceXYZ(v):
    return [c_xyz(c) for c in v_C(v)]

def SurfaceXYZ_v(XYZ):
    return C_v([xyz_c(xyz) for xyz in XYZ])

def q_SurfaceXYZ(q):
    return v_SurfaceXYZ(q.full().T[0])

def SurfaceXYZ_q(XYZ):
    return qt.Qobj(SurfaceXYZ_v(XYZ)).unit()

##################################################################################################################

def q_qubits(state):
    xyzs = q_SurfaceXYZ(state)
    return [SurfaceXYZ_q([xyz]) for xyz in xyzs]

def qubits_q(qubits):
    return SurfaceXYZ_q([q_SurfaceXYZ(qubit)[0] for qubit in qubits])

def symmeterize(pieces):
    if (len(pieces)) == 1:
        return pieces[0]
    n = len(pieces)
    normalization = 1./math.factorial(n)
    permutations = list(itertools.permutations(pieces, n))
    perm_states = []
    for permutation in permutations:
        perm_state = permutation[0]
        for state in permutation[1:]:
            perm_state = qt.tensor(perm_state, state)
        perm_state.dims = [[perm_state.shape[0]],[1]]
        perm_states.append(perm_state)
    tensor_sum = sum(perm_states)
    return normalization*tensor_sum

def dicke_states(n):
    states = []
    for k in range(n+1):
        pieces = [qt.basis(2, 0) for i in range(n-k)]
        pieces.extend([qt.basis(2,1) for i in range(k)])
        dicke = math.sqrt(math.factorial(n)/(math.factorial(n-k)*math.factorial(k)))*symmeterize(pieces)
        states.append(dicke)
    return states

def unsymmeterize(state, use_dickes=None):
    n = state.shape[0]
    d = int(math.log(n, 2))
    dickes = dicke_states(d) if use_dickes == None else use_dickes
    amps = [state.overlap(dicke) for dicke in dickes]
    return qt.Qobj(np.conjugate(np.array(amps))).unit()
    #return qt.Qobj(np.array(amps)).unit()
##################################################################################################################

Kx = np.array([[0,1,0,0], [1,0,0,0], [0,0,0,0], [0,0,0,0]])
Ky = np.array([[0,0,1,0], [0,0,0,0], [1,0,0,0], [0,0,0,0]])
Kz = np.array([[0,0,0,1], [0,0,0,0], [0,0,0,0], [1,0,0,0]])

Jx = np.array([[0,0,0,0], [0,0,0,0], [0,0,0,-1], [0,0,1,0]])
Jy = np.array([[0,0,0,0], [0,0,0,1], [0,0,0,0], [0,-1,0,0]])
Jz = np.array([[0,0,0,0], [0,0,-1,0], [0,1,0,0], [0,0,0,0]])

def mink_hermitianPoint(mink):
    t, x, y, z = mink.tolist()
    return (t*qt.identity(2) + x*qt.sigmax() + y*qt.sigmay() + z*qt.sigmaz()).unit()

def hermitianPoint_mink(point):
    return np.array([0.5*qt.expect(qt.identity(2), point),\
            0.5*qt.expect(qt.sigmax(), point),\
            0.5*qt.expect(qt.sigmay(), point),\
            0.5*qt.expect(qt.sigmaz(), point)])

def mink_hermitianPoint_ndim(mink, n):
    t, x, y, z = mink.tolist()
    j = dim_spin(n) 
    return (t*qt.identity(n) + x*qt.jmat(j, "x") + y*qt.jmat(j, "y") + z*qt.jmat(j, "z")).unit()

def hermitianPoint_mink_ndim(point, n):
    j = dim_spin(n) 
    return [qt.expect(qt.identity(n), point),\
            qt.expect(qt.jmat(j, "x"), point),\
            qt.expect(qt.jmat(j, "y"), point),\
            qt.expect(qt.jmat(j, "z"), point)]

def qubit_mink(qubit):
    a, b = qubit.full().T[0].tolist()
    return np.array([(a*np.conjugate(a) + b*np.conjugate(b)).real,\
            2*(a*np.conjugate(b)).real,\
            -2*(a*np.conjugate(b)).imag,\
            (a*np.conjugate(a) - b*np.conjugate(b)).real])

def qubit_hermitianPoint(qubit):
    return qubit.ptrace(0)

def hermitianPoint_qubit(herm):
    xyz = [-1*qt.expect(qt.sigmax(), herm),\
               qt.expect(qt.sigmay(), herm),\
               qt.expect(qt.sigmaz(), herm)]
    return SurfaceXYZ_q([xyz])

def mink_qubit(mink):
    herm = mink_hermitianPoint(mink)
    return hermitianPoint_qubit(herm)

def mink_rotate(mink, axis, angle, inverse=False):
    angle = angle*10
    op = None
    if axis == "x":
        op = scipy.linalg.expm(angle*Jx)
    elif axis == "y":
        op = scipy.linalg.expm(angle*Jy)
    elif axis == "z":
        op = scipy.linalg.expm(angle*Jz)
    if inverse:
        op = np.linalg.inv(op)
    return np.inner(op,mink)

def mink_boost(mink, axis, rapidity, inverse=False):
    rapidity = rapidity*10
    op = None
    if axis == "x":
        op = scipy.linalg.expm(-1*rapidity*Kx)
    elif axis == "y":
        op = scipy.linalg.expm(-1*rapidity*Ky)
    elif axis == "z":
        op = scipy.linalg.expm(-1*rapidity*Kz)
    if inverse:
        op = np.linalg.inv(op)
    return np.inner(op,mink)

def mink_boost_state(state, axis, dt=0.01, inverse=False):
    qubits = q_qubits(state)
    minks = [mink_boost(qubit_mink(qubit), axis, dt, inverse=inverse) for qubit in qubits]
    qubits2 = [mink_qubit(mink) for mink in minks]
    return qubits_q(qubits2)

def mink_rotate_state(state, axis, dt=0.01, inverse=False):
    qubits = q_qubits(state)
    minks = [mink_rotate(qubit_mink(qubit), axis, dt, inverse=inverse) for qubit in qubits]
    qubits2 = [mink_qubit(mink) for mink in minks]
    return qubits_q(qubits2)

def mink_boost_qubits(qubits, axis, dt=0.01, inverse=False):
    minks = [mink_boost(qubit_mink(qubit), axis, dt, inverse=inverse) for qubit in qubits]
    qubits2 = [mink_qubit(mink) for mink in minks]
    return qubits_q(qubits2)

def mink_rotate_qubits(qubits, axis, dt=0.01, inverse=False):
    minks = [mink_rotate(qubit_mink(qubit), axis, dt, inverse=inverse) for qubit in qubits]
    qubits2 = [mink_qubit(mink) for mink in minks]
    return qubits_q(qubits2)

def oneParameter_mobius(kind, parameter, acts_on):
    if kind == "parabolic_a":
        a = parameter
        if acts_on == "hermitian":
            return np.array([[1, a],\
                             [0, 1]])
        elif acts_on == "txyz":
            return np.array([[1 + (a**2)/2., a, 0, -1*(a**2)/2.],\
                             [a, 1, 0, -1*a],\
                             [0, 0, 1, 0],\
                             [(a**2)/2., a, 0, 1-(a**2)/2.]])
    elif kind == "parabolic_b":
        a = parameter
        if acts_on == "hermitian":
            return np.array([[1, I()*a],\
                             [0, 1]])
        elif acts_on == "txyz":
            return np.array([[1 + (a**2)/2., 0, a, -1*(a**2)/2.],\
                             [0, 1, 0, 0],\
                             [a, 0, 1, -1*a],\
                             [(a**2)/2., 0, a, 1-(a**2)/2.]])
    elif kind == "hyperbolic_z":
        b = parameter
        if acts_on == "hermitian":
            return np.array([[np.exp(b/2.), 0],\
                             [0, np.exp(-1*b/2.)]])
        elif acts_on == "txyz":
            return np.array([[np.cosh(b), 0, 0, np.sinh(b)],\
                             [0, 1, 0, 0],\
                             [0, 0, 1, 0],\
                             [np.sinh(b), 0, b, np.cosh(b)]])
    elif kind == "elliptic_x":
        theta = parameter
        if acts_on == "hermitian":
            return np.array([[np.exp(I()*theta/2.), 0],\
                             [0, np.exp(-1*I()*theta/2.)]])
        elif acts_on == "txyz":
            return np.array([[1, 0, 0, 0],\
                             [0, np.cos(theta), -1*np.sin(theta), 0],\
                             [0, np.sin(theta), np.cos(theta), 0],\
                             [0, 0, 0, 1]])
    elif kind == "elliptic_y":
        theta = parameter
        if acts_on == "hermitian":
            return np.array([[np.cos(theta/2.), -1*np.sin(theta/2.)],\
                             [np.sin(theta/2.), np.cos(theta/2)]])
        elif acts_on == "txyz":
            return np.array([[1, 0, 0, 0],\
                             [0, np.cos(theta), 0, np.sin(theta)],\
                             [0, 0, 1, 0],\
                             [0, -1*np.sin(theta), 0, np.cos(theta)]])
    elif kind == "elliptic_z":
        theta = parameter
        if acts_on == "hermitian":
            return np.array([[np.cos(theta/2.), I()*np.sin(theta/2.)],\
                             [I()*np.sin(theta/2.), np.cos(theta/2)]])
        elif acts_on == "txyz":
            return np.array([[1, 0, 0, 0],\
                             [0, 1, 0, 0],\
                             [0, 0, np.cos(theta), -1*np.sin(theta)],\
                             [0, 0, np.sin(theta), np.cos(theta)]])

##################################################################################################################

def separable(whole, dims, piece_index):
    whole_copy = whole.copy()
    whole_copy.dims = [[dims],[1]*len(dims)]
    reduction = whole_copy.ptrace(piece_index)
    entropy = qt.entropy_vn(reduction) 
    if entropy < 0.0001 and entropy > -0.9999:
        return True
    else:
        return False

def mixed_separable(part):
    entropy = qt.entropy_vn(part) 
    if entropy < 0.0001 and entropy > -0.9999:
        return True
    else:
        return False

def fuzzy(a, b):
    if a-b < 0.001 and a-b > -0.001:
        return True
    else:
        return False

def density_to_purevec(density):
    entropy = qt.entropy_vn(density) 
    if fuzzy(entropy, 0):
        U, S, V = np.linalg.svd(density.full())
        s = S.tolist()
        for i in range(len(s)):
            if fuzzy(s[i], 1):
                return qt.Qobj(np.conjugate(V[i]))

##################################################################################################################

def construct_1dfock_operators(modes, freq=1):
    create = qt.create(modes)
    destroy = qt.destroy(modes)
    number = qt.num(modes)
    position = (qt.destroy(modes) + qt.destroy(modes).dag())/np.sqrt(2)
    momentum = -1j * (qt.destroy(modes) - qt.destroy(modes).dag())/np.sqrt(2)
    energy = 2 * np.pi * freq * (destroy.dag() * destroy + 0.5)
    return {"create": create,\
            "destroy": destroy,\
            "number": number,\
            "position": position,\
            "momentum": momentum,\
            "energy": energy}

def construct_2dfock_operators(modes, freq=1):
    create = qt.create(modes)
    destroy = qt.destroy(modes)
    number = qt.num(modes)
    position = (qt.destroy(modes) + qt.destroy(modes).dag())/np.sqrt(2)
    momentum = -1j * (qt.destroy(modes) - qt.destroy(modes).dag())/np.sqrt(2)
    operators = {"X": {}, "Y": {}}
    operators["X"]["create"] = qt.tensor(create, qt.identity(modes))
    operators["X"]["destroy"] = qt.tensor(destroy, qt.identity(modes))
    operators["X"]["number"] = qt.tensor(number, qt.identity(modes))
    operators["X"]["position"] = qt.tensor(position, qt.identity(modes))
    operators["X"]["momentum"] = qt.tensor(momentum, qt.identity(modes))
    operators["Y"]["create"] = qt.tensor(qt.identity(modes), create)
    operators["Y"]["destroy"] = qt.tensor(qt.identity(modes), destroy)
    operators["Y"]["number"] = qt.tensor(qt.identity(modes), number)
    operators["Y"]["position"] = qt.tensor(qt.identity(modes), position)
    operators["Y"]["momentum"] = qt.tensor(qt.identity(modes), momentum)
    operators["position"] = qt.tensor(position, position)
    operators["little_position"] = position
    operators["momentum"] = qt.tensor(momentum, momentum)
    operators["little_momentum"] = momentum
    operators["T"] = 2 * np.pi * freq * ((operators["X"]["destroy"].dag() * operators["X"]["destroy"] + 0.5)+\
                        (operators["Y"]["destroy"].dag() * operators["Y"]["destroy"] + 0.5))
    operators["Jx"] = (1./(2))*(operators["X"]["create"]*operators["Y"]["destroy"] + operators["Y"]["create"]*operators["X"]["destroy"])
    operators["Jy"] = -1*1j*(1./(2))*(operators["X"]["create"]*operators["Y"]["destroy"] - operators["Y"]["create"]*operators["X"]["destroy"])
    operators["Jz"] = -1*(1./(2))*(operators["X"]["create"]*operators["X"]["destroy"] - operators["Y"]["create"]*operators["Y"]["destroy"])
    return operators

def spin_fockBASIS(j, m):
    n1 = int(j+m)
    n2 = int(j-m)
    modes = int(2*j)+1
    vacuum = qt.tensor(qt.basis(modes, 0), qt.basis(modes, 0))
    createX = qt.tensor(qt.create(modes), qt.identity(modes))
    createY = qt.tensor(qt.identity(modes), qt.create(modes))
    first = None
    second = None
    if n1 == 0:
        first = qt.tensor(qt.identity(modes), qt.identity(modes))
    elif n1 == 1:
        first = createX
    else:
        first = functools.reduce(lambda M, N: M*N, [createX for i in range(n1)])
    if n2 == 0:
        second = qt.tensor(qt.identity(modes), qt.identity(modes))
    elif n2 == 1:
        second = createY
    else:
        second = functools.reduce(lambda M, N: M*N, [createY for i in range(n2)])
    op = (first*second)/(math.sqrt(math.factorial(j+m))*math.sqrt(math.factorial(j-m)))
    return op*vacuum#, (n1, n2)

def fock_spinBASIS(n1, n2):
    j = (n1+n2)/2.
    m = n1-j
    return qt.spin_state(j, m)#, (j, m)

def spin_fock(spin_state):
    n = spin_state.shape[0]
    j = dim_spin(n)
    bases = []
    for m in np.arange(-1*j, j+1, 1):
        amp = spin_state.overlap(qt.spin_state(j, m))
        bases.append(amp*spin_fockBASIS(j, m))
    return sum(bases)

def fock_spin(fock_state):
    fock_n = fock_state.shape[0]
    n_sum = int(math.sqrt(fock_n))
    bases = []
    for n1 in range(0, n_sum):
        for n2 in range(0, n_sum):
            if n1+n2 == n_sum-1:
                amp = fock_state.overlap(qt.tensor(qt.basis(n_sum, n1), qt.basis(n_sum, n2)))
                bases.append(amp*fock_spinBASIS(n1, n2))
    return sum(bases)

##################################################################################################################

def c_altitudeAzimuth(c):
    r, th = cmath.polar(c)
    if r == 0:
        return [(math.pi/2.) - math.pi, th]
    return [(math.pi/2.) - 2*math.atan2(1,r), th]

def altitudeAzimuth_c(altitude, azimuth):
    zenith = (math.pi/2.) - altitude
    if zenith == 0:
        return float('inf')
    return cmath.rect(math.sin(zenith)/(1-math.cos(zenith)), azimuth)

def v_ALTITUDEaZIMUTH(v):
    return [c_altitudeAzimuth(c) for c in v_C(v)]

def ALTITUDEaZIMUTH_v(ALTITUDEaZIMUTH):
    return C_v([altitudeAzimuth_c(*altitudeAzimuth) for altitudeAzimuth in ALTITUDEaZIMUTH])

def latitudeLongitude_xyz(latitude, longitude):
    latitude = math.radians(latitude)
    longitude = math.radians(longitude)
    x = math.cos(latitude)*math.cos(longitude)
    y = math.cos(latitude)*math.sin(longitude)
    z = math.sin(latitude)
    return [x, y, z]

def xyz_latitudeLongitude(xyz):
    x, y, z = xyz[0], xyz[1], xyz[2]
    r = 1
    latitude = math.asin(z/r)*(180/math.pi)
    longitude = None
    if x > 0:
        longitude = math.atan(y/x)*(180/math.pi)
    elif y > 0:
        longitude = math.atan(y/x)*(180/math.pi) + 180
    else:
        longitude = math.atan(y/x)*(180/math.pi) - 180
    return (latitude, longitude)

##################################################################################################################


def coupling_(a, b):
    particle_types = []
    for a_i in np.arange(-1*a, a+1, 1):
        for b_j in np.arange(-1*b, b+1, 1):
            c = abs(a_i+b_j)
            c2 = abs(abs(a_i)+abs(b_j))
            if c != c2:
                particle_types.append(c2)
            particle_types.append(c)

    T = {}
    for particle in particle_types:
        particle_dict = {}
        if particle == 0:
            states = []
            for a_i in np.arange(-1*a, a+1, 1):
                for b_j in np.arange(-1*b, b+1, 1):
                    state = qt.clebsch(a, b, 0, a_i, b_j, 0)*\
                        qt.tensor(qt.spin_state(a, a_i), qt.spin_state(b, b_j))
                    states.append(state)
            STATE = sum(states)
            particle_dict[particle] = (qt.spin_state(0,0), STATE)
        else:
            for c_m in np.arange(-1*particle, particle+1, 1):
                states = []
                for a_i in np.arange(-1*a, a+1, 1):
                    for b_j in np.arange(-1*b, b+1, 1):
                        state = qt.clebsch(a, b, particle, a_i, b_j, c_m)*\
                            qt.tensor(qt.spin_state(a, a_i), qt.spin_state(b, b_j))
                        states.append(state)
                STATE = sum(states)
                particle_dict[c_m] = (qt.spin_state(particle, c_m), STATE)
        T[particle] = particle_dict
    return T

def coupling(a, b):
    STATES = []
    GOTO = []
    WHICH_IS = []
    T = coupling_(a,b)
    #print("PPP")
    #print(T)
    #print('DDDD')
    for could_split_into in T.keys():
        for of_eig in T[could_split_into].keys():
            STATES.append(T[could_split_into][of_eig][1])
            GOTO.append(T[could_split_into][of_eig][0])
            WHICH_IS.append((could_split_into, of_eig))
    #for i in range(len(STATES)):
    #    print("%s ->\n\t%s\n\t\twhich is %s\n\n" % (STATES[i].full().T[0], GOTO[i].full().T[0], WHICH_IS[i]))
    OPERATOR = qt.Qobj(np.array([state.full().T[0] for state in STATES]))
    return OPERATOR, STATES, GOTO, WHICH_IS

if __name__ == '__main__':
    OPERATOR, STATES, GOTO, WHICH_IS = coupling(0.5, 0.5)

    op = OPERATOR
    ket = qt.tensor(qt.basis(2,0), qt.basis(2,1), qt.rand_ket(2))
    #ket = qt.rand_ket(4)
    ket.dims = [[8], [1]]
    dm = ket.ptrace(0)
    ket.dims = [[4,2], [1,1]]
    dm.dims = [[4,2], [4,2]]
    #dm = ket.ptrace(0)
    #overlaps = [ket.overlap(state) for state in STATES]
    #print("ket")
    #print(ket)
    ##print("dm")
    #print(dm)
    ##print("op")
   # print(op)
    #print("overlaps")
    #print(overlaps)
    #print("op on ket")
   ## print(op*ket)
    #print("op on dm")
    #print(op*dm*op.dag())
    #print("op on ket -> dm")
    #print((op*ket).ptrace(0))

    #ss = op*dm*op.dag()


    states = []
    for state in STATES:
        s = qt.Qobj(state)
        state.dims = [[4],[1]]
        states.append(state)
    projectors = [qt.tensor(state.ptrace(0), qt.identity(2)) for state in states]

    #(projectors[0]*dm).tr()
