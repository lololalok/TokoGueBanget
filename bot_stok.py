import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

DB_FILE = "stok_pet.txt"
BOT_TOKEN = "7328409505:AAGjaN14TZjpdO8BG0wb_QPRm23eY2ZsU2Y"

# Kurangi log httpx & telegram.ext
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.basicConfig(format="%(message)s", level=logging.WARNING)


# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang di Bot Stok Pet!\nKetik /menu untuk melihat semua perintah."
    )


# /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""📚 Daftar Perintah:
/tambahstok - Tambah stok pet (multibaris)
/cekstok - Lihat seluruh stok
/clearstok - Hapus seluruh stok
/hapuspet <Nama> - Hapus pet berdasarkan nama
/editstok <Nama> <Tier> <JumlahBaru> - Edit stok pet
/caripet <Nama> - Cari pet (boleh sebagian nama)
/jumlahstok - Lihat total semua stok
/exportstok - Ekspor stok ke file
/stats - Statistik jumlah per tier
/tambahjumlah <Nama> <Jumlah> - Tambah jumlah pet
/kurangjumlah <Nama> <Jumlah> - Kurangi jumlah pet""")


# /tambahstok
async def tambahstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Silakan kirim daftar pet (Nama Tier Jumlah) baris per baris.\nContoh:\nBunny Common 12\nBee Rare 5"
    )
    context.user_data["awaiting_stok_input"] = True


# Handler teks
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_stok_input"):
        lines = update.message.text.strip().split('\n')
        added, failed = [], []
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 3:
                failed.append(line)
                continue
            name, tier = parts[0], parts[1]
            try:
                qty = int(parts[2])
                if qty <= 0: raise ValueError
                with open(DB_FILE, 'a') as f:
                    f.write(f"{name}|{tier}|{qty}\n")
                added.append(f"{name} ({tier}) x{qty}")
            except:
                failed.append(line)
        msg = ""
        if added: msg += "✅ Ditambahkan:\n" + "\n".join(added) + "\n"
        if failed: msg += "⚠️ Gagal tambah:\n" + "\n".join(failed)
        await update.message.reply_text(msg.strip())
        context.user_data["awaiting_stok_input"] = False


# /cekstok
async def cekstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(DB_FILE, 'r') as f:
            lines = f.readlines()
        msg = '\n'.join(line.strip()
                        for line in lines if line.strip()) or "Stok kosong."
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("❌ Gagal membaca stok.")


# /clearstok
async def clearstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        open(DB_FILE, 'w').close()
        await update.message.reply_text("✅ Semua stok telah dihapus.")
    except:
        await update.message.reply_text("❌ Gagal menghapus stok.")


# /hapuspet
async def hapuspet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: /hapuspet <Nama>")
        return
    target = ' '.join(context.args).lower()
    try:
        with open(DB_FILE, 'r') as f:
            lines = f.readlines()
        lines = [
            line for line in lines if not line.lower().startswith(target + "|")
        ]
        with open(DB_FILE, 'w') as f:
            f.writelines(lines)
        await update.message.reply_text(
            f"✅ Pet bernama '{target}' dihapus (jika ada).")
    except:
        await update.message.reply_text("❌ Gagal menghapus pet.")


# /editstok
async def editstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Format: /editstok <Nama> <Tier> <JumlahBaru>")
        return
    try:
        name, tier, qty = context.args[0], context.args[1], int(
            context.args[2])
        updated, new_lines = False, []
        with open(DB_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 3 and parts[0].lower() == name.lower():
                    new_lines.append(f"{name}|{tier}|{qty}\n")
                    updated = True
                else:
                    new_lines.append(line)
        with open(DB_FILE, 'w') as f:
            f.writelines(new_lines)
        await update.message.reply_text(
            "✅ Stok diperbarui." if updated else "❌ Pet tidak ditemukan.")
    except:
        await update.message.reply_text("❌ Format salah atau error.")


# /caripet
async def caripet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: /caripet <Nama>")
        return
    keyword = ' '.join(context.args).lower()
    try:
        with open(DB_FILE, 'r') as f:
            results = [
                line.strip() for line in f
                if keyword in line.lower().split('|')[0]
            ]
        await update.message.reply_text(
            '\n'.join(results) if results else "❌ Pet tidak ditemukan.")
    except:
        await update.message.reply_text("❌ Gagal mencari pet.")


# /jumlahstok
async def jumlahstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(DB_FILE, 'r') as f:
            total = sum(
                int(line.strip().split('|')[2]) for line in f if '|' in line)
        await update.message.reply_text(f"📦 Total semua stok: {total} pet")
    except:
        await update.message.reply_text("❌ Gagal menghitung stok.")


# /exportstok
async def exportstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(DB_FILE, 'r') as f_in, open("export_stok.txt", 'w') as f_out:
            f_out.write("--- Data Stok Pet ---\n" + ''.join(f_in))
        await update.message.reply_document(
            document=open("export_stok.txt", "rb"))
    except:
        await update.message.reply_text("❌ Gagal ekspor atau kirim file.")


# /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tiers = {}
        with open(DB_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 3:
                    tier, qty = parts[1].capitalize(), int(parts[2])
                    tiers[tier] = tiers.get(tier, 0) + qty
        if tiers:
            msg = "📊 Statistik per Tier:\n" + '\n'.join(
                f"- {k}: {v}" for k, v in sorted(tiers.items()))
        else:
            msg = "Stok kosong."
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("❌ Gagal menghitung statistik.")


# /tambahjumlah
async def tambahjumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "Format: /tambahjumlah <Nama> <Jumlah>")
            return
        keyword = ' '.join(context.args[:-1]).lower()
        tambah = int(context.args[-1])
        updated, new_lines = False, []
        with open(DB_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts
                       ) == 3 and not updated and keyword in parts[0].lower():
                    jumlah_baru = int(parts[2]) + tambah
                    new_lines.append(f"{parts[0]}|{parts[1]}|{jumlah_baru}\n")
                    updated = True
                else:
                    new_lines.append(line)
        with open(DB_FILE, 'w') as f:
            f.writelines(new_lines)
        await update.message.reply_text(
            "✅ Ditambah." if updated else "❌ Pet tidak ditemukan.")
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus angka.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# /kurangjumlah
async def kurangjumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "Format: /kurangjumlah <Nama> <Jumlah>")
            return
        keyword = ' '.join(context.args[:-1]).lower()
        kurang = int(context.args[-1])
        updated, new_lines = False, []
        with open(DB_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts
                       ) == 3 and not updated and keyword in parts[0].lower():
                    jumlah_baru = max(0, int(parts[2]) - kurang)
                    new_lines.append(f"{parts[0]}|{parts[1]}|{jumlah_baru}\n")
                    updated = True
                else:
                    new_lines.append(line)
        with open(DB_FILE, 'w') as f:
            f.writelines(new_lines)
        await update.message.reply_text(
            "✅ Dikurangi." if updated else "❌ Pet tidak ditemukan.")
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus angka.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("tambahstok", tambahstok))
    app.add_handler(CommandHandler("cekstok", cekstok))
    app.add_handler(CommandHandler("clearstok", clearstok))
    app.add_handler(CommandHandler("hapuspet", hapuspet))
    app.add_handler(CommandHandler("editstok", editstok))
    app.add_handler(CommandHandler("caripet", caripet))
    app.add_handler(CommandHandler("jumlahstok", jumlahstok))
    app.add_handler(CommandHandler("exportstok", exportstok))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("tambahjumlah", tambahjumlah))
    app.add_handler(CommandHandler("kurangjumlah", kurangjumlah))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot Started ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
