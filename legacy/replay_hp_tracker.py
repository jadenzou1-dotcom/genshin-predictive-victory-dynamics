"""SUPERSEDED by replay/extract.py (kept for history).
Track team HP bars in a replay: fraction of 'filled' pixels along the bar row."""
import cv2, numpy as np, sys, csv
cap=cv2.VideoCapture(sys.argv[1]); fps=cap.get(cv2.CAP_PROP_FPS)
Y=175; L=(666,934); R=(988,1254)
step=int(fps/5)  # 5 samples per second
out=csv.writer(open(sys.argv[2],"w",newline="")); out.writerow(["t","left","right"])
i=0
while True:
    ok=cap.grab()
    if not ok: break
    if i%step==0:
        _,f=cap.retrieve()
        band=f[Y-2:Y+3].astype(int)  # BGR
        b,g,r=band[...,0],band[...,1],band[...,2]
        red=((r>180)&(g<130)&(b<130)).mean(0)>0.5
        blue=((b>200)&(g>150)&(r<150)).mean(0)>0.5
        out.writerow([round(i/fps,2), round(red[L[0]:L[1]].mean(),3), round(blue[R[0]:R[1]].mean(),3)])
    i+=1
