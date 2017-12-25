""" Reproduction of calculations from Sumita et 1996 on compaction and implications for Earth's inner core """



import numpy as np
import scipy as sc
import matplotlib.pyplot as plt

from tdma import *

def Schema():
	print(" <-1 volume-> \n \
|-----.-----|-----.-----|-----.-----|\n\
 0     0     1     1     2     2    \n \
 0   1/2dr  dr   3/2dr  2dr   5/2dr   \n \
            ->          ->          \n \
            V1          V2           \n \
     phi0        phi1        phi2   \n \
      DP0         DP1         DP2\n ")


Nr = 10 #number of points in space
Nt = 10 #number of points in time




def fluxlimiterscheme(velocity, variable, dr, options={}): 
	""" output the coefficients for the advection scheme using the flux limiter scheme. 

	Coefficients for the scheme are lambda+, lambda-, v+ and v-
	(p and m are used instead of + and m)

	The code return the coefficients for the tridiagonal matrix a, b, c

	The scheme is used to solve the equation 
	D/Dt variable = D/Dr (variable * V)
	where D/Dr means partial derivative 

	Equation 3.54 in Sramek thesis gives:
	DF/Dx (at the point i) ~ 1/dx *(a_1 variable_i-1 + b_i variable_i +c_i variable_i+1)

	"""

	# detect size of the system and initialize variables:
	lambdap, lambdam, vp, vm = np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable)
	_a, _b, _c, _d = np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable)

	try: 
		option = options['advection']
	except KeyError:
		option = 'upwind'

	if option == 'upwind':
		pass #lambdap and lambdam == zeros. 
	elif option == "centered":
		lambdam[:] = np.ones_like(variable)
		lambdap[:] = np.ones_like(variable)
	elif option == "FLS":
		Rp=(variable[1:-2]-variable[0:-3])/(variable[2:-1]-variable[1:-2])
		Rm=(variable[3:]-variable[2:-1])  /(variable[2:-1]-variable[1:-2])
		#minmod
		lambdap[1:-2]=np.fmax(0.,np.minimum(1.,Rp))
		lambdam[1:-2]=np.fmax(0.,np.minimum(1.,Rm))
	else: 
		print("Problem with the choosen scheme for advection. Default is upwind.")

	if len(velocity) == 1: 
		vp[:-1] = velocity
		vm[:] = 0.
		vp[-1] = 0.
	else:
		vp[:-1] = 0.5*(velocity[:-1]+np.abs(velocity[:-1]))
		vm[:-1] = 0.5*(velocity[:-1]-np.abs(velocity[:-1]))
		vp[-1] = 0.
		vm[-1] = 0.

	_a[1:] = -vp[:-1]*(1-lambdap[:-1]/2.) - vm[:-1]*lambdam[:-1]/2.
	_b[1:] =  vp[1:]*(1-lambdap[1:]/2.) + vm[1:]*lambdam[1:]/2. \
				- vm[:-1]*(1-lambdam[:-1]/2.) - vp[:-1]*lambdap[:-1]/2.
	_c[1:] =  vm[1:]*(1-lambdam[1:]/2.) + vp[1:]*lambdap[1:]/2.

	_d[1:-1] = _a[1:-1]*variable[:-2]+_b[1:-1]*variable[1:-1]+_c[1:-1]*variable[2:]

	_a[0], _b[0], _c[0] = 0., 1., 0.

	return _a/(2*dr), _b/(2*dr), _c/(2*dr), _d/(2*dr)


def sourceterm():
	pass #for now, we can pass this! But useful for later. Will go into the "d". 

def CrankNicholson(variable, dr, options):
	""" Calculate the coefficients for the diffusion

	Variable is only here to provide the good shape for the arrays.
	"""

	# TODO : find another name for Ra (not the good name, as it is actually 1/Ra)
	try: 
		Ra = options["Ra"]
	except KeyError:
		Ra = 0.  # Default value is 0.

	_a, _b, _c, _d = np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable)
	diff = Ra/(dr**2)
	_a[:-1] = - diff/2.
	_b[:-1] = diff 
	_c[:-1] = - diff/2.
	_d[1:-1] = (variable[:-2] - 2*variable[1:-1] + variable[2:])/2.

	return _a, _b, _c, _d


