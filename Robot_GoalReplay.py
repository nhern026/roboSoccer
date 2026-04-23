import cv2
import collections
import datetime
import numpy as np
import urllib.request

# --- CONFIG ---
STREAM_URL = "http://192.168.4.1:81/stream"
BUFFER_SECONDS = 10
FPS = 15
# --------------

buffer = collections.deque(maxlen=BUFFER_SECONDS * FPS)

def mjpeg_stream(url):
    print(f"Opening stream: {url}")
    stream = urllib.request.urlopen(url, timeout=10)
    print("Connected. Waiting for frames...")
    bytes_buffer = b""
    frame_count = 0
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        bytes_buffer += chunk
        start = bytes_buffer.find(b'\xff\xd8')
        end = bytes_buffer.find(b'\xff\xd9')
        if start != -1 and end != -1:
            jpg = bytes_buffer[start:end + 2]
            bytes_buffer = bytes_buffer[end + 2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                frame_count += 1
                if frame_count <= 3:
                    print(f"Frame {frame_count} received: {frame.shape}")
                yield frame

def overlay_text(frame, text):
    display = frame.copy()
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 1.0
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x, y = 16, th + 16
    cv2.rectangle(display, (x - 8, y - th - 8), (x + tw + 8, y + 8), (0, 0, 0), -1)
    cv2.putText(display, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return display

def save_clip(frames):
    if len(frames) == 0:
        print("Buffer is empty, nothing to save.")
        return None
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"goal_{timestamp}.mp4"
    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filename, fourcc, FPS, (width, height))
    for frame in frames:
        out.write(frame)
    out.release()
    print(f"Saved clip: {filename}  ({len(frames)} frames)")
    return filename

print("Connecting to stream...")
print("Press 'G' to save the last 10 seconds  |  Press 'Q' to quit")

playing_back = False
playback_frames = []
playback_index = 0

try:
    for frame in mjpeg_stream(STREAM_URL):
        buffer.append(frame)

        if playing_back:
            if playback_index < len(playback_frames):
                cv2.imshow("Goal Replay", overlay_text(playback_frames[playback_index], "Instant Replay"))
                playback_index += 1
                key = cv2.waitKey(int(1000 / FPS)) & 0xFF
            else:
                print("Replay finished. Resuming live stream.")
                playing_back = False
                cv2.destroyWindow("Goal Replay")
                key = cv2.waitKey(1) & 0xFF
        else:
            cv2.imshow("Live Stream", overlay_text(frame, "Live Feed"))
            key = cv2.waitKey(1) & 0xFF

        if key == ord('g') or key == ord('G'):
            print("GOAL! Saving clip...")
            clip = list(buffer)
            saved_file = save_clip(clip)
            if saved_file:
                print("Playing back clip...")
                playing_back = True
                playback_frames = clip
                playback_index = 0
                cv2.destroyWindow("Live Stream")

        elif key == ord('q') or key == ord('Q'):
            print("Quitting.")
            break

except urllib.error.URLError as e:
    print(f"ERROR: Could not connect to stream - {e}")
    print("Make sure you are connected to the ELEGOO WiFi network.")
except KeyboardInterrupt:
    print("Stopped.")
finally:
    cv2.destroyAllWindows()