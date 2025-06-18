import cv2
import numpy as np
from PIL import Image
import io

def obtener_embeddings_lbp(imagen_bytes):
    try:
        # Convertir imagen a escala de grises
        imagen = Image.open(io.BytesIO(imagen_bytes)).convert('L')
        imagen_np = np.array(imagen)

        # Redimensionar imagen para estandarizar
        imagen_np = cv2.resize(imagen_np, (128, 128))

        # Aplicar LBP manualmente
        lbp = np.zeros_like(imagen_np)
        for i in range(1, imagen_np.shape[0] - 1):
            for j in range(1, imagen_np.shape[1] - 1):
                centro = imagen_np[i, j]
                binario = ''
                binario += '1' if imagen_np[i-1, j-1] >= centro else '0'
                binario += '1' if imagen_np[i-1, j  ] >= centro else '0'
                binario += '1' if imagen_np[i-1, j+1] >= centro else '0'
                binario += '1' if imagen_np[i  , j+1] >= centro else '0'
                binario += '1' if imagen_np[i+1, j+1] >= centro else '0'
                binario += '1' if imagen_np[i+1, j  ] >= centro else '0'
                binario += '1' if imagen_np[i+1, j-1] >= centro else '0'
                binario += '1' if imagen_np[i  , j-1] >= centro else '0'
                lbp[i, j] = int(binario, 2)

        # Calcular histograma de LBP (256 posibles patrones)
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype("float")
        hist /= (hist.sum() + 1e-6)  # Normalización

        return hist.tolist()

    except Exception as e:
        print("Error LBP:", e)
        return None

def similitud_coseno(a, b):
    """
    Devuelve la similitud coseno entre dos vectores a y b.
    """
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    num = np.dot(va, vb)
    den = np.linalg.norm(va) * np.linalg.norm(vb) + 1e-6
    return float(num / den)

