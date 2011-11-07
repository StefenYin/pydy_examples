from sympy import symbols, sqrt, zeros, ccode, acos
from sympy.physics.mechanics import (dynamicsymbols, ReferenceFrame, Vector,
    Point, inertia, dot, cross, kinematic_equations, Kane, RigidBody)

Vector.simp = False         # Prevent the use of trigsimp and simplify
t, g = symbols('t g')        # Time and gravitational constant
a, b, c = symbols('a b c')  # semi diameters of ellipsoid
d, e, f = symbols('d e f')  # mass center location parameters

# Mass and Inertia scalars
m, Ixx, Iyy, Izz, Ixy, Iyz, Ixz = symbols('m Ixx Iyy Izz Ixy Iyz Ixz')

q = dynamicsymbols('q:5')             # Generalized coordinates
qd = [qi.diff(t) for qi in q]         # Generalized coordinate time derivatives
u = dynamicsymbols('u:3')             # Generalized speeds
ud = [ui.diff(t) for ui in u]         # Generalized speeds time derivatives
ua = dynamicsymbols('ua:3')           # Auxiliary generalized speeds
CF = dynamicsymbols('Rx Ry Rz')       # Contact forces

N = ReferenceFrame('N')                   # Inertial Reference Frame
Y = N.orientnew('Y', 'Axis', [q[0], N.z]) # Yaw Frame
L = Y.orientnew('L', 'Axis', [q[1], Y.x]) # Lean Frame
R = L.orientnew('R', 'Axis', [q[2], L.y]) # Rattleback body fixed frame

I = inertia(R, Ixx, Iyy, Izz, Ixy, Iyz, Ixz)    # Inertia dyadic

# Angular velocity using u's as body fixed measure numbers of angular velocity
R.set_ang_vel(N, u[0]*R.x + u[1]*R.y + u[2]*R.z)

# Inertial origin
NO = Point('NO')

# Rattleback ground contact point
P = NO.locatenew('P', q[3]*N.x + q[4]*N.y)
P.set_vel(N, ua[0]*Y.x + ua[1]*Y.y + ua[2]*Y.z)

# Rattleback ellipsoid center location, see:
# "Realistic mathematical modeling of the rattleback", Kane, Thomas R. and
# David A. Levinson, 1982, International Journal of Non-Linear Mechanics
mew = [dot(rk, Y.z) for rk in R]
eps = sqrt((a*mew[0])**2 + (b*mew[1])**2 + (c*mew[2])**2)
O = P.locatenew('O', -(a*a*mew[0]/eps)*R.x
                     -(b*b*mew[1]/eps)*R.y
                     -(c*c*mew[2]/eps)*R.z)
O.set_vel(N, P.vel(N) + cross(R.ang_vel_in(N), O.pos_from(P)))

# Mass center position, velocity, acceleration
RO = O.locatenew('RO', d*R.x + e*R.y + f*R.z)
RO.set_vel(N, P.vel(N) + cross(R.ang_vel_in(N), RO.pos_from(P)))

# Partial angular velocities and partial velocities
partial_w = [R.ang_vel_in(N).diff(ui, N) for ui in u + ua]
partial_v_P = [P.vel(N).diff(ui, N) for ui in u + ua]
partial_v_RO = [RO.vel(N).diff(ui, N) for ui in u + ua]

# Set auxiliary generalized speeds to zero now that we have obtained all the
# partials.  This only affects points P, O, and RO
#P.set_vel(N, P.vel(N).subs({ua[0]:0, ua[1]:0, ua[2]:0}))
#O.set_vel(N, O.vel(N).subs({ua[0]:0, ua[1]:0, ua[2]:0}))
#RO.set_vel(N, RO.vel(N).subs({ua[0]:0, ua[1]:0, ua[2]:0}))

# Angular acceleration
R.set_ang_acc(N, ud[0]*R.x + ud[1]*R.y + ud[2]*R.z)

# Acceleration of mass center
#RO.set_acc(N, cross(R.ang_acc_in(N), RO.pos_from(P))
#            + cross(R.ang_vel_in(N), cross(R.ang_vel_in(N), RO.pos_from(P))))

# Forces
F_P = sum([cf*uv for cf, uv in zip(CF, Y)])
F_RO = m*g*Y.z



