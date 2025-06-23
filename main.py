import random
import os
import subprocess
import threading
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from keep_alive import keep_alive
from PIL import Image, ImageDraw, ImageFont
import nest_asyncio

nest_asyncio.apply()

DB_FILE = "stok_pet.txt"
GACHA_RESULTS_FILE = "gacha_results.txt"
BOT_TOKEN = "7843912872:AAEXYHad8y94shEMytMKvqaWH0nt_OdmUtk"


def init_db():
    for file in [DB_FILE, GACHA_RESULTS_FILE]:
        if not os.path.exists(file):
            open(file, 'w').close()


def read_stok():
    with open(DB_FILE, 'r') as f:
        return [
            line.strip().split('|') for line in f
            if line.strip() and len(line.strip().split('|')) == 3
        ]


def save_results(gacha_id, results, bonus, temp_stok):
    with open(DB_FILE, 'w') as f:
        for pet in temp_stok:
            f.write('|'.join(pet) + '\n')
    with open(GACHA_RESULTS_FILE, 'a') as f:
        f.write(f"--- ID Gacha {gacha_id} ({datetime.now()}) ---\n")
        for i, (name, tier) in enumerate(results, 1):
            f.write(f"{i}. {name} ({tier})\n")
        if bonus:
            f.write(f"\n🎁 Bonus Pet: {bonus[0]} ({bonus[1]})\n")
        f.write("\n")


def create_gacha_image(gacha_id, results, bonus):
    width, height = 600, 450
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    y = 20
    draw.text((20, y), f"Hasil Gacha ID: {gacha_id}", fill='black', font=font)
    y += 30

    for i, (name, tier) in enumerate(results, 1):
        draw.text((20, y), f"{i}. {name} ({tier})", fill='black', font=font)
        y += 30

    if bonus:
        y += 10
        draw.text((20, y),
                  f"🎁 Bonus Pet: {bonus[0]} ({bonus[1]})",
                  fill='darkblue',
                  font=font)

    filename = f"{gacha_id}.png"
    img.save(filename)
    return filename


def process_gacha(tier, temp_stok):
    available = [
        pet for pet in temp_stok if pet[1] == tier and int(pet[2]) > 0
    ]
    if not available:
        return None
    pet = random.choice(available)
    pet[2] = str(int(pet[2]) - 1)
    return (pet[0], pet[1])


def fallback_any_available(temp_stok):
    candidates = [pet for pet in temp_stok if int(pet[2]) > 0]
    if not candidates:
        return None
    pet = random.choice(candidates)
    pet[2] = str(int(pet[2]) - 1)
    return (pet[0], pet[1])


def do_gacha(qty):
    temp_stok = read_stok()
    results = []
    mythical_attempts = qty // 5
    normal_attempts = qty - mythical_attempts
    mythical_failed = 0

    for _ in range(mythical_attempts):
        pet = process_gacha("Mythical", temp_stok)
        if pet:
            results.append(pet)
        else:
            mythical_failed += 1

    total_to_draw = normal_attempts + mythical_failed
    for _ in range(total_to_draw):
        rand = random.random() * 100
        if rand < 10:
            tier = "Rare"
        elif rand < 40:
            tier = "Uncommon"
        else:
            tier = "Common"
        pet = process_gacha(tier, temp_stok)
        if not pet:
            pet = fallback_any_available(temp_stok)
        if pet:
            results.append(pet)

    bonus = fallback_any_available(temp_stok)
    return results, bonus, temp_stok


async def gacha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Gunakan format: /gacha jumlah\nContoh: /gacha 3")
        return
    try:
        jumlah = int(context.args[0])
        if jumlah <= 0:
            raise ValueError
    except:
        await update.message.reply_text("Jumlah harus angka positif!")
        return

    results, bonus, temp_stok = do_gacha(jumlah)
    if not results:
        await update.message.reply_text("Stok habis semua! ❌")
        return

    gacha_id = f"GACHA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pesan = f"🎁 Hasil Gacha (ID: {gacha_id}):\n"
    for i, (name, tier) in enumerate(results, 1):
        pesan += f"{i}. {name} ({tier})\n"
    if bonus:
        pesan += f"\nBonus Pet: {bonus[0]} ({bonus[1]})"
    pesan += "\n\nKonfirmasi gacha ini? Balas dengan /confirm"

    context.user_data['results'] = results
    context.user_data['bonus'] = bonus
    context.user_data['temp_stok'] = temp_stok
    context.user_data['gacha_id'] = gacha_id

    await update.message.reply_text(pesan)


