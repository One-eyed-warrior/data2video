import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image
import os
import subprocess
import shutil
import struct

# ==== CONFIG ====
FRAME_WIDTH, FRAME_HEIGHT = 192, 108
PIXELS_PER_FRAME = FRAME_WIDTH * FRAME_HEIGHT
BYTES_PER_FRAME = PIXELS_PER_FRAME * 3

# ==== ENCODER ====
def encode_file_to_video(filepath):
    output_dir = "output"
    frames_dir = os.path.join(output_dir, "frames")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(frames_dir)

    with open(filepath, "rb") as f:
        file_data = f.read()

    # Add file size as 8-byte header
    header = struct.pack(">Q", len(file_data))  # Q = unsigned long long (8 bytes)
    data = header + file_data

    chunks = [data[i:i + BYTES_PER_FRAME] for i in range(0, len(data), BYTES_PER_FRAME)]

    for idx, chunk in enumerate(chunks):
        pixels = [tuple(chunk[i:i+3]) if i+2 < len(chunk) else (0, 0, 0)
                  for i in range(0, len(chunk), 3)]
        while len(pixels) < PIXELS_PER_FRAME:
            pixels.append((0, 0, 0))  # pad with black

        img = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT))
        img.putdata(pixels)
        img.save(os.path.join(frames_dir, f"frame_{idx:05d}.png"))

    # Use FFV1 (lossless) codec to ensure bit-accurate encoding
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "1",
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-c:v", "ffv1",
        os.path.join(output_dir, "output.avi")
    ])

    return os.path.join(output_dir, "output.avi")

# ==== DECODER ====
def decode_video_to_file(video_path, user_ext=".bin"):
    output_dir = "recovered"
    frames_dir = os.path.join(output_dir, "frames")
    output_file_path = os.path.join(output_dir, f"reconstructed{user_ext}")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(frames_dir)

    subprocess.run([
        "ffmpeg", "-i", video_path,
        os.path.join(frames_dir, "frame_%05d.png")
    ])

    byte_array = bytearray()
    frame_files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
    for frame_file in frame_files:
        img = Image.open(os.path.join(frames_dir, frame_file))
        pixels = list(img.getdata())
        for pixel in pixels:
            byte_array.extend(pixel)

    # Read the first 8 bytes for the original file size
    original_file_size = struct.unpack(">Q", byte_array[:8])[0]
    file_data = byte_array[8:8 + original_file_size]

    with open(output_file_path, "wb") as f:
        f.write(file_data)

    return output_file_path

# ==== GUI LOGIC ====
def start_encoding():
    filepath = filedialog.askopenfilename()
    if filepath:
        status_label.config(text="Encoding...")
        root.update()
        try:
            output_path = encode_file_to_video(filepath)
            status_label.config(text=f"✅ Encoded to {output_path}")
            messagebox.showinfo("Encoding Complete", f"Video saved as:\n{output_path}")
        except Exception as e:
            status_label.config(text="❌ Encoding failed")
            messagebox.showerror("Error", str(e))

def start_decoding():
    video_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.avi")])
    if video_path:
        user_ext = simpledialog.askstring("File Extension", "Enter file extension (e.g., .pdf, .txt, .zip):", initialvalue=".bin")
        if user_ext and not user_ext.startswith("."):
            user_ext = "." + user_ext
        status_label.config(text="Decoding...")
        root.update()
        try:
            output_path = decode_video_to_file(video_path, user_ext)
            status_label.config(text=f"✅ Decoded to {output_path}")
            messagebox.showinfo("Decoding Complete", f"File reconstructed as:\n{output_path}")
        except Exception as e:
            status_label.config(text="❌ Decoding failed")
            messagebox.showerror("Error", str(e))

# ==== MAIN GUI ====
root = tk.Tk()
root.title("File ↔ Video Encoder/Decoder")

canvas = tk.Canvas(root, height=300, width=500)
canvas.pack()

frame = tk.Frame(root)
frame.place(relx=0.5, rely=0.4, anchor="center")

encode_btn = tk.Button(frame, text="🔐 Encode File → Video", command=start_encoding, width=30, height=2, bg="#90ee90")
encode_btn.pack(pady=10)

decode_btn = tk.Button(frame, text="🔓 Decode Video → File", command=start_decoding, width=30, height=2, bg="#add8e6")
decode_btn.pack(pady=10)

status_label = tk.Label(root, text="Welcome! Choose an action above.", font=("Arial", 10))
status_label.pack(pady=20)

root.mainloop()
