#include <iostream>
#include <fstream>
#include <cmath>
#include <gsl/gsl_errno.h>
#include <gsl/gsl_odeiv2.h>
#include "rattleback.h"

int main(int argc, char *argv[]) {
  rattleback_params p;
  p.a = 0.2;
  p.b = 0.03;
  p.c = 0.02;
  p.d = p.e = 0.0;
  p.f = 0.01;
  p.m = 1.0;
  p.g = 9.81;
  p.Ixx =  0.0002;
  p.Iyy =  0.0016;
  p.Izz =  0.0017;
  p.Ixy = -0.00002;
  p.Iyz = p.Ixz = 0.0;

  // Initial time and state
  simdata s = {0.0, {0.0,              // Yaw (ignorable)
                     0.5*M_PI/180.0,   // Roll
                     0.5*M_PI/180.0,   // Pitch
                     0.0, 0.0,         // x, y of contact (ignorable)
                     0.0,              // u0
                     0.0,              // u1
                     -5.0} };          // u2

  rattleback_outputs(&s, &p);
  const double tf = 20.0;                          // final time
  const int N = 20001;                             // number of points
  
  // GSL setup code
  gsl_odeiv2_system sys = {rattleback_ode, NULL, 8, &p};
  
  double scale_abs[] = {0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0};
  gsl_odeiv2_driver * d = gsl_odeiv2_driver_alloc_scaled_new(&sys,
      gsl_odeiv2_step_rk8pd,
      1e-3,       // Initial step size
      1e-6,       // eps absolute
      1e-3,       // eps relative
      1.0,        // a_y
      1.0,        // a_dydt
      scale_abs);
  gsl_odeiv2_driver_set_hmin(d, 1e-6);
  gsl_odeiv2_driver_set_hmax(d, 1e-3);

  // Open a file for writing
  std::ofstream f("datafile.dat", std::ios::binary | std::ios::out);

  // Simulation loop
  f.write((char *) &s, sizeof(simdata));          // Write initial time data
  for (int i = 1; i <= N; ++i) {
    double ti = i * tf / N;
    int error = gsl_odeiv2_driver_apply(d, &(s.t), ti, s.x);  // integrate the ODE's
    if (error == GSL_FAILURE) {
      std::cerr << "aborting!!!!" << std::endl;
      abort();
    }
    rattleback_outputs(&s, &p);                   // compute the contact forces
    f.write((char *) &s, sizeof(simdata));        // write to file
  }

  gsl_odeiv2_driver_free(d);                      // free resources
  f.close();                                      // close file
  return 0;
}
