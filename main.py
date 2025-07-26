#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram per Noleggio SUP - Versione Ottimizzata con Noleggi Giornalieri
Autore: Dino Bronzi
Data creazione: 26 Luglio 2025
Versione: 2.4 - Noleggi giornalieri + Foto ricevute
"""

import os
import csv
import json
import logging
from datetime import datetime
from collections import defaultdict
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Configura logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Stati conversazione
(DATA, COGNOME, NOME, DOCUMENTO, NUMERO_DOCUMENTO, TELEFONO, ASSOCIATO, TIPO_NOLEGGIO, 
 DETTAGLI_SUP, DETTAGLI_LETTINO, LETTINO_NUMERO, TEMPO, PAGAMENTO, IMPORTO, FOTO_RICEVUTA, NOTE) = range(16)

# File e directory
DATA_FILE = 'noleggi.json'
PHOTOS_DIR = 'ricevute_photos'
os.makedirs(PHOTOS_DIR, exist_ok=True)

class SupRentalBot:
    def __init__(self):
        self.noleggi = self.load_data()
    
    def load_data(self):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Creo nuovo database")
            return []
    
    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.noleggi, f, ensure_ascii=False, indent=2)
    
    def get_noleggi_oggi(self):
        """Restituisce solo i noleggi di oggi"""
        oggi = datetime.now().strftime('%d/%m/%Y')
        return [n for n in self.noleggi if n['data'] == oggi]

bot_instance = SupRentalBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Avvia registrazione"""
    await update.message.reply_text(
        "🏄‍♂️ **Benvenuto nel sistema noleggio SUP!**\n\n"
        "Inserisci la **data** (formato: DD/MM/YYYY):"
    )
    return DATA

