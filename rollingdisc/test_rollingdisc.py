from sympy import symbols, Matrix, solve, Poly
from sympy.physics.mechanics import *

# Symbols for time and constant parameters
t, r, m, g, I, J = symbols('t r m g I J')
# Symbols for contact forces
Fx, Fy, Fz = symbols('Fx Fy Fz')

# Configuration variables and their time derivatives
# q[0] -- yaw
# q[1] -- lean
# q[2] -- spin
q = dynamicsymbols('q:3')
qd = [qi.diff(t) for qi in q]

# Generalized speeds and their time derivatives
# u[0] -- disc angular velocity component, disc fixed x direction
# u[1] -- disc angular velocity component, disc fixed y direction
# u[2] -- disc angular velocity component, disc fixed z direction
u = dynamicsymbols('u:3')
ud = [ui.diff(t) for ui in u]
ud_zero = {udi : 0 for udi in ud}     # 

# Auxiliary generalized speeds
# ua[0] -- contact point auxiliary generalized speed, x direction
# ua[1] -- contact point auxiliary generalized speed, y direction
# ua[2] -- contact point auxiliary generalized speed, z direction
ua = dynamicsymbols('ua:3')
ua_zero = {uai : 0 for uai in ua}

# Reference frames
N = ReferenceFrame('N')
A = N.orientnew('A', 'Axis', [q[0], N.z])   # Yaw intermediate frame
B = A.orientnew('B', 'Axis', [q[1], A.x])   # Lean intermediate frame
C = B.orientnew('C', 'Axis', [q[2], B.y])   # Disc fixed frame

# Angular velocity and angular acceleration of disc fixed frame
C.set_ang_vel(N, u[0]*B.x + u[1]*B.y + u[2]*B.z)
C.set_ang_acc(N, C.ang_vel_in(N).diff(t, B)
               + cross(B.ang_vel_in(N), C.ang_vel_in(N)))

# Velocity and acceleration of points
P = Point('P')                   # Disc-ground contact point
O = P.locatenew('O', -r*B.z)     # Center of disc
P.set_vel(N, ua[0]*A.x + ua[1]*A.y + ua[2]*A.z)
O.v2pt_theory(P, N, C)
O.set_acc(N, O.vel(N).subs(ua_zero).diff(t, B)
           + cross(B.ang_vel_in(N), O.vel(N).subs(ua_zero)))

# Kinematic differential equations
w_c_n_qd = qd[0]*A.z + qd[1]*B.x + qd[2]*B.y
kindiffs = Matrix([dot(w_c_n_qd - C.ang_vel_in(N), uv) for uv in B])
qd_kd = solve(kindiffs, qd)     # solve for dq/dt's in terms of u's
mprint(kindiffs)

# Values of generalized speeds during a steady turn
steady_conditions = solve(kindiffs.subs({qd[1] : 0}), u)
steady_conditions.update({qd[1] : 0})
print(steady_conditions)

# Partial angular velocities and velocities
partial_w_C = [C.ang_vel_in(N).diff(ui, N) for ui in u + ua]
partial_v_O = [O.vel(N).diff(ui, N) for ui in u + ua]
partial_v_P = [P.vel(N).diff(ui, N) for ui in u + ua]

print(partial_w_C)
print(partial_v_O)
print(partial_v_P)

# Active forces
F_O = m*g*A.z
F_P = Fx * A.x + Fy * A.y + Fz * A.z
# Generalized active forces
Fr = [dot(F_O, pv_o) + dot(F_P, pv_p) for pv_o, pv_p in
        zip(partial_v_O, partial_v_P)]

# Inertia force
R_star_O = -m*O.acc(N)

# Inertia torque
I_C_O = inertia(B, I, J, I)
T_star_C = -(dot(I_C_O, C.ang_acc_in(N)) \
             + cross(C.ang_vel_in(N), dot(I_C_O, C.ang_vel_in(N))))

# Generalized inertia forces
Fr_star = [dot(R_star_O, pv) + dot(T_star_C, pav) for pv, pav in
           zip(partial_v_O, partial_w_C)]


Fr_star_steady = [Fr_star_i.subs(ud_zero).subs(steady_conditions).expand()
                  for Fr_star_i in Fr_star]

mprint(Fr)
mprint(Fr_star_steady)

# First dynamic equation, under steady conditions is 2nd order polynomial in
# dq0/dt.
steady_turning_dynamic_equation = Fr[0] + Fr_star_steady[0]
# Equilibrium is posible when the solution to this quadratic is real, i.e.,
# when the discriminant in the quadratic is non-negative
p = Poly(steady_turning_dynamic_equation, qd[0])
a, b, c = p.coeffs()
discriminant = b*b - 4*a*c      # Must be non-negative for equilibrium
# in case of thin disc inertia assumptions
#mprint((discriminant / (r**3 * m**2)).expand())


