import os
import aprslib
from ax253 import Frame
import kiss
import time

MYCALL = os.environ.get("MYCALL", "K8SDR")
KISS_HOST = os.environ.get("KISS_HOST", "localhost")
KISS_PORT = os.environ.get("KISS_PORT", "8001")

# Global variable to store the kiss connection
ki = None


def send_ack(msg_no, dest):
    """Send an ACK for the received message using AX.25 frame."""
    global ki
    try:
        if ki is None:
            print("KISS connection is not established.")
            return

        # Construct the ACK frame using the specified format
        ack_frame = Frame.ui(
            destination="APWW11",
            source=MYCALL,
            path=["WIDE1-1"],
            info=f":{dest:<9}:ack{msg_no}" + "}"
        )

        # Send the frame
        ki.write(ack_frame)
        print(f"Sent ACK for msgNo: {msg_no} to {dest}")
        print(aprslib.parse(str(ack_frame)))

    except Exception as e:
        print(f"Error sending ACK: {e}")


def send_response(dest, message):
    """Send an ACK for the received message using AX.25 frame."""
    global ki
    try:
        if ki is None:
            print("KISS connection is not established.")
            return

        # Construct the message frame using the specified format
        message_frame = Frame.ui(
            destination="APWW11",
            source=MYCALL,
            path=["WIDE1-1"],
            info=f":{dest:<9}:{message}"
        )

        # Send the frame
        ki.write(message_frame)
        print(f"Sent Response to {dest}")
        print(aprslib.parse(str(message_frame)))

    except Exception as e:
        print(f"Error sending Response: {e}")



def print_frame(frame):
    """Process incoming frames and send ACKs as needed."""
    global ki
    msgFrame = str(Frame.from_bytes(frame))
    parsedFrame = aprslib.parse(msgFrame)
    print(msgFrame)
    print(parsedFrame)

    # Check if the message is intended for us
    if MYCALL == parsedFrame.get('addresse'):
        print('Message intended for us')

        # Check if the frame contains a message number and send an ACK if needed
        if parsedFrame.get('msgNo') is not None:
            print('Requesting ACK')
            # Send ACK to the correct sender
            send_ack(parsedFrame['msgNo'], parsedFrame.get('from'))  # Use 'from' to send the ACK back
            time.sleep(3)


        if parsedFrame.get('message_text') is not None:
            msg = parsedFrame.get('message_text')
            if msg.startswith('ping'):
                send_response(dest=parsedFrame.get('from'), message='pong')




def main():
    """Initialize the KISS connection and read frames."""
    global ki
    try:
        ki = kiss.TCPKISS(host=KISS_HOST, port=int(KISS_PORT), strip_df_start=True)
        ki.start()
        print("KISS connection established.")

        # Create a frame to send
        frame = Frame.ui(
            destination="APWW11",
            source=MYCALL,
            path=["WIDE1-1"],
            info="",
        )
        ki.write(frame)  # Send the initial frame
        ki.read(callback=print_frame, min_frames=None)  # Start reading frames
    except Exception as e:
        print(f"Error initializing KISS: {e}")


if __name__ == "__main__":
    main()
