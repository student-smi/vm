# 🚀 OmniRoute + Claude Code + RuFlow સર્વર ગાઈડ

આ ગાઈડની મદદથી તમે તમારી ફ્રી Oracle Cloud VM પર **OmniRoute, Claude Code અને RuFlow** નું આખું AI Swarm ચલાવી શકશો.

---

## 🌟 ૧. VM બન્યા પછી કેવી રીતે કનેક્ટ થવું?

જેવી VM બનશે, તમારા ફોલ્ડરમાં `instance_created.txt` બની જશે જેમાં VM નો **Public IP** અને **SSH Command** હશે:

```bash
ssh -i oci_vm_key ubuntu@<તમારો_PUBLIC_IP>
```

---

## ⚡ ૨. One-Click AI Stack ઇન્સ્ટોલ કરવું

VM માં લૉગિન કર્યા પછી ફક્ત આ ૧ જ કમાન્ડ રન કરો:

```bash
curl -fsSL https://raw.githubusercontent.com/student-smi/vm/main/setup_ai_server.sh | sudo bash
```
*(અથવા જો ફાઇલ ઓલરેડી હોય તો: `sudo bash setup_ai_server.sh`)*

આ કમાન્ડ આપોઆપ:
1. **4GB Swap Memory** બનાવશે જેથી ક્યારેય RAM ઓછી ન પડે.
2. **Node.js 20 LTS** & Python ઇન્સ્ટોલ કરશે.
3. **OmniRoute** (Port 20128) બેકગ્રાઉન્ડમાં 24/7 PM2 વડે ચાલુ કરી દેશે.
4. **Claude Code CLI** અને **RuFlow (Ruflo)** ઇન્સ્ટોલ કરી દેશે.

---

## 🌐 ૩. OmniRoute સેટઅપ (Free AI Models જોડવા માટે)

1. તમારા બ્રાઉઝરમાં ખોલો:
   `http://<તમારો_PUBLIC_IP>:20128`
2. ત્યાં તમારા **Gemini (Free API Key)**, **Groq (Free & Fast Key)**, **DeepSeek** કે **OpenRouter** ના API Keys એડ કરી દો.
3. OmniRoute આ તમામ મોડલ્સને એક સિંગલ એન્ડપોઇન્ટ આપશે.

---

## 🤖 ૪. RuFlow અને Claude Code ચલાવવું

VM ના ટર્મિનલમાં કોઈપણ પ્રોજેક્ટ ફોલ્ડરમાં જાઓ:

```bash
# ૧. પ્રોજેક્ટ શરૂ કરો
mkdir my-saas-project && cd my-saas-project

# ૨. RuFlow Swarm ઇનિશિયલાઇઝ કરો
ruflo init

# ૩. Claude Code સ્ટાર્ટ કરો
claude
```

હવે 60+ AI એજન્ટ્સ તમારી નવી VM પર 24/7 પેરેલલમાં કોડિંગ, ટેસ્ટિંગ અને ડેવલપમેન્ટ કરશે!
