import sys

def main():
    try:
        print("Démarrage de FlowerApp...")
        # Your logic goes here
        print("Application logic started successfully.")
    except Exception as e:
        print(f"Erreur lors de l'exécution : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()