import cv2
import numpy as np
from PIL import Image
import io
from scipy.signal import convolve2d
from skimage.feature import hog

# --------- LPQ Manual ----------
def lpq_descriptor(image, win_size=7):
    rho = 0.90
    STFTalpha = 1.0 / win_size
    conv_mode = 'valid'
    x = np.arange(-(win_size // 2), win_size // 2 + 1)[np.newaxis]
    w0 = np.ones_like(x)
    w1 = np.exp(2 * np.pi * 1j * x * STFTalpha)
    w2 = np.conj(w1)

    # Filters
    filters = [
        w0.T @ w1,  # horizontal
        w1.T @ w0,  # vertical
        w1.T @ w1,  # diagonal /
        w1.T @ w2,  # diagonal \
    ]

    # Apply filters and stack results
    responses = [convolve2d(image, np.real(f), mode=conv_mode) for f in filters]
    responses += [convolve2d(image, np.imag(f), mode=conv_mode) for f in filters]

    # Quantization
    responses = np.stack(responses, axis=-1)
    codes = (responses > 0).astype(np.uint8)
    lpq_codes = np.zeros(codes.shape[:2], dtype=np.uint8)
    for i in range(8):
        lpq_codes += codes[:, :, i] << i

    # Histogram
    hist, _ = np.histogram(lpq_codes.ravel(), bins=256, range=(0, 256))
    hist = hist.astype("float")
    hist /= (hist.sum() + 1e-6)
    return hist

# --------- SIFT Descriptor ----------
def sift_descriptor(image_np, max_features=64):
    try:
        sift = cv2.SIFT_create(nfeatures=max_features)
        keypoints, descriptors = sift.detectAndCompute(image_np, None)
        if descriptors is None:
            # Si no hay keypoints, devolvemos ceros
            return np.zeros((max_features * 128,), dtype=np.float32)
        desc = descriptors.flatten()
        if len(desc) < max_features * 128:
            desc = np.pad(desc, (0, max_features * 128 - len(desc)), 'constant')
        else:
            desc = desc[:max_features * 128]
        return desc.astype(np.float32)
    except Exception as e:
        print("Error SIFT:", e)
        return np.zeros((max_features * 128,), dtype=np.float32)

# --------- HOG Descriptor ----------
def hog_descriptor(image_np):
    image_np = image_np.astype('float32') / 255.0
    features = hog(image_np, pixels_per_cell=(16, 16), cells_per_block=(2, 2),
                   orientations=9, block_norm='L2-Hys', visualize=False)
    return features

# --------- Simple Data Augmentation ----------
def augmentations(image_np):
    # Devuelve la imagen original y una volteada horizontal (puedes agregar más)
    return [image_np, cv2.flip(image_np, 1)]

# --------- Embeddings Fusionados LBP + LPQ + SIFT + HOG + Augmentation ----------
def obtener_embeddings_lbp_lpq_sift_hog(imagen_bytes):
    try:
        imagen = Image.open(io.BytesIO(imagen_bytes)).convert('L')
        imagen_np = np.array(imagen)
        imagen_np = cv2.resize(imagen_np, (128, 128))
        imagen_np = cv2.equalizeHist(imagen_np)

        variantes = augmentations(imagen_np)
        embeddings_list = []

        for variante in variantes:
            # --- LBP ---
            lbp = np.zeros_like(variante)
            for i in range(1, variante.shape[0] - 1):
                for j in range(1, variante.shape[1] - 1):
                    centro = variante[i, j]
                    binario = ''
                    binario += '1' if variante[i-1, j-1] >= centro else '0'
                    binario += '1' if variante[i-1, j  ] >= centro else '0'
                    binario += '1' if variante[i-1, j+1] >= centro else '0'
                    binario += '1' if variante[i  , j+1] >= centro else '0'
                    binario += '1' if variante[i+1, j+1] >= centro else '0'
                    binario += '1' if variante[i+1, j  ] >= centro else '0'
                    binario += '1' if variante[i+1, j-1] >= centro else '0'
                    binario += '1' if variante[i  , j-1] >= centro else '0'
                    lbp[i, j] = int(binario, 2)
            hist_lbp, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
            hist_lbp = hist_lbp.astype("float")
            hist_lbp /= (hist_lbp.sum() + 1e-6)

            # --- LPQ ---
            hist_lpq = lpq_descriptor(variante, win_size=7)

            # --- SIFT ---
            sift_vec = sift_descriptor(variante)

            # --- HOG ---
            hog_vec = hog_descriptor(variante)

            # --- Fusionar ---
            fusion = np.concatenate([hist_lbp, hist_lpq, sift_vec, hog_vec])
            embeddings_list.append(fusion)

        # Promedio de las variantes
        embeddings_final = np.mean(np.stack(embeddings_list), axis=0)
        return embeddings_final.tolist()
    except Exception as e:
        print("Error LBP+LPQ+SIFT+HOG:", e)
        import traceback; traceback.print_exc()
        return None

    