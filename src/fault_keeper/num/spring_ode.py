"""SpringDynamicsSolver: Simple harmonic oscillator ODE solver."""

from __future__ import annotations
import math


class SpringDynamicsSolver:
    """
    Solver for spring-mass system (simple harmonic oscillator).
    
    Equations of motion:
        m·d²x/dt² = -k·x  (Hooke's Law)
        d²x/dt² + (k/m)·x = 0
    
    Solution: x(t) = A·cos(ωt + φ), where ω = sqrt(k/m)
    
    Uses Euler-Cromer method for numerical stability.
    """

    def __init__(self, k: float, m: float):
        """Initialize spring-mass system.
        
        Args:
            k: Spring constant (N/m)
            m: Mass (kg)
        """
        if k <= 0 or m <= 0:
            raise ValueError("k and m must be positive")
        
        self.k = k
        self.m = m
        self.omega = math.sqrt(k / m)  # Angular frequency
        
        # Initial conditions
        self.x = 0.0  # Position
        self.v = 0.0  # Velocity

    def set_initial_conditions(self, x0: float, v0: float) -> None:
        """Set initial position and velocity.
        
        Args:
            x0: Initial position (m)
            v0: Initial velocity (m/s)
        """
        self.x = x0
        self.v = v0

    def step(self, dt: float) -> None:
        """Advance system by time step dt.
        
        Uses Euler-Cromer method for energy conservation:
            v(t+dt) = v(t) + a·dt
            x(t+dt) = x(t) + v(t+dt)·dt
        
        Args:
            dt: Time step (s)
        """
        # Acceleration from Hooke's Law
        a = -self.k * self.x / self.m
        
        # Euler-Cromer integration
        self.v = self.v + a * dt
        self.x = self.x + self.v * dt

    def integrate(self, t_final: float, dt: float = 0.001) -> list[tuple[float, float]]:
        """Integrate to final time.
        
        Args:
            t_final: Final simulation time (s)
            dt: Time step (s)
            
        Returns:
            List of (time, position) tuples
        """
        times = []
        positions = []
        
        current_time = 0.0
        while current_time < t_final:
            times.append(current_time)
            positions.append(self.x)
            self.step(dt)
            current_time += dt
        
        return list(zip(times, positions))

    def analytical_solution(self, t: float) -> tuple[float, float]:
        """Get analytical solution at time t.
        
        x(t) = x0·cos(ωt) + (v0/ω)·sin(ωt)
        v(t) = -x0·ω·sin(ωt) + v0·cos(ωt)
        
        Args:
            t: Time (s)
            
        Returns:
            Tuple of (position, velocity)
        """
        x_analytical = self.x * math.cos(self.omega * t) + (self.v / self.omega) * math.sin(self.omega * t)
        v_analytical = -self.x * self.omega * math.sin(self.omega * t) + self.v * math.cos(self.omega * t)
        
        return x_analytical, v_analytical

    def energy(self) -> float:
        """Get total mechanical energy.
        
        E = ½·k·x² + ½·m·v² (constant for conservative system)
        
        Returns:
            Total energy (Joules)
        """
        potential = 0.5 * self.k * self.x ** 2
        kinetic = 0.5 * self.m * self.v ** 2
        return potential + kinetic


if __name__ == "__main__":
    # Test spring dynamics
    solver = SpringDynamicsSolver(k=10.0, m=1.0)
    solver.set_initial_conditions(x0=1.0, v0=0.0)
    
    # Integrate for 2π seconds (one full period)
    trajectory = solver.integrate(t_final=2 * math.pi, dt=0.01)
    
    print(f"Final position: {trajectory[-1][1]:.6f} (expected ~1.0)")
    print(f"Energy conservation: {solver.energy():.6e} J")