async def confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'results' not in context.user_data:
        await update.message.reply_text(
            "Tidak ada gacha yang perlu dikonfirmasi.")
        return

    gacha_id = context.user_data['gacha_id']
    results = context.user_data['results']
    bonus = context.user_data['bonus']
    temp_stok = context.user_data['temp_stok']

    save_results(gacha_id, results, bonus, temp_stok)
    image_path = create_gacha_image(gacha_id, results, bonus)

    await update.message.reply_photo(photo=open(image_path, 'rb'))

    pet_list = "\n".join([f"🌟 {name}" for name, _ in results])
    bonus_text = f"\n\n🎁 Bonus Pet:\n🐾 {bonus[0]}" if bonus else ""
    message = (
        f"Halo Kak! Hasil spin dari sistem sudah keluar ya 😊\n"
        f"Berikut pet yang Kakak dapatkan (ID: {gacha_id}):\n\n"
        f"{pet_list}"
        f"{bonus_text}\n\n"
        f"Hasil spin ini bersifat permanen, karena langsung dihasilkan secara acak oleh sistem.\n"
        f"Username Kakak juga sudah tercatat di sistem, dan peluang mendapatkan pet langka akan meningkat "
        f"di pembelian berikutnya, dengan syarat Kakak memberikan konfirmasi ulasan positif bintang 5 setelah transaksi selesai ⭐⭐⭐⭐⭐\n\n"
        f"Apakah mau lanjut ke proses transaksi dan pengiriman sekarang, Kak? 😊"
    )
    await update.message.reply_text(message)

    context.user_data.clear()
    os.remove(image_path)


async def start_telegram_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("gacha", gacha_command))
    app.add_handler(CommandHandler("confirm", confirm_command))
    print("🚀 Bot Telegram aktif!")
    await app.run_polling()


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def safe_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return None


def add_stock():
    print("\nFormat: <nama_pet>|<tier>|<jumlah>")
    while True:
        entry = safe_input("> ")
        if entry is None or entry.strip() == "":
            break
        with open(DB_FILE, 'a') as f:
            f.write(f"{entry.strip()}\n")
        print(f"✔ Ditambahkan: {entry}")


def view_stock():
    print("\n=== DAFTAR STOK PET ===")
    try:
        with open(DB_FILE, 'r') as f:
            lines = [line.strip().split('|') for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Stok tidak ditemukan.")
        return

    stok = {}
    for pet in lines:
        if len(pet) != 3:
            continue
        name, tier, qty = pet
        if tier not in stok:
            stok[tier] = []
        stok[tier].append(f"{name} (x{qty})")

    if not stok:
        print("Stok kosong!")
    else:
        for tier in sorted(stok.keys()):
            print(f"\n[{tier.upper()}]")
            for item in stok[tier]:
                print(f"- {item}")


def gacha_pet():
    order_number = safe_input("Masukkan Nomor Pesanan Anda: ")
    if not order_number:
        return
    try:
        qty = int(safe_input("Jumlah pet yang ingin dibeli: "))
        if qty <= 0:
            raise ValueError
    except:
        print("Jumlah harus angka positif!")
        return

    results, bonus, temp_stok = do_gacha(qty)
    print("\n=== HASIL GACHA 🎉 ===")
    print(f"Nomor Pesanan: {order_number}")
    for i, (name, tier) in enumerate(results, 1):
        print(f"{i}. {name} ({tier})")
    print(f"\nBonus Pet: {bonus[0]} ({bonus[1]})")

    confirm = safe_input("\nKonfirmasi gacha ini? [Y/N]: ")
    if confirm and confirm.lower() == 'y':
        save_results(order_number, results, bonus, temp_stok)
        print("✔ Stok dikurangi & hasil disimpan.")
    else:
        print("❌ Gacha dibatalkan. Tidak ada perubahan stok.")


def start_terminal_menu():
    while True:
        clear_screen()
        print("=== MENU PET GACHA ===")
        print("1. Isi Stok Pet")
        print("2. Cek Stok Pet")
        print("3. Gacha Pet")
        print("4. Template Pembuka")
        print("5. Template Penutup")
        print("6. Keluar")
        menu = safe_input("\nPilih menu [1-6]: ")
        if not menu:
            break
        if menu == '1':
            add_stock()
        elif menu == '2':
            view_stock()
        elif menu == '3':
            gacha_pet()
        elif menu == '4':
            print("\n✨ Hai kak! Sistem sedang memproses gacha pet kakak... 🎁")
        elif menu == '5':
            print(
                "\n🎉 Terima kasih kak! Di pembelian berikutnya kakak akan lebih beruntung! Jangan lupa konfirmasi & kasih bintang 5 ya! ⭐️"
            )
        elif menu == '6':
            break
        else:
            print("Pilihan tidak valid.")
        input("\nTekan Enter untuk lanjut...")


async def main():
    init_db()
    keep_alive()
    try:
        subprocess.Popen(["python", "bot_stok.py"])
        print("✅ bot_stok.py berhasil dijalankan.")
    except Exception as e:
        print(f"❌ Gagal menjalankan bot_stok.py: {e}")
    threading.Thread(target=start_terminal_menu, daemon=True).start()
    await start_telegram_bot()


if __name__ == "__main__":
    asyncio.run(main())
