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

3. **⚠️ DÔLEŽITÉ: Nastav GPS Mock (POVINNÉ):**
   - Nainštaluj `android-gps-mock/gps-mock.apk` na telefón (setup.command to spraví automaticky)
   - **Settings → Developer options → Select mock location app → GPS Mock**
   - *(Toto sa nedá automatizovať kvôli Android security)*

4. **⚠️ DÔLEŽITÉ: Reštartuj telefón:**
   ```bash
   adb reboot
   ```
   - *Nutné pri prvom setupe na vyčistenie GPS provider stavu*
   - Počkaj kým sa telefón reštartuje

5. **⚠️ DÔLEŽITÉ: Povol notifikácie GPS Mock (Android 13+):**
   - Pri prvom spustení GPS Mock aplikácie povoľ notifikácie
   - Alebo manuálne: **Settings → Apps → GPS Mock → Notifications → Povoliť**
   - *Nutné pre stabilný beh foreground service*

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
- Check logs: `cat ~/.appium-server.log`
- **Ak GUI nespúšťa Appium** (port obsadený, ale žiadny proces): **Reštartuj počítač** - zombie socket problém

### GPS Mock nefunguje (auto sa nehýbe na mape)

**1. Diagnostika:**
```bash
# Skontroluj či je GPS Mock nastavený
adb shell settings get secure mock_location_app
# Má vrátiť: com.roadlords.gpsmock

# Test GPS Mock
adb shell am start -n com.roadlords.gpsmock/.MainActivity
sleep 2
adb shell am broadcast -a com.roadlords.gpsmock.SET --ef lat 48.127 --ef lon 17.1072 -n com.roadlords.gpsmock/.CommandReceiver
adb shell dumpsys location | grep "last mock location"
# Má ukázať súradnice, nie "null"
```

**2. Časté problémy:**

| Problém | Riešenie |
|---------|----------|
| Mock location app nie je nastavený | Settings → Developer Options → Select mock location app → GPS Mock |
| GPS provider v zlom stave | Reštartuj telefón: `adb reboot` |
| Service nebeží (Android 13+) | Spusti: `adb shell am start -n com.roadlords.gpsmock/.MainActivity` |
| Notifikácie blokované (Android 13+) | Settings → Apps → GPS Mock → Notifications → Povoliť |

**3. Kompletný reset:**
```bash
adb uninstall com.roadlords.gpsmock
adb reboot
# Počkaj na reboot
adb install -r android-gps-mock/gps-mock.apk
# Nastav ako mock location provider v Settings
adb reboot
```

**Podrobný troubleshooting:** Pozri `README.md` sekcia "## Troubleshooting"

### Test padá
- Skontroluj či je nainštalovaný Roadlords na telefóne
- Skontroluj či má telefón povolené všetky permissions pre Roadlords