async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida data e continua"""
    try:
        data_text = update.message.text
        data_obj = datetime.strptime(data_text, '%d/%m/%Y')
        
        # Verifica range valido
        if data_obj.year < 2025 or data_obj > datetime.now().replace(year=datetime.now().year + 1):
            await update.message.reply_text("❌ Data non valida. Usa formato DD/MM/YYYY (dal 2025):")
            return DATA
            
        context.user_data['data'] = data_text
        await update.message.reply_text("Inserisci il COGNOME:")
        return COGNOME
        
    except ValueError:
        await update.message.reply_text("❌ Formato errato. Usa DD/MM/YYYY:")
        return DATA

async def get_cognome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['cognome'] = update.message.text
    await update.message.reply_text("Inserisci il NOME:")
    return NOME

async def get_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['nome'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("C.I.", callback_data="doc_CI")],
        [InlineKeyboardButton("PAT", callback_data="doc_PAT")],
        [InlineKeyboardButton("PASS", callback_data="doc_PASS")],
        [InlineKeyboardButton("ALTRO", callback_data="doc_ALTRO")]
    ]
    
    await update.message.reply_text(
        "Seleziona tipo DOCUMENTO:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DOCUMENTO

async def get_numero_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    numero_doc = update.message.text.strip()
    if len(numero_doc) < 3:
        await update.message.reply_text("❌ Numero documento troppo corto (min 3 caratteri):")
        return NUMERO_DOCUMENTO
    
    context.user_data['numero_documento'] = numero_doc
    await update.message.reply_text("Inserisci TELEFONO:")
    return TELEFONO

async def get_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['telefono'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("✅ SÌ", callback_data="assoc_SI")],
        [InlineKeyboardButton("❌ NO", callback_data="assoc_NO")]
    ]
    
    await update.message.reply_text(
        "È ASSOCIATO?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASSOCIATO

async def get_importo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve importo con icona EUR"""
    importo_text = update.message.text.replace(',', '.').strip()
    
    try:
        importo = float(importo_text)
        if importo <= 0:
            raise ValueError
        
        # Usa icona EUR invece del simbolo €
        context.user_data['importo'] = f"{importo:.2f} EUR"
        
        keyboard = [
            [InlineKeyboardButton("📸 SÌ - Allego foto", callback_data="foto_SI")],
            [InlineKeyboardButton("❌ NO - Nessuna foto", callback_data="foto_NO")]
        ]
        
        await update.message.reply_text(
            f"✅ Importo: {context.user_data['importo']}\n\n📷 Allegare foto ricevuta?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return FOTO_RICEVUTA
        
    except ValueError:
        await update.message.reply_text("❌ Importo non valido (es: 25, 30.50):")
        return IMPORTO

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler unificato per tutti i callback"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Gestione noleggi multipli
    elif data == "altro_noleggio":
        # Ripristina i dati base del cliente
        if 'cliente_base' in context.user_data:
            context.user_data.update(context.user_data['cliente_base'])
        
        # Pulisce i dati del noleggio precedente
        for key in ['tipo_noleggio', 'dettagli', 'numero', 'tempo', 'pagamento', 'importo', 'foto_ricevuta', 'note']:
            context.user_data.pop(key, None)
        
        keyboard = [
            [InlineKeyboardButton("🏄‍♂️ SUP", callback_data="tipo_SUP")],
            [InlineKeyboardButton("🚣‍♂️ KAYAK", callback_data="tipo_KAYAK")],
            [InlineKeyboardButton("🏖️ LETTINO", callback_data="tipo_LETTINO")],
            [InlineKeyboardButton("📱 PHONEBAG", callback_data="tipo_PHONEBAG")],
            [InlineKeyboardButton("🎒 DRYBAG", callback_data="tipo_DRYBAG")]
        ]
        
        await query.edit_message_text(
            f"➕ **ALTRO NOLEGGIO PER:**\n"
            f"👤 {context.user_data.get('cognome', '')} {context.user_data.get('nome', '')}\n\n"
            f"Cosa noleggia ancora?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TIPO_NOLEGGIO
    
    elif data == "finito":
        # Calcola totale noleggi per questo cliente
        nome_completo = f"{context.user_data.get('cognome', '')} {context.user_data.get('nome', '')}"
        oggi = datetime.now().strftime('%d/%m/%Y')
        
        noleggi_cliente_oggi = [n for n in bot_instance.noleggi 
                               if n['data'] == oggi and 
                               f"{n.get('cognome', '')} {n.get('nome', '')}" == nome_completo]
        
        # Riassunto finale
        messaggio_finale = f"""
🎉 **REGISTRAZIONE COMPLETA!**

👤 **Cliente:** {nome_completo}
📅 **Data:** {oggi}
📱 **Telefono:** {context.user_data.get('telefono', '')}

🏄‍♂️ **NOLEGGI TOTALI:** {len(noleggi_cliente_oggi)}
        """
        
        # Lista tutti i noleggi
        for i, noleggio in enumerate(noleggi_cliente_oggi, 1):
            tipo_icon = {"SUP": "🏄‍♂️", "KAYAK": "🚣‍♂️", "LETTINO": "🏖️", "PHONEBAG": "📱", "DRYBAG": "🎒"}.get(noleggio['tipo_noleggio'], "📦")
            messaggio_finale += f"\n{i}. {tipo_icon} {noleggio['tipo_noleggio']} {noleggio['dettagli']} N.{noleggio['numero']} ({noleggio['tempo']}) - {noleggio.get('importo', 'N/A')}"
        
        messaggio_finale += f"\n\n💡 Usa `/mostra_noleggi` per vedere tutti i clienti di oggi"
        
        await query.edit_message_text(messaggio_finale)
        context.user_data.clear()
        return ConversationHandler.END
    if data.startswith("cliente_"):
        cliente_idx = int(data.replace("cliente_", ""))
        noleggi_oggi = bot_instance.get_noleggi_oggi()
        
        if cliente_idx < len(noleggi_oggi):
            registro = noleggi_oggi[cliente_idx]
            
            # Pulsante per vedere foto se presente
            keyboard = []
            if registro.get('foto_ricevuta'):
                keyboard.append([InlineKeyboardButton("📸 Vedi Foto Ricevuta", callback_data=f"foto_{cliente_idx}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            messaggio = f"""
👤 **{registro.get('cognome', '')} {registro.get('nome', '')}**

📞 {registro['telefono']}
📄 {registro['documento']} - {registro.get('numero_documento', '')}
🏅 Associato: {registro['associato']}

🏄‍♂️ **NOLEGGIO:**
• Tipo: {registro['tipo_noleggio']} {registro['dettagli']}
• Numero: {registro['numero']}
• Tempo: {registro['tempo']}

💰 **PAGAMENTO:**
• Tipo: {registro['pagamento']}
• Importo: {registro.get('importo', 'N/A')}

📝 Note: {registro.get('note', 'Nessuna nota')}
            """
            
            await query.edit_message_text(messaggio, reply_markup=reply_markup)
        
        return ConversationHandler.END
    
    # Gestione visualizzazione foto
    elif data.startswith("foto_"):
        cliente_idx = int(data.replace("foto_", ""))
        noleggi_oggi = bot_instance.get_noleggi_oggi()
        
        if cliente_idx < len(noleggi_oggi):
            registro = noleggi_oggi[cliente_idx]
            foto_filename = registro.get('foto_ricevuta')
            
            if foto_filename:
                foto_path = os.path.join(PHOTOS_DIR, foto_filename)
                if os.path.exists(foto_path):
                    with open(foto_path, 'rb') as foto:
                        await query.message.reply_photo(
                            photo=foto,
                            caption=f"📸 Ricevuta di {registro.get('cognome', '')} {registro.get('nome', '')}\n"
                                   f"💰 {registro.get('importo', 'N/A')} - {registro['pagamento']}"
                        )
                else:
                    await query.message.reply_text("❌ File foto non trovato")
            else:
                await query.message.reply_text("❌ Nessuna foto disponibile")
        
        return ConversationHandler.END
    
    # Documento
    if data.startswith("doc_"):
        documento = data.replace("doc_", "").replace("_", ".")
        context.user_data['documento'] = documento
        await query.edit_message_text(f"✅ Documento: {documento}\n\nInserisci NUMERO documento:")
        return NUMERO_DOCUMENTO
    
    # Associato
    elif data.startswith("assoc_"):
        associato = "SÌ" if data == "assoc_SI" else "NO"
        context.user_data['associato'] = associato
        
        keyboard = [
            [InlineKeyboardButton("🏄‍♂️ SUP", callback_data="tipo_SUP")],
            [InlineKeyboardButton("🚣‍♂️ KAYAK", callback_data="tipo_KAYAK")],
            [InlineKeyboardButton("🏖️ LETTINO", callback_data="tipo_LETTINO")],
            [InlineKeyboardButton("📱 PHONEBAG", callback_data="tipo_PHONEBAG")],
            [InlineKeyboardButton("🎒 DRYBAG", callback_data="tipo_DRYBAG")]
        ]
        
        await query.edit_message_text(
            f"✅ Associato: {associato}\n\nTipo noleggio?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TIPO_NOLEGGIO
    
    # Tipo noleggio
    elif data.startswith("tipo_"):
        tipo = data.replace("tipo_", "")
        context.user_data['tipo_noleggio'] = tipo
        
        if tipo == 'SUP':
            keyboard = [
                [InlineKeyboardButton("All-around", callback_data="sup_All-around")],
                [InlineKeyboardButton("Touring", callback_data="sup_Touring")],
                [InlineKeyboardButton("Race", callback_data="sup_Race")],
                [InlineKeyboardButton("Surf", callback_data="sup_Surf")],
                [InlineKeyboardButton("Yoga", callback_data="sup_Yoga")]
            ]
            await query.edit_message_text(
                f"✅ {tipo}\n\nTipo SUP:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DETTAGLI_SUP
            
        elif tipo == 'LETTINO':
            keyboard = [
                [InlineKeyboardButton("🌲 Pineta", callback_data="lettino_Pineta")],
                [InlineKeyboardButton("🚤 Squero", callback_data="lettino_Squero")]
            ]
            await query.edit_message_text(
                f"✅ {tipo}\n\nTipo lettino:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DETTAGLI_LETTINO
            
        elif tipo in ['PHONEBAG', 'DRYBAG']:
            await query.edit_message_text(f"✅ {tipo}\n\nInserisci numero (0-99):")
            return LETTINO_NUMERO
            
        else:  # KAYAK
            context.user_data['dettagli'] = 'Standard'
            return await show_tempo_buttons(query, context)
    
    # Dettagli SUP
    elif data.startswith("sup_"):
        dettagli = data.replace("sup_", "")
        context.user_data['dettagli'] = dettagli
        return await show_tempo_buttons(query, context)
    
    # Dettagli lettino
    elif data.startswith("lettino_"):
        dettagli = data.replace("lettino_", "")
        context.user_data['dettagli'] = dettagli
        
        associato = context.user_data['associato']
        testo = "Inserisci LETTERA (A-Z):" if associato == 'SÌ' else "Inserisci NUMERO (0-99):"
        await query.edit_message_text(f"✅ {dettagli}\n\n{testo}")
        return LETTINO_NUMERO
    
    # Tempo
    elif data.startswith("tempo_"):
        tempo = data.replace("tempo_", "")
        context.user_data['tempo'] = tempo
        
        keyboard = [
            [InlineKeyboardButton("💳 CARTA", callback_data="pag_CARD")],
            [InlineKeyboardButton("🏦 BONIFICO", callback_data="pag_BONIFICO")]
        ]
        
        await query.edit_message_text(
            f"✅ Tempo: {tempo}\n\nTipo PAGAMENTO:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PAGAMENTO
    
    # Pagamento
    elif data.startswith("pag_"):
        pagamento = data.replace("pag_", "")
        context.user_data['pagamento'] = pagamento
        
        await query.edit_message_text(
            f"✅ Pagamento: {pagamento}\n\nInserisci IMPORTO (es: 25, 30.50):"
        )
        return IMPORTO
    
    # Foto ricevuta
    elif data.startswith("foto_"):
        if data == "foto_SI":
            await query.edit_message_text("📸 Invia foto ricevuta:")
            context.user_data['attende_foto'] = True
            return FOTO_RICEVUTA
        else:
            context.user_data['foto_ricevuta'] = None
            await query.edit_message_text("✅ Nessuna foto\n\nAggiungi NOTE? (o 'skip'):")
            return NOTE
    
    return ConversationHandler.END

async def show_tempo_buttons(query, context):
    """Mostra opzioni tempo - CON MEZZ'ORE"""
    keyboard = [
        [InlineKeyboardButton("⏱️ 1h", callback_data="tempo_1h")],
        [InlineKeyboardButton("⏱️ 1,5h", callback_data="tempo_1,5h")],
        [InlineKeyboardButton("⏱️ 2h", callback_data="tempo_2h")],
        [InlineKeyboardButton("⏱️ 2,5h", callback_data="tempo_2,5h")],
        [InlineKeyboardButton("⏱️ 3h", callback_data="tempo_3h")],
        [InlineKeyboardButton("⏱️ 3,5h", callback_data="tempo_3,5h")],
        [InlineKeyboardButton("⏱️ 4h", callback_data="tempo_4h")],
        [InlineKeyboardButton("⏱️ 4,5h", callback_data="tempo_4,5h")],
        [InlineKeyboardButton("⏱️ 5h", callback_data="tempo_5h")],
        [InlineKeyboardButton("⏱️ 6h", callback_data="tempo_6h")],
        [InlineKeyboardButton("⏱️ 8h", callback_data="tempo_8h")]
    ]
    
    dettagli = context.user_data.get('dettagli', 'Standard')
    
    try:
        await query.edit_message_text(
            f"✅ {dettagli}\n\nTempo noleggio:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await query.message.reply_text(
            f"✅ {dettagli}\n\nTempo noleggio:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return TEMPO

async def get_lettino_numero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve numero/lettera per lettini e numeri per phonebag/drybag"""
    numero_text = update.message.text.upper()
    tipo = context.user_data['tipo_noleggio']
    
    # Validazione semplificata
    if tipo == 'LETTINO':
        associato = context.user_data['associato']
        if associato == 'SÌ':
            if not (len(numero_text) == 1 and 'A' <= numero_text <= 'Z'):
                await update.message.reply_text("❌ Inserisci lettera A-Z:")
                return LETTINO_NUMERO
        else:
            try:
                num = int(numero_text)
                if not (0 <= num <= 99):
                    raise ValueError
            except ValueError:
                await update.message.reply_text("❌ Inserisci numero 0-99:")
                return LETTINO_NUMERO
    
    context.user_data['numero'] = numero_text
    
    # Simula callback per tempo
    from types import SimpleNamespace
    fake_query = SimpleNamespace()
    fake_query.edit_message_text = lambda text, reply_markup=None: update.message.reply_text(text, reply_markup=reply_markup)
    fake_query.message = update.message
    
    return await show_tempo_buttons(fake_query, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gestisce foto ricevuta"""
    if not context.user_data.get('attende_foto', False):
        return FOTO_RICEVUTA
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome = context.user_data.get('nome', 'unknown')
        cognome = context.user_data.get('cognome', 'unknown')
        filename = f"{timestamp}_{cognome}_{nome}_ricevuta.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)
        
        await file.download_to_drive(filepath)
        context.user_data['foto_ricevuta'] = filename
        
        await update.message.reply_text("✅ Foto salvata!\n\nAggiungi NOTE? (o 'skip'):")
        return NOTE
        
    except Exception as e:
        logger.error(f"Errore foto: {e}")
        await update.message.reply_text("⚠️ Errore foto\n\nAggiungi NOTE? (o 'skip'):")
        context.user_data['foto_ricevuta'] = None
        return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve note e salva"""
    note_text = update.message.text.strip()
    
    if note_text.lower() == 'skip':
        context.user_data['note'] = None
    else:
        context.user_data['note'] = note_text
    
    return await salva_registrazione(update, context)

async def salva_registrazione(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva registrazione e chiede se aggiungere altro noleggio"""
    try:
        registrazione = {
            'data': context.user_data['data'],
            'cognome': context.user_data['cognome'],
            'nome': context.user_data['nome'],
            'documento': context.user_data['documento'],
            'numero_documento': context.user_data['numero_documento'],
            'telefono': context.user_data['telefono'],
            'associato': context.user_data['associato'],
            'tipo_noleggio': context.user_data['tipo_noleggio'],
            'dettagli': context.user_data.get('dettagli', ''),
            'numero': context.user_data.get('numero', ''),
            'tempo': context.user_data['tempo'],
            'pagamento': context.user_data['pagamento'],
            'importo': context.user_data.get('importo', ''),
            'foto_ricevuta': context.user_data.get('foto_ricevuta'),
            'note': context.user_data.get('note'),
            'timestamp': datetime.now().isoformat()
        }
        
        bot_instance.noleggi.append(registrazione)
        bot_instance.save_data()
        
        # Salva i dati cliente per eventuali noleggi aggiuntivi
        if 'cliente_base' not in context.user_data:
            context.user_data['cliente_base'] = {
                'data': context.user_data['data'],
                'cognome': context.user_data['cognome'],
                'nome': context.user_data['nome'],
                'documento': context.user_data['documento'],
                'numero_documento': context.user_data['numero_documento'],
                'telefono': context.user_data['telefono'],
                'associato': context.user_data['associato']
            }
        
        messaggio = f"""
✅ **NOLEGGIO REGISTRATO!**

👤 {registrazione['cognome']} {registrazione['nome']}
🏄‍♂️ {registrazione['tipo_noleggio']} {registrazione['dettagli']}
🔢 N. {registrazione['numero']}
⏱️ {registrazione['tempo']}
💰 {registrazione['importo']}
        """
        
        # Pulsanti per aggiungere altro o finire
        keyboard = [
            [InlineKeyboardButton("➕ Aggiungi altro noleggio", callback_data="altro_noleggio")],
            [InlineKeyboardButton("✅ Finito", callback_data="finito")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(messaggio + "\n\n🤔 Vuole noleggiare altro?", reply_markup=reply_markup)
        
        return TIPO_NOLEGGIO  # Resta nello stato per gestire altri noleggi
        
    except Exception as e:
        logger.error(f"Errore salvataggio: {e}")
        await update.message.reply_text("❌ Errore salvataggio")
        context.user_data.clear()
        return ConversationHandler.END

async def mostra_noleggi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra SOLO i noleggi di oggi raggruppati per cliente"""
    noleggi_oggi = bot_instance.get_noleggi_oggi()
    
    if not noleggi_oggi:
        oggi = datetime.now().strftime('%d/%m/%Y')
        await update.message.reply_text(f"📅 **Nessun noleggio per oggi ({oggi})**")
        return
    
    # Raggruppa per cliente
    clienti_noleggi = defaultdict(list)
    for noleggio in noleggi_oggi:
        nome_completo = f"{noleggio.get('cognome', '')} {noleggio.get('nome', '')}"
        clienti_noleggi[nome_completo].append(noleggio)
    
    # Crea pulsanti inline per ogni cliente
    keyboard = []
    cliente_index = 0
    
    for nome_cliente, noleggi_cliente in clienti_noleggi.items():
        # Crea stringa con tutti i noleggi del cliente
        noleggi_str = ""
        ha_foto = False
        
        for noleggio in noleggi_cliente:
            tipo_icon = {"SUP": "🏄‍♂️", "KAYAK": "🚣‍♂️", "LETTINO": "🏖️", "PHONEBAG": "📱", "DRYBAG": "🎒"}.get(noleggio['tipo_noleggio'], "📦")
            noleggi_str += f"{tipo_icon}"
            if noleggio.get('foto_ricevuta'):
                ha_foto = True
        
        # Aggiungi icona foto se almeno un noleggio ha foto
        foto_icon = " 📸" if ha_foto else ""
        
        button_text = f"{noleggi_str} {nome_cliente} ({len(noleggi_cliente)}){foto_icon}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cliente_{cliente_index}")])
        cliente_index += 1
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    oggi = datetime.now().strftime('%d/%m/%Y')
    totale_clienti = len(clienti_noleggi)
    totale_noleggi = len(noleggi_oggi)
    
    await update.message.reply_text(
        f"📅 **NOLEGGI DI OGGI ({oggi})**\n"
        f"👥 Clienti: {totale_clienti} | 🏄‍♂️ Noleggi: {totale_noleggi}\n\n"
        f"📸 = con foto ricevuta\n"
        f"(n) = numero noleggi\n"
        f"Clicca su un cliente per i dettagli:",
        reply_markup=reply_markup
    )

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export CSV semplificato"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun dato da esportare")
        return
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"noleggi_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Data', 'Cognome', 'Nome', 'Telefono', 'Tipo_Noleggio', 'Tempo', 'Importo']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for registro in bot_instance.noleggi:
                writer.writerow({
                    'Data': registro['data'],
                    'Cognome': registro.get('cognome', ''),
                    'Nome': registro.get('nome', ''),
                    'Telefono': registro['telefono'],
                    'Tipo_Noleggio': registro['tipo_noleggio'],
                    'Tempo': registro['tempo'],
                    'Importo': registro.get('importo', '')
                })
        
        with open(csv_filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=csv_filename,
                caption=f"📊 {len(bot_instance.noleggi)} registrazioni"
            )
        
        os.remove(csv_filename)
        
    except Exception as e:
        logger.error(f"Errore export: {e}")
        await update.message.reply_text("❌ Errore export")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancella operazione"""
    await update.message.reply_text("❌ Annullato", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help semplificato"""
    help_text = """
🏄‍♂️ **BOT NOLEGGIO SUP v.2.5**

/nuovo - Nuova registrazione noleggio
/mostra_noleggi - Clienti di oggi (raggruppati)
/export - Esporta tutti i dati CSV
/help - Questa guida
/cancel - Annulla operazione

**🔄 NOLEGGI MULTIPLI:**
• Dopo ogni noleggio puoi aggiungerne altri
• Stesso cliente = dati già compilati
• Esempio: SUP + 2 PHONEBAG + LETTINO

**📅 VISTA GIORNALIERA:**
• `/mostra_noleggi` raggruppa per cliente
• Mostra tutti i noleggi per persona
• 📸 indica clienti con foto ricevute
• (n) = numero di noleggi del cliente

**⚠️ Usa sempre i PULSANTI durante la registrazione!**

👨‍💻 Dino Bronzi - 26/07/2025
    """
    await update.message.reply_text(help_text)

def main():
    """Avvia il bot"""
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Token mancante!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Conversation handler principale
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nuovo", start)],
        states={
            DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_data)],
            COGNOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cognome)],
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nome)],
            DOCUMENTO: [CallbackQueryHandler(handle_callback)],
            NUMERO_DOCUMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_numero_documento)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_telefono)],
            ASSOCIATO: [CallbackQueryHandler(handle_callback)],
            TIPO_NOLEGGIO: [CallbackQueryHandler(handle_callback)],
            DETTAGLI_SUP: [CallbackQueryHandler(handle_callback)],
            DETTAGLI_LETTINO: [CallbackQueryHandler(handle_callback)],
            LETTINO_NUMERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lettino_numero)],
            TEMPO: [CallbackQueryHandler(handle_callback)],
            PAGAMENTO: [CallbackQueryHandler(handle_callback)],
            IMPORTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_importo)],
            FOTO_RICEVUTA: [
                CallbackQueryHandler(handle_callback),
                MessageHandler(filters.PHOTO, handle_photo)
            ],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Aggiungi handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler(["start", "help"], help_command))
    application.add_handler(CommandHandler("mostra_noleggi", mostra_noleggi))
    application.add_handler(CommandHandler("export", export_csv))
    
    # Handler per i callback di mostra_noleggi (fuori dalla conversazione)
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(cliente_|foto_)"))
    
    print("🏄‍♂️ Bot SUP v.2.4 avviato!")
    print("📅 /mostra_noleggi - Vedi clienti di oggi")
    print("📸 Foto ricevute visualizzabili nei dettagli clienti")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
