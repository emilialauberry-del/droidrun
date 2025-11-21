# 🚀 Guide DroidRun pour Client

Bienvenue ! Ce guide vous explique comment utiliser DroidRun dans votre propre GitHub Codespace.

## 📋 Prérequis

- Un compte GitHub
- Un téléphone Android (pour les tests réels)
- Une clé API Google Gemini

## 🛠️ Installation rapide

1. **Ouvrez ce repository dans GitHub Codespace :**
   - Allez sur https://github.com/droidrun/droidrun
   - Cliquez sur "Code" → "Codespaces" → "Create codespace on main"

2. **Exécutez le script de configuration :**
   ```bash
   ./setup_droidrun.sh
   ```

3. **Configurez votre clé API Google Gemini :**
   - Allez sur https://makersuite.google.com/app/apikey
   - Créez une clé API
   - Dans le terminal Codespace :
   ```bash
   export GOOGLE_API_KEY=votre-cle-api-ici
   ```

## 🧪 Test de l'installation

```bash
# Vérifier que DroidRun fonctionne
droidrun --help

# Lister les appareils (aucun pour l'instant)
droidrun devices
```

## 📱 Connexion de votre téléphone Android

### Préparation du téléphone :
1. **Activer les options développeur :**
   - Paramètres → À propos du téléphone
   - Tapez 7 fois sur "Numéro de build"
   - Retour → Options développeur activées

2. **Activer le débogage USB :**
   - Paramètres → Options développeur
   - Activer "Débogage USB"

3. **Connecter le téléphone :**
   - Branchez votre téléphone en USB à votre ordinateur
   - Acceptez le débogage sur votre téléphone

### ⚠️ Limitation importante

**GitHub Codespace ne peut PAS accéder directement à votre téléphone USB !**

Pour utiliser DroidRun avec votre téléphone, vous avez 2 options :

## ✅ Solution 1 : DroidRun Cloud (Recommandé)

Utilisez le service officiel cloud qui gère tout automatiquement :

1. Allez sur https://cloud.droidrun.ai/sign-in
2. Créez un compte
3. Suivez les instructions pour connecter votre téléphone
4. Utilisez l'interface web pour contrôler votre Android

## ✅ Solution 2 : Installation locale

Installez DroidRun sur votre propre ordinateur :

```bash
# Installation
pip install 'droidrun[google,anthropic,openai,deepseek,ollama,dev]'

# Configuration
export GOOGLE_API_KEY=votre-cle-api
droidrun setup  # Installe le Portal sur le téléphone
droidrun ping   # Test de connexion
droidrun run "Ouvre les paramètres"  # Test
```

## 🎯 Exemples de commandes

Une fois votre téléphone connecté (localement ou via cloud) :

```bash
# Ouvrir les paramètres
droidrun run "Ouvre les paramètres"

# Vérifier la batterie
droidrun run "Vérifie le niveau de batterie"

# Prendre une capture d'écran
droidrun run "Prends une capture d'écran" --vision

# Tâche complexe avec planification
droidrun run "Trouve un contact nommé John et envoie-lui un email" --reasoning
```

## 📖 Ressources

- [Documentation officielle](https://docs.droidrun.ai)
- [DroidRun Cloud](https://cloud.droidrun.ai)
- [Configuration avancée](https://docs.droidrun.ai/v3/sdk/configuration)

## ❓ Support

Si vous avez des questions :
- Consultez la [documentation](https://docs.droidrun.ai)
- Rejoignez le [Discord](https://discord.gg/ZZbKEZZkwK)

---

**Note :** Ce guide suppose que vous utilisez la configuration par défaut avec Google Gemini. Pour d'autres fournisseurs LLM, consultez la documentation de configuration.