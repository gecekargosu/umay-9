from rag.memory_manager import add_memory

knowledge = """
Benim adım Cengiz Kılıç.
UMAY, benim geliştirdiğim kişisel yapay zeka asistanı projesidir.
UMAY'ın amacı: yerel çalışan, hafızası olan, çoklu ajan destekli kişisel yapay zeka sistemi oluşturmaktır.
UMAY ChromaDB hafıza, Ollama modelleri ve RAG mimarisi kullanır.
"""

if add_memory(knowledge, source="initial_knowledge"):
    print("UMAY bilgiyi öğrendi.")
else:
    print("Bilgi zaten hafızada.")
