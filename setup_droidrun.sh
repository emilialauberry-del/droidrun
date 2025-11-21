#!/bin/bash

# Script de configuration DroidRun pour GitHub Codespace
# Ce script reproduit la configuration que nous avons faite

echo "🚀 Configuration de DroidRun dans GitHub Codespace"
echo "=================================================="

# 1. Vérifier Python
echo "📋 Vérification de Python..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python n'est pas installé"
    exit 1
fi

# 2. Installer ADB
echo "🔧 Installation d'ADB..."
sudo apt update && sudo apt install -y android-tools-adb

# 3. Installer DroidRun en mode développement
echo "📦 Installation de DroidRun..."
pip install -e .

# 4. Installer les dépendances Google Gemini
echo "🤖 Installation des dépendances Google Gemini..."
pip install 'droidrun[google]'

# 5. Créer le fichier de configuration
echo "⚙️  Configuration créée automatiquement au premier lancement"

echo ""
echo "✅ Configuration terminée !"
echo ""
echo "📝 Prochaines étapes pour votre client :"
echo "1. Obtenir une clé API Google Gemini : https://makersuite.google.com/app/apikey"
echo "2. Exécuter : export GOOGLE_API_KEY=votre-cle-api"
echo "3. Tester : droidrun --help"
echo ""
echo "📱 Pour connecter un téléphone Android :"
echo "- Activer les options développeur"
echo "- Activer le débogage USB"
echo "- Connecter en USB"
echo "- Exécuter : droidrun setup"
echo "- Tester : droidrun ping"
echo ""
echo "🎯 Exemple de commande :"
echo 'droidrun run "Ouvre les paramètres et vérifie la version Android"'
echo ""
echo "⚠️  Note : Codespace ne peut pas accéder directement aux appareils USB locaux."
echo "   Pour un usage réel, utilisez DroidRun Cloud : https://cloud.droidrun.ai"