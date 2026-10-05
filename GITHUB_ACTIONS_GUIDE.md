# 🚀 GitHub Actions પર 24/7 OCI VM Launcher સેટઅપ ગાઈડ

આ સેટઅપ પછી તમારે તમારું કમ્પ્યુટર ચાલુ રાખવાની જરૂર નથી. GitHub ના સર્વર પર આ સ્ક્રિપ્ટ **દર ૩૦ મિનિટે ઓટોમેટિક ૨૪ કલાક ચાલતી રહેશે** અને જેવી મુંબઈમાં કેપેસિટી મળશે, તરત જ તમારા માટે ૧૨ GB વાળી VM બનાવી લેશે!

---

## 🔒 સ્ટેપ ૧: GitHub પર Private Repository બનાવો

1. તમારા બ્રાઉઝરમાં [github.com](https://github.com) પર જાઓ.
2. ઉપર જમણી બાજુ **`+`** પર ક્લિક કરીને **`New repository`** પસંદ કરો.
3. **Repository name:** `oci-mumbai-vm` (કોઈપણ નામ રાખી શકો છો).
4. ⚠️ **ખાસ ધ્યાન રાખો:** **`Private`** સિલેક્ટ કરવું (Public રાખવું નહીં).
5. નીચે **`Create repository`** બટન પર ક્લિક કરો.

---

## 💻 સ્ટેપ ૨: આ કોડને GitHub પર પુશ (Push) કરો

તમારા કમ્પ્યુટરમાં આ જ ફોલ્ડરમાં PowerShell ખોલો અને નીચેના ૩ કમાન્ડ રન કરો:
*(તમારા GitHub repo ની લિંક મૂકવી)*

```powershell
git branch -M main
git remote add origin https://github.com/<તમારું_USERNAME>/oci-mumbai-vm.git
git push -u origin main
```

---

## 🔐 સ્ટેપ ૩: GitHub Repository Secrets ઉમેરો (સૌથી મહત્વનું)

1. તમારા GitHub repo માં જાઓ.
2. ઉપર **`Settings`** ટેબ પર ક્લિક કરો.
3. ડાબી બાજુની મેનૂમાંથી **`Secrets and variables`** ➡️ **`Actions`** પર ક્લિક કરો.
4. **`New repository secret`** બટન પર ક્લિક કરીને નીચે મુજબના ૪ Secrets ઉમેરો:

### ૧. OCI_USER
- **Name:** `OCI_USER`
- **Secret:** `ocid1.user.oc1..aaaaaaaaea2sa3nojwdsyuzwlj7otvtpcslzdvfo5fkena7z3daraf6vgp6q`

### ૨. OCI_FINGERPRINT
- **Name:** `OCI_FINGERPRINT`
- **Secret:** `23:03:c3:c2:8a:e7:c8:91:07:55:30:4b:65:15:c4:8b`

### ૩. OCI_TENANCY
- **Name:** `OCI_TENANCY`
- **Secret:** `ocid1.tenancy.oc1..aaaaaaaaljlosxqdwdj7nosnrujmaa6azsjhxtzhw3tstvas7d7k4q6sc4ba`

### ૪. OCI_KEY_CONTENT
- **Name:** `OCI_KEY_CONTENT`
- **Secret:** તમારા ફોલ્ડરમાં રહેલી `.pem` ફાઇલ (`smitpanchal734@gmail.com-2026-10-05T12_54_54.881Z.pem`) ને Notepad માં ખોલો.
  તેમાં રહેલું બધું લખાણ (જેમાં `-----BEGIN PRIVATE KEY-----` થી લઈને `-----END PRIVATE KEY-----` સુધીનું બધું) કૉપિ કરીને અહીં પેસ્ટ કરી દો.

---

## 📱 સ્ટેપ ૪ (ઓપ્શનલ): મોબાઇલમાં Telegram એલર્ટ મેળવવા માટે

જો VM બન્યા પછી તમને મોબાઇલમાં સીધો મેસેજ જોઈતો હોય:
1. `TELEGRAM_BOT_TOKEN` : તમારા Telegram Bot નો ટોકન
2. `TELEGRAM_CHAT_ID` : તમારો Telegram Chat ID

*(જો આ ન મુકવું હોય તો સ્ક્રિપ્ટ એમનેમ પણ કામ કરશે)*

---

## ▶️ સ્ટેપ ૫: Workflow ચાલુ કરો

1. GitHub repo માં ઉપર **`Actions`** ટેબ પર ક્લિક કરો.
2. જો પૂછે તો **`I understand my workflows, go ahead and enable them`** પર ક્લિક કરો.
3. ડાબી બાજુ **`OCI 12GB Mumbai VM Auto-Launcher`** પર ક્લિક કરો.
4. જમણી બાજુ **`Run workflow`** બટન પર ક્લિક કરો.

બસ! હવે GitHub 24 કલાક સતત દર 30 મિનિટે બેકગ્રાઉન્ડમાં ઓટોમેટિક સ્ક્રિપ્ટ રન કરશે. જેવું મુંબઈમાં સર્વર ફ્રી થશે કે તરત જ તમારું VM બની જશે!
