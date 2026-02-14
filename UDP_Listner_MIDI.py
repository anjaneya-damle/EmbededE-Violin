import socket
import mido
import time

# --- MIDI and Network Configuration ---
MIDI_PORT_NAME = 'loopMIDI Port 0 1'
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# --- MIDI Note Mappings ---
NOTES = {
    "Sa": 72,        
    "Re": 74,
    "Ga": 76,
    "Ma": 77,
    "Pa": 79,
    "Da": 81,
    "Ni": 83,
    "Upper Sa": 84, 
    "LPa": 67,       
    "LDa": 69,
    "LNi": 71,
    "LSa": 72,
}

# --- Timing Constants ---
NOTE_SUSTAIN_TIMEOUT_SECONDS = 0.1
BREAK_DURATION_SECONDS = 0.08
LOOP_SLEEP_SECONDS = 0.001

# --- Global State ---
current_active_note = None
last_note_message_time = 0.0
in_break_state = False
break_state_start_time = 0.0
pressed_pads = {"A": False, "B": False, "C": False}
priority_pad = None

# --- MIDI Output Setup ---
try:
    midi_out = mido.open_output(MIDI_PORT_NAME)
except Exception as e:
    print(f"Error opening MIDI port '{MIDI_PORT_NAME}': {e}")
    exit()

# --- UDP Setup ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

print(f"UDP Listener on {UDP_IP}:{UDP_PORT}")
print(f"MIDI Output: '{MIDI_PORT_NAME}'")
print("Ready to receive messages...")

def send_midi_note_on(note_number: int, velocity: int = 100):
    midi_out.send(mido.Message('note_on', note=note_number, velocity=velocity))

def send_midi_note_off(note_number: int, velocity: int = 100):
    midi_out.send(mido.Message('note_off', note=note_number, velocity=velocity))

def stop_current_note():
    global current_active_note
    if current_active_note is not None:
        send_midi_note_off(current_active_note)
        current_active_note = None

def update_pad_status(binary_message: str):
    if len(binary_message) != 3 or not all(c in "01" for c in binary_message):
        print(f"⚠️ Ignoring invalid binary touch message: '{binary_message}'")
        return

    pressed_pads["A"] = binary_message[0] == "1"
    pressed_pads["B"] = binary_message[1] == "1"
    pressed_pads["C"] = binary_message[2] == "1"

    global priority_pad
    if pressed_pads["C"]:
        priority_pad = "C"
    elif pressed_pads["B"]:
        priority_pad = "B"
    elif pressed_pads["A"]:
        priority_pad = "A"
    else:
        priority_pad = None

    state_str = "  ".join([f"Pad {k}: {'✔️' if v else '❌'}" for k, v in pressed_pads.items()])
    print(f"[TOUCH] {state_str}  => Priority Pad: {priority_pad or 'None'}")

try:
    while True:
        current_time = time.monotonic()
        received_message = None

        # --- 1. Receive UDP message ---
        try:
            data, _ = sock.recvfrom(1024)
            received_message = data.decode().strip()
        except BlockingIOError:
            pass

        # --- 2. Handle break ---
        if received_message == "break":
            stop_current_note()
            if not in_break_state:
                print(f"INFO: Entering BREAK state for {BREAK_DURATION_SECONDS*1000} ms.")
            in_break_state = True
            break_state_start_time = current_time
            last_note_message_time = current_time
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        # --- 3. Maintain break duration ---
        if in_break_state:
            if (current_time - break_state_start_time) < BREAK_DURATION_SECONDS:
                time.sleep(LOOP_SLEEP_SECONDS)
                continue
            else:
                print("INFO: Exiting BREAK state.")
                in_break_state = False

        # --- 4. Handle note messages ---
        new_note_to_play = None

        if received_message in ("Sa", "Pa", "LPa"):
            if received_message == "Sa":
                if priority_pad == "A":
                    new_note_to_play = NOTES["Re"]
                    print("INFO: 'Sa' + Pad A → Re")
                elif priority_pad == "B":
                    new_note_to_play = NOTES["Ga"]
                    print("INFO: 'Sa' + Pad B → Ga")
                elif priority_pad == "C":
                    new_note_to_play = NOTES["Ma"]
                    print("INFO: 'Sa' + Pad C → Ma")
                else:
                    new_note_to_play = NOTES["Sa"]
                    print("INFO: 'Sa' with no pad → Sa")

            elif received_message == "Pa":
                if priority_pad == "A":
                    new_note_to_play = NOTES["Da"]
                    print("INFO: 'Pa' + Pad A → Da")
                elif priority_pad == "B":
                    new_note_to_play = NOTES["Ni"]
                    print("INFO: 'Pa' + Pad B → Ni")
                elif priority_pad == "C":
                    new_note_to_play = NOTES["Upper Sa"]
                    print("INFO: 'Pa' + Pad C → Upper Sa")
                else:
                    new_note_to_play = NOTES["Pa"]
                    print("INFO: 'Pa' with no pad → Pa")

            elif received_message == "LPa":
                if priority_pad == "A":
                    new_note_to_play = NOTES["LDa"]
                    print("INFO: 'LPa' + Pad A → LDa")
                elif priority_pad == "B":
                    new_note_to_play = NOTES["LNi"]
                    print("INFO: 'LPa' + Pad B → LNi")
                elif priority_pad == "C":
                    new_note_to_play = NOTES["LSa"]
                    print("INFO: 'LPa' + Pad C → LSa")
                else:
                    new_note_to_play = NOTES["LPa"]
                    print("INFO: 'LPa' with no pad → LPa")

            last_note_message_time = current_time

        elif received_message and all(c in "01" for c in received_message.strip()) and len(received_message.strip()) == 3:
            update_pad_status(received_message.strip())

        # --- 5. Play MIDI if needed ---
        if new_note_to_play is not None:
            if current_active_note != new_note_to_play:
                stop_current_note()
                send_midi_note_on(new_note_to_play)
                current_active_note = new_note_to_play

        # --- 6. Note sustain timeout ---
        elif current_active_note is not None and \
             (current_time - last_note_message_time > NOTE_SUSTAIN_TIMEOUT_SECONDS):
            print(f"INFO: Note {current_active_note} timed out. Stopping.")
            stop_current_note()

        time.sleep(LOOP_SLEEP_SECONDS)

except KeyboardInterrupt:
    print("\nProgram interrupted by user (Ctrl+C).")
finally:
    stop_current_note()
    midi_out.close()
    sock.close()
    print("Clean exit. MIDI port and UDP socket closed.")
