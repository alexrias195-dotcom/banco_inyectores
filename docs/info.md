<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project implements a sequential fuel injector test bench controller (`tt_um_example`) controlled by a PWM signal on `ui_in[0]`.

- **PWM Duty-Cycle Measurement:** `ui_in[0]` passes through a two-flip-flop synchronizer and is measured over a `PWM_WIN_TICKS` (`CLK_HZ / 20`) window to compute a `0..9` operating level (`level_0_9`). If no high pulses are counted (`high_cnt = 0`), `level_0_9` remains `0` and the outputs stay inactive.
- **Pump Relay Control:** `uo_out[6]` (`relay_bomba`) asserts `'1'` when `rst_n = '1'` and a non-zero level is active (`active_on = '1'`), and returns to `'0'` otherwise.
- **Sequential Injector Firing:** `uo_out[5:0]` activates injector channels `0` through `5` one after another. Higher `level_0_9` values decrease the step period (`CLK_HZ / level_0_9`) between channels, while each pulse lasts `PULSE_TICKS` (`CLK_HZ / 50`).
- **7-Segment Display:** `uio_out[6:0]` (configured as outputs via `uio_oe = "01111111"`) outputs an active-low (`'0'` = on, `'1'` = off) common-anode 7-segment code (`a..g`) indicating `level_0_9` (`0..9`).

## How to test

1. Apply low reset (`rst_n = 0`) and then set `rst_n = 1` while driving the system clock on `clk`.
2. Feed a PWM signal into `ui_in[0]` at varying duty cycles to select levels `1` to `9` (or keep `ui_in[0]` at `'0'` for level `0`).
3. Verify that `uo_out[6]` goes high when `level_0_9 > 0` and stays low when idle or in reset.
4. Check `uo_out[5:0]` for sequential pulses from bit `0` to bit `5`, speeding up as the PWM duty cycle increases.
5. Confirm on `uio_out[6:0]` that the common-anode 7-segment display shows the corresponding digit (`0`–`9`).

## External hardware

- PWM signal source connected to `ui_in[0]`.
- 6 LEDs or injector driver/test indicators on `uo_out[5:0]`.
- Pump relay indicator/driver on `uo_out[6]`.
- Common-anode 7-segment display (with current-limiting resistors) on `uio_out[6:0]`.