# ADD ALL CODE DIRECTLY BELOW HERE, do not change above!
# Think there should be at 12 assertion tests:
# 1) Fr[i] == fr from KanesMethod  i = 0, ..., 5
# 2) Fr_star[i] == frstar from KanesMethod i = 0, ..., 5
# if 2) is slow, try comparing this instead:
# 2a) Fr_star_steady[i] == frstar from KanesMethod, evaluated at steady turning
# conditions.
# This should be something like frstar.subs(ud_zero).subs(steady_conditions)




"""
Here goes with KanesMethod command directly, to compare to the values of 
kinematical differential equations, generalized active forces, and generalized
inertial forces in general case and steady turning from mannual calcualtion 
above.
Note: here without dependent generalized speeds and coordinates.
"""
# Rigid Bodies
#bodies
iner_tuple = (I_C_O, O)
disc = RigidBody('disc', O, C, m, iner_tuple)
bodyList = [disc]

#generalized forces
F_o = (O, F_O) #gravity
F_p = (P, F_P) #auxiliary forces
forceList = [F_o,  F_p]

# Kanes Method
kane = KanesMethod(
    N, q_ind= q[:3], u_ind= u[:3], kd_eqs=kindiffs, 
    #q_dependent=q[3:], configuration_constraints = f_c, 
    #u_dependent=u[3:], velocity_constraints= f_v, 
    u_auxiliary=ua
    )
 
(fr, frstar)= kane.kanes_equations(forceList, bodyList)

#steady condition
frstar_steady = frstar.subs(ud_zero).subs(steady_conditions).expand()

kdd = kane.kindiffdict()


# test the results
from sympy import trigsimp, simplify

# FIRST try the kinematical differential eqautions.
print ('\n\nSTART TO TEST:\n'
        'Kinematical differential equations:\n')

kdd_simp = {}
for qdi, uis in kdd.items():
    kdd_simp[qdi] = uis.trigsimp().simplify()

try:
    assert kdd_simp == qd_kd
except AssertionError:
    print ('kinematical differential equations are not the same.')
    # see the difference
    difference_kdd = [(luke - stefen) for luke, stefen in zip(
                qd_kd, kdd_simp)]
    print ('See the difference:\n'), difference_kdd
else:
    print ('kinematical differential equations are the same.')



print ('\n\n')
# SECOND try Fr == fr of general cases
# From the results, Fr_c has no negative sign in front of each terms. so I 
# multipled by -1 of both fr and frstar to compare.
print ('Generalized active forces equations:\n')

mprint(Fr); print('\n')
mprint(fr); print('\n')

#convert fr to a list to compare to Fr list.
fr_list = [fri for fri in -fr]
try:
    assert Fr == fr_list
except AssertionError:
    print ('fr equations are not the same.')
    # see the difference
    difference_fr = [(luke.expand() - (-stefen.expand())).trigsimp() for luke, 
                    stefen in zip(Fr, fr_list)]
    print ('See the difference:\n')
    mprint(difference_fr)
else:
    print ('fr equations are the same')



print ('\n\n')
# THIRD try Fr_star == frstar of general cases
print ('General inertia forces equaitons:\n')

mprint(Fr_star); print('\n') 
mprint(frstar); print('\n')

try:
    assert Matrix(Fr_star).expand() == (-frstar).expand()
except AssertionError:
    print ('fr_star equations are not the same.')
    # see the difference
    difference_fr_star = [(luke.expand() - (-stefen.expand())).trigsimp() for 
                        luke, stefen in zip(Fr_star, frstar)]
    print ('See the difference:\n')
    mprint (difference_fr_star)
else:
    print ('fr_star equations are the same')


print ('\n\n')
# FOURTH try Fr_star_steady == frstar_steady in steady turning
mprint(Fr_star_steady); print('\n')
mprint(frstar_steady); print('\n')

try:
    assert Matrix(Fr_star_steady).expand() == (-frstar_steady).expand()
except AssertionError:
    print ('fr_star_steady equations are not the same.')
    # see the difference
    difference_fr_star_steady = [(luke.expand() - (-stefen.expand())).trigsimp() 
                        for luke, stefen in zip(Fr_star_steady, frstar_steady)]
    print ('See the difference:\n')
    mprint (difference_fr_star_steady)
else:
    print ('fr_star_steady equations are the same')
