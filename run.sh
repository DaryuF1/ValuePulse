#!/bin/bash
cd "$(dirname "$0")"

# Funcție pentru a elibera portul
cleanup_port() {
    fuser -k 8501/tcp 2>/dev/null
}

echo "================================"
echo "      PariuBot Controller       "
echo "================================"
echo "1. Rulează varianta WEB (app.py + Browser Automat)"
echo "2. Rulează varianta CLI (main.py - Fără browser)"
echo "3. Ieșire"
echo "================================"
read -p "Alege opțiunea [1-3]: " choice

case $choice in
    1)
        echo "Pregătire mediului Web..."
        cleanup_port
        
        # Pornim Streamlit în fundal
        ./venv/bin/streamlit run app.py --server.port 8501 --server.headless true &
        
        # Așteptăm serverul și deschidem browserul
        echo "Aștept ca serverul să pornească..."
        sleep 4
        powershell.exe -Command "Start-Process 'http://localhost:8501'"
        echo "Aplicația rulează la http://localhost:8501"
        
        # Așteptăm ca procesul să fie închis manual de utilizator
        wait
        ;;
        
    2)
        echo "Rulez varianta CLI (main.py)..."
        cleanup_port
        # Rulăm direct în terminal pentru a permite input-ul tău
        ./venv/bin/python3 main.py
        ;;
        
    3)
        echo "La revedere!"
        exit 0
        ;;
        
    *)
        echo "Opțiune invalidă. Rulează din nou scriptul."
        ;;
esac