kindiffs = kinematic_equations(u, q[:3], 'body', 'ZXY')
# Contact point coordinates:
v_O_qd = qd[3]*N.x + qd[4]*N.y + cross(qd[0]*N.z + qd[1]*Y.x + q[2]*L.y, O.pos_from(P))
kindiffs += [dot(v_O_qd - O.vel(N), N.x), dot(v_O_qd - O.vel(N), N.y)]
Rat = RigidBody()
Rat.mass = m
Rat.mc = RO
Rat.frame = R
Rat.inertia = (I, RO)
BL = [Rat]
KM = Kane(N)
KM.coords(q)
KM.speeds(u, u_auxiliary=ua)
KM.kindiffeq(kindiffs)
FL = [(RO, F_RO), (P, F_P)]
KM.kanes_equations(FL, BL)


# The first three equations of Fr + Fr^* = 0 are the dynamic equations
# associated with the three independent generalized speeds, u0, u1, u2.  These
# equations ultimately need to be solved for the time derivatives of the u's,
# so with this in mind, we rearrange them as:
# M_dyn(q) * du/dt = f_dyn(q, u)
f_dyn = KM.forcing
M_dyn = KM.mass_matrix

# The last three equations of Fr + Fr^* = 0 are the auxiliary dynamic equations
# associated with the three auxiliary generalized speeds.  These equations
# ultimately need to be solved for the constraint forces.  With this in mind we
# rearrange them as:
# CF = f_cf(q, u, ud)
f_cf = KM.auxiliary_eqs

# The kinematic differential equations as constructed above are of the form:
# M_qd * dq/dt + M_u * u = 0
# These equations ultimately need to be solved for dq/dt, so we rearrange them
# into the following form
# M_qd * dq/dt = -M_ub * u = f_qd
# where M_qd is 5 x 5, dq/dt is 5x1, -M_ub is 5 x 3, and b is 5 x 1
M_qd = zeros(5, 5)
f_qd = zeros(5, 1)
for i in range(5):
  for j in range(3):
    f_qd[i] += -kindiffs[i].diff(u[j]) * u[j]
  for j in range(5):
    M_qd[i, j] = kindiffs[i].diff(qd[j])

# Kinetic and potential energy
ke = m*dot(RO.vel(N), RO.vel(N))/2.0 +\
     dot(R.ang_vel_in(N), dot(I, R.ang_vel_in(N)))/2.0
pe = -m*g*dot(RO.pos_from(P), Y.z)

# Delta -- angle between N.z and R.z
delta = acos(dot(N.z, R.z))

# Now, the order in which we need to solve all these equations is the
# following:
# 1) given q and u, solve for dq/dt
# 2) solve dynamic equations for du/dt
# 3) contact forces, which depend on du/dt
# 4) ke and pe, which only depend on q and u

output_M_qd = ""
output_f_qd = ""
for i in range(5):
  for j in range(5):
    output_M_qd += "  M_qd({0}, {1}) = ".format(i, j) + ccode(M_qd[i, j]) + ";\n"
  output_f_qd += "  f_qd({0}, 0) = ".format(i) + ccode(f_qd[i, 0]) + ";\n"

output_f_dyn = ""
output_M_dyn = ""
output_cf = "\n"
ud_subs_dict = dict(zip(ud, symbols('udot:3')))

for i in range(3):
  output_f_dyn += "  f_dyn({0}, 0) = ".format(i) + ccode(f_dyn[i, 0]) + ";\n"
  output_cf += "  CF[{0}] = ".format(i) + ccode(f_cf[i, 0].subs(ud_subs_dict)) + ";\n"
  for j in range(3):
    output_M_dyn += "  M_dyn({0}, {1}) = ".format(i, j) + ccode(M_dyn[i, j]).replace("(t)", "") + ";\n"


output_energy = "\n"
output_energy += "  ke = " + ccode(ke) + ";\n"
output_energy += "  pe = " + ccode(pe) + ";\n"
output_energy += "  te = ke + pe;\n"

output_delta = "\n"
output_delta += "  delta = " + ccode(delta) + ";\n"

output  = "  static Eigen::Matrix<double, 5, 5> M_qd;\n"
output += "  static Eigen::Matrix<double, 5, 1> f_qd;\n"
output += "  static Eigen::Matrix<double, 3, 1> f_dyn;\n"
output += "  static Eigen::Matrix<double, 3, 3> M_dyn;\n\n"
output += (output_f_qd + output_M_qd + output_f_dyn + output_M_dyn + output_cf
    + output_energy + output_delta).replace("(t)", "")

state_rep = [("q{0}".format(i), "x[{0}]".format(i)) for i in range(5)] +\
            [("u{0}".format(i), "x[{0}]".format(i + 5)) for i in range(3)] +\
            [("udot{0}".format(i), "dxdt[{0}]".format(i + 5)) for i in range(3)]

for old, new in state_rep:
  output = output.replace(old, new)

f = file("rattleback_output.txt", 'w')
f.write(output)
f.close()
