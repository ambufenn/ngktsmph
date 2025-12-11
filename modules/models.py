# image classification wrapper with optional Gemini (mock fallback)
import os, base64
WASTE_TYPES=['Plastik PET','HDPE','PP','Logam','Kertas','Kaca','Minyak Jelantah','Organik']

def classify_image(image_path=None):
    # Mocked classifier: returns random-ish classification with contamination and recyclability score
    import random
    label = random.choice(WASTE_TYPES)
    contamination = random.choice(['Clean','Slightly contaminated','Contaminated'])
    score = random.randint(40,98)
    advice='Bersihkan bagian yang berminyak, lalu keringkan.'
    return {'label':label, 'contamination':contamination, 'recyclability_score':score, 'advice':advice}
