#!/usr/bin/env python3
"""Audio format conversion using ffmpeg."""
import subprocess, shutil, os, sys, argparse
CREATE_NO_WINDOW = 0x08000000
from pathlib import Path

def base_dir():
    if getattr(sys,'frozen',False):
        if hasattr(sys,'_MEIPASS'): return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

def find_ffmpeg():
    e=os.environ.get("FFMPEG_PATH")
    if e and Path(e).exists(): return e
    p=shutil.which("ffmpeg")
    if p: return p
    b=base_dir()
    for c in [b/"ffmpeg"/"ffmpeg.exe",b/"ffmpeg.exe",b/"bin"/"ffmpeg.exe",Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe")]:
        if c.exists(): return str(c)
    return None

def find_ffprobe():
    e=os.environ.get("FFPROBE_PATH")
    if e and Path(e).exists(): return e
    p=shutil.which("ffprobe")
    if p: return p
    b=base_dir()
    for c in [b/"ffmpeg"/"ffprobe.exe",b/"ffprobe.exe",b/"bin"/"ffprobe.exe",Path("C:/Program Files/ffmpeg/bin/ffprobe.exe")]:
        if c.exists(): return str(c)
    return None

def check_ffmpeg():
    ff=find_ffmpeg()
    if not ff: return False,"ffmpeg not found"
    try:
        r=subprocess.run([ff,"-version"],capture_output=True,text=True,timeout=10, creationflags=CREATE_NO_WINDOW)
        return True,r.stdout.split("\n")[0]
    except Exception as e: return False,str(e)

def convert(inp, out, bitrate="320k", sr=None):
    ff=find_ffmpeg()
    if not ff: return False,"ffmpeg not found"
    cmd=[ff,"-y","-i",str(inp)]
    if sr: cmd.extend(["-ar",str(sr)])
    ext=Path(out).suffix.lower()
    if ext in ['.mp3','.aac','.m4a','.ogg','.opus','.wma']: cmd.extend(["-b:a",bitrate])
    elif ext=='.flac': cmd.extend(["-compression_level","5"])
    elif ext=='.wav': cmd.extend(["-c:a","pcm_s16le"])
    cmd.append(str(out))
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=300, creationflags=CREATE_NO_WINDOW)
        if r.returncode==0: return True,f"Converted to {out}"
        return False,r.stderr[-300:] if r.stderr else "Failed"
    except Exception as e: return False,str(e)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("input"); p.add_argument("output")
    p.add_argument("--bitrate",default="320k")
    a=p.parse_args()
    ok,msg=convert(a.input,a.output,a.bitrate)
    print(msg); sys.exit(0 if ok else 1)
