# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


# Patrones de ánodo común ('0' = segmento encendido, '1' = apagado)
# Orden de bits en seg7[6:0]: (6=>a, 5=>b, 4=>c, 3=>d, 2=>e, 1=>f, 0=>g)
SEG7_ANODE_COMMON = {
    0: 0b1000000,
    1: 0b1111001,
    2: 0b0100100,
    3: 0b0110000,
    4: 0b0011001,
    5: 0b0010010,
    6: 0b0000010,
    7: 0b0111000,
    8: 0b0000000,
    9: 0b0010000,
}


async def drive_pwm_window(dut, duty_percent: int, pwm_period_cycles: int, windows: int = 3):
    """Genera una señal PWM de `duty_percent` (0..100%) durante `windows` ventanas de muestreo."""
    # Con CLK_HZ = 1_000 en tb.v, PWM_WIN_TICKS = 50 ciclos de clk.
    # Si pruebas con CLK_HZ = 50_000_000, ajusta `window_cycles` acorde a tu diseño.
    window_cycles = 50
    total_cycles = window_cycles * windows
    high_cycles = max(0, min(pwm_period_cycles, round(pwm_period_cycles * duty_percent / 100)))

    for i in range(total_cycles):
        if duty_percent <= 0 or high_cycles == 0:
            dut.ui_in.value = 0
        elif duty_percent >= 100 or high_cycles >= pwm_period_cycles:
            dut.ui_in.value = 1
        else:
            dut.ui_in.value = 1 if (i % pwm_period_cycles) < high_cycles else 0
        await ClockCycles(dut.clk, 1)


@cocotb.test()
async def test_banco_inyectores(dut):
    dut._log.info("Inicio de prueba: tt_um_banco_inyectores")

    # Reloj de 100 kHz (periodo de 10 us)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset inicial
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Verificar configuración de direcciones en uio_oe (uio[6:0] salidas)
    assert (int(dut.uio_oe.value) & 0x7F) == 0x7F, f"uio_oe inesperado: {dut.uio_oe.value}"

    # 1. Estado apagado (0% PWM -> dígito 0, relé apagado, sin pulsos de inyector)
    dut._log.info("Probando estado apagado (0% PWM)")
    await drive_pwm_window(dut, duty_percent=0, pwm_period_cycles=10, windows=3)

    seg7_val = int(dut.uio_out.value) & 0x7F
    relay_bomba = (int(dut.uo_out.value) >> 6) & 0x1
    inyectores = int(dut.uo_out.value) & 0x3F

    assert seg7_val == SEG7_ANODE_COMMON[0], f"Esperado '0' en 7-seg ({bin(SEG7_ANODE_COMMON[0])}), obtenido {bin(seg7_val)}"
    assert relay_bomba == 0, "Relevador de bomba debería estar apagado en 0% PWM"
    assert inyectores == 0, "No debería haber pulsos en inyectores en 0% PWM"

    # 2. Probar niveles intermedios y máximo (~50% -> nivel 5, ~90% -> nivel 9)
    for duty, expected_digit in [(50, 5), (90, 9)]:
        dut._log.info(f"Probando PWM ~{duty}% -> esperado nivel {expected_digit}")
        await drive_pwm_window(dut, duty_percent=duty, pwm_period_cycles=10, windows=4)

        seg7_val = int(dut.uio_out.value) & 0x7F
        relay_bomba = (int(dut.uo_out.value) >> 6) & 0x1

        assert relay_bomba == 1, f"Relevador de bomba debería estar activo con PWM al {duty}%"
        assert seg7_val == SEG7_ANODE_COMMON[expected_digit], (
            f"Nivel {expected_digit}: esperado 7-seg {bin(SEG7_ANODE_COMMON[expected_digit])}, "
            f"obtenido {bin(seg7_val)}"
        )

    # 3. Verificar secuencia en los 6 canales de inyector (uo_out[5:0])
    dut._log.info("Verificando secuencia de inyectores 0..5")
    seen_channels = set()
    # Mantener PWM alto (~90%) mientras observamos disparos de inyectores
    for _ in range(1500):
        dut.ui_in.value = 1
        await ClockCycles(dut.clk, 1)
        inj_mask = int(dut.uo_out.value) & 0x3F
        if inj_mask != 0:
            # Comprueba que solo un canal esté activo a la vez en modo secuencial
            assert (inj_mask & (inj_mask - 1)) == 0, f"Más de un inyector activo a la vez: {bin(inj_mask)}"
            for ch in range(6):
                if inj_mask == (1 << ch):
                    seen_channels.add(ch)
        if len(seen_channels) == 6:
            break

    assert seen_channels == {0, 1, 2, 3, 4, 5}, f"Canales observados incompletos: {seen_channels}"
    dut._log.info("¡Todas las pruebas pasaron correctamente!")
