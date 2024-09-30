from pymongo import MongoClient

# Configura a conexão com o MongoDB
client = MongoClient("mongodb+srv://gabriel:123@cluster0.ojszv.mongodb.net/")
db = client['Aposta']  # Nome do banco de dados
usuarios_collection = db['usuarios']  # Coleção de usuários