def velocity_Sramek(variable, radius, options):  
	""" Sramek thesis p46, equation 3.22
	$$ \frac{V}{\delta**2\phi**2} = \frac{d}{dz} [ \frac{(1+4/3\phi)(1-\phi)}{\phi} \frac{d}{dz}V]-s(1-\phi) $$

	"""

	dr = radius[1]-radius[0]

	try:
		s = options['s']
	except KeyError:
		s=1.
		print("s (sign of density difference) was not defined, please consider defining it for later. Default value is {}".format(s))
	
	try:
		K0 = options['K0']
	except KeyError:
		K0=1.
		print("K0 was not defined, please consider defining it for later. Default value is {}".format(K0))

	try: 
		delta = options["delta"]
	except KeyError:
		delta = 1.
		print("Delta (compaction length) was not defined, please consider defining it for later. Default value is {}".format(delta))

	print("delta: {}, K0: {}, s: {}".format(delta, K0, s))
	_inter = (K0+4./3.*variable)*(1.-variable)/variable

	_a, _b, _c, _d = np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable)

	_a[1:] = _inter[:-1]/dr**2
	_b[1:] = -1./(delta**2*variable[:-1]*variable[1:]) \
					-  _inter[:-1]/dr**2\
					-  _inter[1:] /dr**2
	_c[1:] = _inter[1:]/dr**2
	_d[1:] = s*(1-np.sqrt(variable[:-1]*variable[1:])) #if buoyancy/density variations, add terms here! s is 1 or -1.

	_a[-1], _b[-1], _c[-1], _d[-1] = 0,1,0,0
	_a[0], _b[0], _c[0], _d[0] = 0,1,0,0


	#new_velocity = np.zeros_like(variable)
	#new_velocity[1:-1] = TDMAsolver(_a[1:-1], _b[1:-1], _c[1:-1], _d[1:-1])
	new_velocity = inversion_matrice(_a[1:], _b, _c[:-1], _d)
	return new_velocity


def velocity_Sumita(variable, radius, options={}):  
	### NOT WORKING

	# spherical symmetry
	# cartesian symmetry

	dr = radius[1]-radius[0] #assuming no variations of dr

	try:
		K0 = options['K0']
	except KeyError:
		K0=0.
		print("K0 was not defined, please consider defining it for later. Default value is {}".format(K0))

	try: 
		eta = options["eta"]
	except KeyError:
		eta = 1.
		print("eta was not defined, please consider defining it for later. Default value is {}".format(eta))

	_a, _b, _c, _d = np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable), np.zeros_like(variable)

	_a[1:] = - K0 *eta /dr**2 * variable[:-1]
	_b[1:] = 1 + K0*eta/dr**2 * (variable[1:]+variable[:-1])
	_c[1:] = - K0 *eta /dr**2 * variable[1:]
	_d[1:] = -K0 * np.sqrt(variable[:-1]*variable[1:])
	
	_a[-1], _b[-1], _c[-1], _d[-1] = 0,1,0,0

	new_velocity = inversion_matrice(_a, _b, _c, _d)

	print(new_velocity)

	return new_velocity


def update(V, phi, dt, dr, options = {'advection':"upwind", 'Ra':0.}):

		a_adv, b_adv, c_adv, d_adv = fluxlimiterscheme(V, phi, dr, options)
		a_diff, b_diff, c_diff, d_diff = CrankNicholson(phi, dr, options)
		_a, _b, _c, _d = a_adv+a_diff, b_adv+b_diff, c_adv+c_diff, d_adv+d_diff
	
		_a = _a*dt
		_b = 1.+_b*dt
		_c = _c*dt
		_d = phi-_d*dt
		_d = boundary_conditions(phi, _a, _b, _c, _d, options)
		# for the boundary conditions, we need to modify d[0] and d[-1]
		#phi2 = phi[:]
		phi2 = np.zeros_like(phi)
		_phi = inversion_matrice(_a[1:-1], _b[1:-1], _c[1:-1], _d[1:-1])
		#phi2 = TDMAsolver(_a, _b, _c, _d)
		phi2[1:-1] = _phi
		phi2[0], phi2[-1] = phi[0], phi[-1]


		_phi = TDMAsolver(_a, _b, _c, _d)
		phi2 = _phi

		return phi2


def boundary_conditions(variable, a, b, c, d, options):

	try: 
		BC = options["bc"]
	except KeyError:
		BC = "dirichlet"

	if BC == "dirichlet":
		d[0]  = d[0] -a[0] *variable[0]
		d[-1] = d[-1]-c[-1]*variable[-1] #Dirichlet
		#print("==========Dirichlet.")
	else: 
		#print("==========not-Dirichlet.")
		d[0] = variable[0]
		d[-1] = variable[-1]

	return d





if __name__ == '__main__':


	#here is the main part of the code
	print('Sumita et al 1996, Geoph. J. Int.')
	Schema()

	