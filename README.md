# Oracle Cloud Always Free 12GB VM Launcher (ap-mumbai-1)

આ સ્ક્રિપ્ટ મુંબઈ રીજન (`ap-mumbai-1`) માં **Oracle Cloud Always Free Ampere A1 (ARM64)** વર્ચ્યુઅલ મશીન (2 OCPU + 12 GB RAM) બનાવવા માટે તૈયાર કરવામાં આવી છે.

જ્યારે પણ મુંબઈ રીજનમાં કેપેસિટી ખાલી થશે (Capacity Available), આ સ્ક્રિપ્ટ તરત જ તમારા એકાઉન્ટમાં VM બનાવી લેશે.

---

## 🛠️ Step-by-Step ગાઈડ (ફક્ત 2 સ્ટેપ)

### સ્ટેપ ૧: Private Key ફાઇલ મુકો
જ્યારે તમે Oracle Cloud માં API Key બનાવી ત્યારે બ્રાઉઝરમાંથી એક `.pem` ફાઇલ ડાઉનલોડ થઈ હશે (દા.ત. `oci_api_key.pem` અથવા `xxxx.pem`).

👉 તે ફાઇલને આ જ ફોલ્ડરમાં મૂકો અને તેનું નામ બદલીને **`oci_api_key.pem`** રાખો.

*(જો ફાઇલનું નામ બીજું રાખવું હોય તો [oci_config.ini](file:///c:/Users/hp/JC-Panchal%20-3d8d/New%20folder%20%282%29/oci_config.ini) માં `key_file` લાઇન બદલી શકો છો)*

---

### સ્ટેપ ૨: સ્ક્રિપ્ટ ચલાવો
ટર્મિનલમાં નીચેનો કમાન્ડ રન કરો અથવા `run.bat` પર ડબલ ક્લિક કરો:

```powershell
python oci_vm_launcher.py
```

---

## 🚀 સ્ક્રિપ્ટ શું કરશે:
1. **ઓટોમેશન:**
   - તમારા ક્રેડેન્શિયલ ચેક કરશે.
   - મુંબઈનું Availability Domain (`AP-MUMBAI-1-AD-1`) પસંદ કરશે.
   - VCN અને Public Subnet જો નહિ હોય તો ઓટોમેટિક બનાવી લેશે.
   - લેટેસ્ટ Ubuntu 24.04 / 22.04 ARM64 OS સિલેક્ટ કરશે.
   - તમારા માટે નવો SSH Keypair (`oci_vm_key` / `oci_vm_key.pub`) ઓટોમેટિક જનરેટ કરી દેશે.

2. **ઓટોમેટિક રીટ્રાય (Auto Retry):**
   - મુંબઈમાં "Out of host capacity" હોવાથી દર 60 સેકન્ડે રિક્વેસ્ટ મોકલશે.
   - જેવી કેપેસિટી મળશે, તરત જ મશીન ક્રિએટ કરી દેશે અને કમ્પ્યુટરમાં બીપ (Sound) વગાડી એલર્ટ આપશે.

3. **કનેક્ટ કરવા માટે:**
   - VM બની ગયા પછી તેનો Public IP અને SSH કમાન્ડ સ્ક્રીન પર દેખાશે અને `instance_created.txt` માં સેવ થઈ જશે:
   ```bash
   ssh -i oci_vm_key ubuntu@<તમારો_PUBLIC_IP>
   ```
