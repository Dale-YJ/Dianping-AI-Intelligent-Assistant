import os
from sentence_transformers import SentenceTransformer

sentences = ["This is an example sentence", "Each sentence is converted"]

# 使用脚本所在目录的绝对路径，无论从哪里运行都能找到模型
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "models", "all-MiniLM-L6-v2")
model = SentenceTransformer(model_path)
embeddings = model.encode(sentences)
print(f"Embedding shape: {embeddings.shape}")
print(embeddings)