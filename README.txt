═══════════════════════════════════════════════════
  OG IOS SHOP — Telegram Bot
═══════════════════════════════════════════════════

SETUP
-----
1. Install Python 3.10+ on your server/VPS.

2. Install dependencies:
   pip install -r requirements.txt

3. (Optional) Place payment QR images in the same folder:
   • UPI  : upi_qr.jpg   (or upi_qr.png)
   • Binance: binance_qr.jpg (or binance_qr.png)

4. Run the bot:
   python3 bot.py

   Or with env variable (recommended):
   BOT_TOKEN=YOUR_TOKEN python3 bot.py

PRODUCTS
--------
  Free Fire (iOS):
  • Fluorite  — 31D $23 / 7D $15 / 1D $5
  • Proxy     — 31D $20 / 7D $10 / 1D $3
  • Fliza     — 31D $20 / 7D $10 / 1D $3
  • Migul     — 31D $20 / 7D $10 / 1D $3

ADMIN PANEL FEATURES
--------------------
  • Add Keys       — add license keys per product & duration
  • Add File       — add IPA/ZIP/link per product (auto-sent on purchase)
  • View Keys Stock — see how many keys per slot
  • View Files Stock — see how many files per product
  • Remove File    — remove next or all files from a product
  • Remove Keys    — clear all keys (with confirmation)
  • Add Balance    — top up a user's balance (USER_ID AMOUNT)
  • Deduct Balance — subtract from a user's balance
  • Check Balance  — look up any user's balance
  • Add Admin      — promote a user to admin by Telegram ID
  • Broadcast      — send a message to all verified users

ADMIN IDs (hardcoded)
---------------------
  8503115617 / 6761125512 / 6617032248

HOW KEYS WORK
-------------
  Keys are stored per product+duration slot.
  When a purchase is approved, the next key is popped from the queue
  and sent to the buyer. A file (if loaded) is also sent automatically.

HOW PAYMENT WORKS
-----------------
  1. User selects product → duration → payment method.
  2. For UPI / Binance: user sends screenshot → admin approves/denies.
  3. For Balance: instant delivery if balance is sufficient.

SUPPORT CONTACTS (edit in bot.py)
----------------------------------
  @Mar1xff  @Bhavisss  @Pssysmglr
