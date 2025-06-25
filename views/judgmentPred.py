import json
import os
import numpy as np
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from PIL import Image
import pytesseract
import tensorflow as tf
from tensorflow.keras.layers import GRU, Dense, Dropout, Input, Masking, Bidirectional
from tensorflow.keras.models import Model
import google.generativeai as genai

# === ENV & MODEL SETUP ===
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model_gemini = genai.GenerativeModel("gemini-2.0-flash")

class AttentionLayer(tf.keras.layers.Layer):
    def __init__(self, attention_dim=200, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)
        self.attention_dim = attention_dim

    def build(self, input_shape):
        self.W = self.add_weight(
            shape=(input_shape[-1], self.attention_dim),
            initializer="glorot_uniform",
            trainable=True
        )
        self.b = self.add_weight(
            shape=(self.attention_dim,),
            initializer="zeros",
            trainable=True
        )
        self.u = self.add_weight(
            shape=(self.attention_dim, 1),
            initializer="glorot_uniform",
            trainable=True
        )
        super(AttentionLayer, self).build(input_shape)

    def call(self, x):
        u_t = tf.math.tanh(tf.linalg.matmul(x, self.W) + self.b)
        a = tf.linalg.matmul(u_t, self.u)
        a = tf.nn.softmax(tf.squeeze(a, -1))
        weighted_input = x * tf.expand_dims(a, -1)
        return tf.reduce_sum(weighted_input, axis=1)

def load_bi_gru_model():
    input_text = Input(shape=(None, 768), dtype='float32', name='text')
    masked_input = Masking(mask_value=-99.)(input_text)
    gru_out = Bidirectional(GRU(100, return_sequences=True))(masked_input)
    gru_out = Bidirectional(GRU(100, return_sequences=True))(gru_out)
    attention_out = AttentionLayer(attention_dim=200)(gru_out)
    dropout_out = Dropout(0.5)(attention_out)
    dense_out = Dense(30, activation='relu')(dropout_out)
    final_out = Dense(1, activation='sigmoid')(dense_out)
    model = Model(inputs=input_text, outputs=final_out)
    return model

bi_gru_model = load_bi_gru_model()

# === FUNCTIONS ===

def extract_text_from_file(file_obj, file_type):
    text = ""
    if file_type == "pdf":
        pdf_reader = PdfReader(file_obj)
        text = "\n\n".join([page.extract_text().strip() for page in pdf_reader.pages if page.extract_text()])
    elif file_type == "docx":
        doc = DocxDocument(file_obj)
        text = "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text])
    elif file_type == "image":
        image = Image.open(file_obj)
        text = pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type.")
    return text


def predict_verdict(case_details):
    """
    Predict the verdict using Bi-GRU + Gemini for rationale.
    :param case_details: str
    :return: dict with verdict, rationale, and laws
    """
    # Replace with real embeddings in production
    embedded_input = np.random.randn(1, 512, 768)
    bi_gru_prediction = bi_gru_model.predict(embedded_input)
    bi_gru_verdict = "Guilty" if bi_gru_prediction[0][0] > 0.5 else "Not Guilty"

    # Build Gemini prompt
    prompt = f"""
You are an AI Legal Assistant specialized in Indian law.

Provide the rationale and relevant laws to support the predicted verdict: {bi_gru_verdict} as per given below response format having

Response format:
Rationale: (Short, concise, in future tense and directly to the point)
Relevant Laws: (List legal references or principles that support the verdict) and give only the details and not say anything extra.
This the case details {case_details}
"""
    gemini_response = model_gemini.generate_content(prompt).text.strip()

    return {
        "verdict": bi_gru_verdict,
        "analysis": gemini_response
    }

# === EXAMPLE USAGE ===
# (Uncomment to test standalone)

# file_text = extract_text_from_file("example.pdf", "pdf")
# result = predict_verdict(file_text)
# print(result["verdict"])
# print(result["analysis"])
