import socket

# APRS KISS settings
SOURCE_CALLSIGN = "AD8NT"
DIGI_PATH = ["WIDE1-1", "WIDE2-1"]  # Digipeater path

# Commands and responses
COMMANDS = {
    "PING": "PONG!",
    "TIME": "The current time is not available.",
    "HELP": "Available commands: PING, TIME, HELP",
}

# Sample location coordinates
LATITUDE = "4903.50N"
LONGITUDE = "07201.75W"
SYMBOL_TABLE = "/"
SYMBOL = "O"  # House or location symbol in APRS


def ax25_encode_callsign(callsign, is_last=False):
    callsign, ssid = (callsign.split("-") + ["0"])[:2]
    callsign = callsign.upper().ljust(6)

    encoded = bytearray([ord(c) << 1 for c in callsign[:6]])

    ssid = int(ssid) & 0x0F
    ssid_byte = (ssid << 1) | 0x60
    if is_last:
        ssid_byte |= 0x01

    encoded.append(ssid_byte)

    return encoded

def ax25_create_frame(source, destination, digipeaters, message):
    frame = bytearray()
    frame.extend(ax25_encode_callsign(destination))
    frame.extend(ax25_encode_callsign(source))

    for i, digi in enumerate(digipeaters):
        is_last_digi = (i == len(digipeaters) - 1)
        frame.extend(ax25_encode_callsign(digi, is_last=is_last_digi))

    frame.extend([0x03, 0xF0])
    frame.extend(message.encode('ascii'))

    return frame

def create_location_packet():
    # APRS location packet format
    location_packet = f"!{LATITUDE}{SYMBOL_TABLE}{LONGITUDE}{SYMBOL}"
    return location_packet

def kiss_encode(ax25_frame):
    kiss_frame = bytearray([0xC0])
    kiss_frame.append(0x00)

    for byte in ax25_frame:
        if byte == 0xC0:
            kiss_frame.extend([0xDB, 0xDC])
        elif byte == 0xDB:
            kiss_frame.extend([0xDB, 0xDD])
        else:
            kiss_frame.append(byte)

    kiss_frame.append(0xC0)
    return bytes(kiss_frame)

def send_kiss_message(sock, source_call, dest_call, digipeaters, message):
    # Ensure dest_call is 9 characters with padding, as required by APRS spec
    dest_call_padded = dest_call.ljust(9)
    aprs_message = f":{dest_call_padded}:{message}"

    ax25_frame = ax25_create_frame(source_call, dest_call, digipeaters, aprs_message)
    kiss_frame = kiss_encode(ax25_frame)
    sock.sendall(kiss_frame)
    print(f"Sent message to {dest_call}: {message}")


def parse_command(aprs_message):
    parts = aprs_message.strip().split(":")
    if len(parts) > 2:
        command = parts[2].strip().upper()
        return COMMANDS.get(command, f"Unknown command: {command}")
    return None

def extract_aprs_message(ax25_frame):
    num_callsigns = 2 + len(DIGI_PATH)
    start_of_message = 7 * num_callsigns + 2
    aprs_message = ax25_frame[start_of_message:].decode('ascii', errors='ignore')
    return aprs_message

def extract_callsigns(ax25_frame):
    num_callsigns = 2 + len(DIGI_PATH)
    callsigns = []
    for i in range(num_callsigns):
        callsign_bytes = ax25_frame[i * 7: (i + 1) * 7]
        callsign = ''.join(chr((b >> 1) & 0x7F) for b in callsign_bytes[:6]).rstrip()
        callsign = callsign.lstrip()
        callsign = ''.join(c for c in callsign if c.isprintable())
        if callsign.startswith('p'):
            callsign = callsign[1:]
        ssid = callsign_bytes[6] & 0x0F
        if ssid:
            callsign += f"-{ssid}"
        callsigns.append(callsign)
    return callsigns

def receive_kiss_messages(sock):
    buffer = bytearray()
    while True:
        data = sock.recv(1024)
        if not data:
            break
        buffer.extend(data)

        while 0xC0 in buffer:
            start = buffer.index(0xC0)
            if buffer.count(0xC0) >= 2:
                end = buffer.index(0xC0, start + 1)
                kiss_frame = buffer[start:end + 1]
                buffer = buffer[end + 1:]

                ax25_frame = kiss_decode(kiss_frame)
                aprs_message = extract_aprs_message(ax25_frame)
                callsigns = extract_callsigns(ax25_frame)

                if len(callsigns) >= 2:
                    source_callsign = callsigns[1]  # Sender's callsign
                    print(f"Received message from {source_callsign}: {aprs_message}")

                    response = parse_command(aprs_message)
                    if response:
                        send_kiss_message(sock, SOURCE_CALLSIGN, source_callsign, DIGI_PATH, response)


def kiss_decode(kiss_frame):
    if kiss_frame[0] != 0xC0 or kiss_frame[-1] != 0xC0:
        raise ValueError("Invalid KISS frame delimiters")

    ax25_frame = bytearray()
    i = 1
    while i < len(kiss_frame) - 1:
        if kiss_frame[i] == 0xDB:
            if kiss_frame[i + 1] == 0xDC:
                ax25_frame.append(0xC0)
            elif kiss_frame[i + 1] == 0xDD:
                ax25_frame.append(0xDB)
            i += 2
        else:
            ax25_frame.append(kiss_frame[i])
            i += 1
    return ax25_frame

if __name__ == "__main__":
    tnc_host = "127.0.0.1"
    tnc_port = 8001

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((tnc_host, tnc_port))
            print("Connected to TNC")

            # Send location packet on startup
            location_packet = create_location_packet()
            send_kiss_message(sock, SOURCE_CALLSIGN, SOURCE_CALLSIGN, DIGI_PATH, location_packet)

            # Start listening for incoming messages
            receive_kiss_messages(sock)

    except Exception as e:
        print(f"Error: {e}")
