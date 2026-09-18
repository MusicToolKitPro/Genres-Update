#!/usr/bin/env python3
"""Audio enhancement: denoise, normalize, EQ."""
import numpy as np, soundfile as sf, argparse
from pathlib import Path

def denoise(y, sr, strength=0.8):
    try:
        import librosa
        stft = librosa.stft(y); mag, phase = librosa.magphase(stft)
        nf = max(1, int(0.5*sr/512)); ne = np.mean(mag[:,:nf],axis=1,keepdims=True)
        mask = (mag > ne*(1+strength*2)).astype(float)*0.8+0.2
        return librosa.istft(mag*mask*phase)[:len(y)]
    except: return y

def normalize_rms(y, target=-14.0):
    r = np.sqrt(np.mean(y**2)); return y*(10**(target/20)/r) if r>1e-10 else y

def normalize_peak(y):
    p = np.max(np.abs(y)); return y/p if p>1e-10 else y

def bass_boost(y, sr, gain=3.0):
    try:
        from scipy.signal import butter, lfilter
        b,a = butter(2, 250/(sr/2), btype='low')
        return y + lfilter(b,a,y)*(10**(gain/20)-1)
    except: return y

def treble_boost(y, sr, gain=2.0):
    try:
        from scipy.signal import butter, lfilter
        b,a = butter(2, 4000/(sr/2), btype='high')
        return y + lfilter(b,a,y)*(10**(gain/20)-1)
    except: return y

def trim_silence(y, sr, th=-40):
    t = 10**(th/20); w = int(sr*0.01); start=0
    for i in range(0,len(y)-w,w):
        if np.sqrt(np.mean(y[i:i+w]**2))>t: start=i; break
    end=len(y)
    for i in range(len(y)-w,0,-w):
        if np.sqrt(np.mean(y[i:i+w]**2))>t: end=min(i+w,len(y)); break
    return y[start:end]

def enhance(inp, out, denoise_=False, strength=0.8, norm=False, target=-14.0, peak=False, bass=0.0, treble=0.0, trim=False, sr=None):
    y, s = sf.read(inp, dtype='float32')
    if y.ndim>1: y=y.mean(axis=1)
    steps=[]
    if denoise_: y=denoise(y,s,strength); steps.append("denoise")
    if trim: y=trim_silence(y,s); steps.append("trim")
    if bass!=0: y=bass_boost(y,s,bass); steps.append(f"bass{bass:+.1f}")
    if treble!=0: y=treble_boost(y,s,treble); steps.append(f"treble{treble:+.1f}")
    if norm: y=normalize_rms(y,target); steps.append("normalize")
    if peak: y=normalize_peak(y); steps.append("peak")
    sf.write(out, y, sr or s)
    print(f"Enhanced: {', '.join(steps) or 'conversion'}")
    return {"input":inp,"output":out,"steps":steps}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("input"); p.add_argument("output")
    p.add_argument("--denoise",action="store_true"); p.add_argument("--normalize",action="store_true")
    p.add_argument("--bass",type=float,default=0.0); p.add_argument("--treble",type=float,default=0.0)
    p.add_argument("--trim-silence",action="store_true")
    a=p.parse_args()
    enhance(a.input,a.output,a.denoise,norm=a.normalize,bass=a.bass,treble=a.treble,trim=a.trim_silence)
