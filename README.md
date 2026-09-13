# HIND DEALS BOT — main.py

## Run
pip install -r requirements.txt
python main.py

## Payment Gateway (iPey.shop) — one-time setup
1. Bot me owner/admin se `/gateway` bhejo (ya Admin Panel -> ⚡ PAYMENT GATEWAY).
2. "🔑 SET API TOKEN" dabao aur iPey.shop panel (https://ipey.shop/auth/index -> login -> API / Developer)
   ka `user_token` paste karo. Token save hote hi gateway ON ho jata hai.
3. "🧪 TEST GATEWAY" se check karo — link aaye to sab sahi hai.
4. Panel URL badalna ho to "🌐 SET PANEL URL", minimum amount "💵 SET MIN AMOUNT".

Payment aane par wallet/order har 15 second me AUTO confirm hota hai (koi screenshot nahi).
Users: `/addmoney` ya Wallet -> ⚡ ADD MONEY, aur buy karte waqt "⚡ PAY ONLINE — AUTO".
Gateway OFF ho to purana QR/UPI + wallet flow waise hi chalta hai.

## Naye changes (fix update)
- 🕙 **QR 10 minute valid** — ek hi amount ka QR baar-baar generate nahi hota. Andar `QR_VALID_MIN = 10`.
- 💳 **`qr` ya `/qr`** likhne par bot amount poochta hai, phir usi amount ka QR bhejta hai (`qr 100` bhi chalta hai).
- ⛔ **Auto approval OFF** — `AUTO_APPROVAL = False`. Har payment admin manually approve karta hai (gateway auto-verify loop band).
- 🎨 **Button styles** — har button par colour marker: 🔵 primary, 🟢 success, 🔴 danger.
- 🧾 **Manual payment approval card** — screenshot aane par admin ko milta hai: buyer ka Name, Username, Buyer ID, Payment Method (QR/UPI), Amount, Order/Deposit ID, aur Product name ya **WALLET TOP-UP**, saath me 🟢 APPROVE / 🔴 DECLINE buttons.
