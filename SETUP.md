# Roadlords Test Runner - Setup Guide

## Quick Start (Automatic Installation)

### Mac
1. Rozbaľ ZIP súbor
2. Dvojklik na **`setup.command`**
3. Po inštalácii dvojklik na **`Run Roadlords Test.command`**

### Windows
1. Rozbaľ ZIP súbor
2. Pravý klik na **`setup.bat`** → **"Spustiť ako správca"**
3. Po inštalácii dvojklik na **`Run Roadlords Test.bat`**

**Čo sa nainštaluje automaticky:**
- Python 3, Node.js, ADB, Appium + UiAutomator2 driver

---

## Manuálna inštalácia

Ak automatická inštalácia nefunguje, nainštaluj manuálne:

### 1. Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Python 3
```bash
brew install python
```

### 3. Node.js
```bash
brew install node
```

### 4. Android Platform Tools (ADB)
```bash
brew install --cask android-platform-tools
```

### 5. Appium
```bash
npm install -g appium
appium driver install uiautomator2
```

### 6. Python dependencies
```bash
cd roadlords-automation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install flask
```

---

## Nastavenie telefónu

1. **Povol Developer Options:**
   - Settings → About phone → Build number (klikni 7x)

2. **Povol USB debugging:**
   - Settings → Developer options → USB debugging → ON

3. **Nastav GPS Mock:**
   - Nainštaluj `android-gps-mock/gps-mock.apk` na telefón
   - Settings → Developer options → Select mock location app → GPS Mock

---

## Spustenie testu

1. Pripoj telefón cez USB
2. Dvojklik na **`Run Roadlords Test.command`**
3. Otvorí sa prehliadač s testovacím rozhraním
4. Klikni **"Run Test"**
5. Report sa otvorí automaticky po dokončení

---

## Troubleshooting

### "No device connected"
- Skontroluj USB kábel
- Povol USB debugging na telefóne
- Na telefóne potvrď "Allow USB debugging"
- Spusti `adb devices` v terminále

### "Appium not running"
- Klikni "Start Appium" v aplikácii
- Alebo spusti `appium` v terminále

### GPS nefunguje
- Skontroluj či je GPS Mock nastavený ako Mock location app
- Reštartuj GPS Mock aplikáciu na telefóne

### Test padá
- Skontroluj či je nainštalovaný Roadlords na telefóne
- Skontroluj či má telefón povolené všetky permissions pre Roadlords
