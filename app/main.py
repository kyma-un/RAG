from .logging.SQLiteLogger import SQLiteLogger
from .rag import RAG

def main():
    print("initializing RAG system...")

    # Iniciar el Logger
    logger = SQLiteLogger()

    # Inicializar el RAG
    rag = RAG(logger)

    print("Sistema listo. escribir exit para salir. \n")

    while True:
        question = input("Query:")

        if question.lower() == "exit":
            print("Saliendo...")
            break

        result = rag.query(question)
        print(f"Answer: {result['answer']}")
        print(f"Context: {result['context']}")
        print(f"Response time: {result['response_time']:.2f} s")


if __name__ == "__main__":
    main()
