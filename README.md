# Miniature Electric Violin Emulator

A distributed embedded system that emulates core violin performance mechanics — string selection, bow excitation, and pitch articulation — using IMU-based motion sensing, capacitive touch input, UDP transport, and MIDI synthesis.

The system is architected as a real-time hardware–software pipeline bridging ESP32 microcontrollers and a DAW via MIDI.


<video src="https://github.com/anjaneya-damle/EmbededE-Violin/blob/main/DemoViolin.mp4" controls width="100%"></video>

---

## System Architecture

### 1. Bow Subsystem (ESP32 + MPU6500)

The bow is emulated using an MPU6500 6-DoF IMU.

- Orientation determines active string selection.
- Linear acceleration along the bowing axis determines note excitation.
- Continuous motion sustains the note.
- Loss of motion triggers note timeout.

The ESP32 transmits discrete string identifiers (`Sa`, `Pa`, `LPa`, etc.) over UDP.

File:  
`ESP_Bow_Sender.ino`

---

### 2. Fingerboard Subsystem (ESP32 + Capacitive Touch)

The fingerboard uses foil-based capacitive touch pads arranged to approximate violin finger spacing.

- Pads transmit a 3-bit binary string (`ABC`) via UDP.
- Priority logic resolves simultaneous presses (C > B > A).
- Touch state modifies pitch relative to the active string.

File:  
`ESP_Fingerboard_Sender.ino`

---

### 3. UDP → MIDI Bridge (Python)

The Python receiver listens on UDP port 5005 and performs:

- Non-blocking socket read
- Pad state decoding
- String + pad priority resolution
- MIDI note mapping
- Sustain timeout handling
- Break-state enforcement

  
The script:
- Sends `note_on` only on pitch change
- Enforces sustain timeout (`NOTE_SUSTAIN_TIMEOUT_SECONDS`)
- Implements break suppression window
- Outputs to a virtual MIDI port
