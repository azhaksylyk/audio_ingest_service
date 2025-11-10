import numpy as np, soundfile as sf
sr=16000
t=np.arange(sr)/sr
x=0.2*np.sin(2*np.pi*1000*t).astype(np.float32)
sf.write("test.wav", x, sr)
print("OK", len(open("test.wav","rb").read()))