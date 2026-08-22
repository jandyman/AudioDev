import math


def snap_to_e96(value):
    """Snaps a resistor value to the nearest 1% E96 standard resistor."""
    if value <= 0:
        return value

    e96_base = [
        1.00,
        1.02,
        1.05,
        1.07,
        1.10,
        1.13,
        1.15,
        1.18,
        1.21,
        1.24,
        1.27,
        1.30,
        1.33,
        1.37,
        1.40,
        1.43,
        1.47,
        1.50,
        1.54,
        1.58,
        1.62,
        1.65,
        1.69,
        1.74,
        1.78,
        1.82,
        1.87,
        1.91,
        1.96,
        2.00,
        2.05,
        2.10,
        2.15,
        2.21,
        2.26,
        2.32,
        2.37,
        2.43,
        2.49,
        2.55,
        2.61,
        2.67,
        2.74,
        2.80,
        2.87,
        2.94,
        3.01,
        3.09,
        3.16,
        3.24,
        3.32,
        3.40,
        3.48,
        3.57,
        3.65,
        3.74,
        3.83,
        3.92,
        4.02,
        4.12,
        4.22,
        4.32,
        4.42,
        4.53,
        4.64,
        4.75,
        4.87,
        4.99,
        5.11,
        5.23,
        5.36,
        5.49,
        5.62,
        5.76,
        5.90,
        6.04,
        6.19,
        6.34,
        6.49,
        6.65,
        6.81,
        6.98,
        7.15,
        7.32,
        7.50,
        7.68,
        7.87,
        8.06,
        8.25,
        8.45,
        8.66,
        8.87,
        9.09,
        9.31,
        9.53,
        9.76,
    ]

    exponent = math.floor(math.log10(value))
    mantissa = value / (10**exponent)

    closest_base = min(e96_base, key=lambda x: abs(x - mantissa))

    if closest_base == 9.76 and mantissa > 9.88:
        return 10.0 * (10**exponent)

    return closest_base * (10**exponent)


def calculate_sallen_key_lowpass(
    fc, Q_target, C_farads=100e-9, Ra_base_ohms=10e3
):
    """Calculates Equal-Component Sallen-Key Low-Pass Filter network.

    Parameters:
    fc           : Target cutoff frequency (Hz)
    Q_target     : Quality factor target (Note: Equal-component SK requires Q <
    3.0)
    C_farads     : Chosen matched capacitor value (C1 = C2 = C)
    Ra_base_ohms : Reference resistor for the gain network (Ra)
    """
    if Q_target >= 3.0:
        raise ValueError(
            f"Target Q={Q_target} is too high for equal-component Sallen-Key."
            " Gain A0 would exceed 3.0, causing stage oscillation."
        )

    # 1. Filter Resistors (R1 = R2 = R)
    R_exact = 1.0 / (2.0 * math.pi * fc * C_farads)

    # 2. Non-Inverting Gain Network (Ra, Rb)
    # Gain A0 = 3 - (1
    A0_target = 3.0 - (1.0 / Q_target)

    if A0_target <= 1.0:
        # Unity-gain buffer configuration (Rb = 0, Ra = open)
        Ra_exact = float("inf")
        Rb_exact = 0.0
        A0_target = 1.0
    else:
        Ra_exact = Ra_base_ohms
        Rb_exact = Ra_exact * (A0_target - 1.0)

    # 3. Snap to standard 1% E96 resistor values
    R_e96 = snap_to_e96(R_exact)
    Ra_e96 = snap_to_e96(Ra_exact) if Ra_exact != float("inf") else float("inf")
    Rb_e96 = snap_to_e96(Rb_exact) if Rb_exact != 0.0 else 0.0

    # 4. Recalculate actual performance with E96 components
    fc_actual = 1.0 / (2.0 * math.pi * R_e96 * C_farads)

    if Rb_e96 == 0.0:
        A0_actual = 1.0
    else:
        A0_actual = 1.0 + (Rb_e96 / Ra_e96)

    Q_actual = 1.0 / (3.0 - A0_actual)

    return {
        "exact": {
            "R": R_exact,
            "Ra": Ra_exact,
            "Rb": Rb_exact,
            "A0": A0_target,
        },
        "e96": {"R": R_e96, "Ra": Ra_e96, "Rb": Rb_e96},
        "actual_performance": {"fc": fc_actual, "Q": Q_actual, "A0": A0_actual},
    }


if __name__ == "__main__":
    # Design targets for active preamp filter stage
    fc_target = 1000.0  # 1 kHz
    Q_target = 2.0  # High-Q resonant peak

    # Matched standard capacitors (C1 = C2)
    C_val = 100e-9  # 100 nF standard film/C0G cap

    results = calculate_sallen_key_lowpass(
        fc=fc_target, Q_target=Q_target, C_farads=C_val, Ra_base_ohms=10000.0
    )

    print(f"Target Parameters : fc = {fc_target} Hz, Q = {Q_target}\n")
    print(f"Capacitors Used   : C1 = C2 = {C_val*1e9:.1f} nF\n")

    print("Calculated Ideal Resistors:")
    print(f"  R1, R2 (Filter Resistors) : {results['exact']['R'] / 1e3:.3f} kΩ")
    if results["exact"]["Ra"] == float("inf"):
        print("  Ra (Gain Network)         : Open")
        print("  Rb (Gain Network)         : 0 Ω (Short)")
    else:
        print(
            "  Ra (Gain Network)        "
            f" : {results['exact']['Ra'] / 1e3:.3f} kΩ"
        )
        print(
            "  Rb (Gain Network)        "
            f" : {results['exact']['Rb'] / 1e3:.3f} kΩ"
        )
    print(f"  Stage Passband Gain (A0)  : {results['exact']['A0']:.3f} V/V\n")

    print("Nearest 1% E96 Standard Resistors:")
    print(f"  R1, R2 (Filter Resistors) : {results['e96']['R'] / 1e3:.3f} kΩ")
    if results["e96"]["Ra"] == float("inf"):
        print("  Ra (Gain Network)         : Open")
        print("  Rb (Gain Network)         : 0 Ω (Short)")
    else:
        print(
            "  Ra (Gain Network)        "
            f" : {results['e96']['Ra'] / 1e3:.3f} kΩ"
        )
        print(
            "  Rb (Gain Network)        "
            f" : {results['e96']['Rb'] / 1e3:.3f} kΩ"
        )

    perf = results["actual_performance"]
    print("\nActual Circuit Performance with E96 Values:")
    print(
        f"  Actual fc   : {perf['fc']:.2f} Hz  (Shift:"
        f" {((perf['fc'] - fc_target)/fc_target)*100:+.2f}%)"
    )
    print(
        f"  Actual Q    : {perf['Q']:.3f}     (Shift:"
        f" {((perf['Q'] - Q_target)/Q_target)*100:+.2f}%)"
    )
    print(f"  Actual Gain : {perf['A0']:.3f} V/V")




