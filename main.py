#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram per Noleggio SUP
Autore: Dino Bronzi
Data creazione: 26 Luglio 2025
Versione: 2.0 - BASTA PERDERE TEMPO! Layout semplice che FUNZIONA
"""

import os
import csv
import json
import logging
from datetime import datetime
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from typing import Dict, Any

# Configura il logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Stati della conversazione
(DATA, COGNOME, NOME, DOCUMENTO, NUMERO_DOCUMENTO, TELEFONO, ASSOCIATO, TIPO_NOLEGGIO, 
 DETTAGLI_SUP, DETTAGLI_LETTINO, LETTINO_NUMERO, TEMPO, PAGAMENTO, FOTO_RICEVUTA) = range(14)

# File per salvare i dati e le foto
DATA_FILE = 'noleggi.json'
PHOTOS_DIR = 'ricevute_photos'

# Crea la directory per le foto se non esiste
os.makedirs(PHOTOS_DIR, exist_ok=True)

class SupRentalBot:
    def __init__(self):
        self.noleggi = self.load_data()
    
    def load_data(self):
        """Carica i dati esistenti dal file JSON"""
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("File dati non trovato, creo nuovo database")
            return []
        except json.JSONDecodeError:
            logger.error("Errore nel file JSON, creo nuovo database")
            return []
        except Exception as e:
            logger.error(f"Errore caricamento dati: {e}")
            return []
    
    def save_data(self):
        """Salva i dati nel file JSON"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.noleggi, f, ensure_ascii=False, indent=2)
            logger.info("Dati salvati correttamente")
        except Exception as e:
            logger.error(f"Errore salvataggio dati: {e}")
            raise

# Istanza globale del bot
bot_instance = SupRentalBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Avvia la conversazione di registrazione"""
    await update.message.reply_text(
        "🏄‍♂️ **Benvenuto nel sistema di noleggio SUP!**\n\n"
        "Iniziamo la registrazione del noleggio.\n"
        "Per prima cosa, inserisci la **data** (formato: DD/MM/YYYY):"
    )
    return DATA

async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la data e chiede il cognome"""
    try:
        data_text = update.message.text
        # Valida il formato della data
        datetime.strptime(data_text, '%d/%m/%Y')
        context.user_data['data'] = data_text
        
        await update.message.reply_text("Perfetto! Ora inserisci il COGNOME:")
        return COGNOME
    except ValueError:
        await update.message.reply_text(
            "❌ Formato data non valido. Usa il formato DD/MM/YYYY (es: 25/12/2024):"
        )
        return DATA

async def get_cognome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il cognome e chiede il nome"""
    context.user_data['cognome'] = update.message.text
    await update.message.reply_text("Ottimo! Ora inserisci il NOME:")
    return NOME

async def get_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il nome e chiede il tipo di documento"""
    context.user_data['nome'] = update.message.text
    
    # Inline buttons per il documento
    keyboard = [
        [InlineKeyboardButton("C.I.", callback_data="doc_CI")],
        [InlineKeyboardButton("PAT", callback_data="doc_PAT")],
        [InlineKeyboardButton("PASS", callback_data="doc_PASS")],
        [InlineKeyboardButton("ALTRO", callback_data="doc_ALTRO")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Seleziona il tipo di DOCUMENTO:",
        reply_markup=reply_markup
    )
    return DOCUMENTO

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gestisce tutti i callback dei pulsanti inline"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    data = query.data
    
    # Documento
    if data.startswith("doc_"):
        documento = data.replace("doc_", "").replace("_", ".")
        context.user_data['documento'] = documento
        
        await query.edit_message_text(
            f"✅ Documento selezionato: {documento}\n\n"
            f"Inserisci il NUMERO del documento {documento}:"
        )
        return NUMERO_DOCUMENTO
    
    # Associato
    elif data.startswith("assoc_"):
        associato = "SÌ" if data == "assoc_SI" else "NO"
        context.user_data['associato'] = associato
        
        # Inline buttons per tipo noleggio
        keyboard = [
            [InlineKeyboardButton("🏄‍♂️ SUP", callback_data="tipo_SUP")],
            [InlineKeyboardButton("🚣‍♂️ KAYAK", callback_data="tipo_KAYAK")],
            [InlineKeyboardButton("🏖️ LETTINO", callback_data="tipo_LETTINO")],
            [InlineKeyboardButton("📱 PHONEBAG", callback_data="tipo_PHONEBAG")],
            [InlineKeyboardButton("🎒 DRYBAG", callback_data="tipo_DRYBAG")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Associato: {associato}\n\n"
            "Cosa viene noleggiato?",
            reply_markup=reply_markup
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
                [InlineKeyboardButton("Yoga", callback_data="sup_Yoga")],
                [InlineKeyboardButton("Whitewater", callback_data="sup_Whitewater")],
                [InlineKeyboardButton("Windsurf", callback_data="sup_Windsurf")],
                [InlineKeyboardButton("Foil", callback_data="sup_Foil")],
                [InlineKeyboardButton("Multi", callback_data="sup_Multi")],
                [InlineKeyboardButton("Fishing", callback_data="sup_Fishing")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Tipo noleggio: {tipo}\n\n"
                "Seleziona il tipo di SUP:",
                reply_markup=reply_markup
            )
            return DETTAGLI_SUP
            
        elif tipo == 'LETTINO':
            keyboard = [
                [InlineKeyboardButton("🌲 Pineta", callback_data="lettino_Pineta")],
                [InlineKeyboardButton("🚤 Squero", callback_data="lettino_Squero")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Tipo noleggio: {tipo}\n\n"
                "Seleziona il tipo di LETTINO:",
                reply_markup=reply_markup
            )
            return DETTAGLI_LETTINO
            
        elif tipo in ['PHONEBAG', 'DRYBAG']:
            await query.edit_message_text(
                f"✅ Tipo noleggio: {tipo}\n\n"
                f"Inserisci il numero del {tipo} (0-99):"
            )
            return LETTINO_NUMERO
            
        else:  # KAYAK
            context.user_data['dettagli'] = 'Standard'
            return await show_tempo_buttons(query, context)
    
    # SUP dettagli
    elif data.startswith("sup_"):
        dettagli = data.replace("sup_", "")
        context.user_data['dettagli'] = dettagli
        return await show_tempo_buttons(query, context)
    
    # Lettino dettagli
    elif data.startswith("lettino_"):
        dettagli = data.replace("lettino_", "")
        context.user_data['dettagli'] = dettagli
        
        associato = context.user_data['associato']
        if associato == 'SÌ':
            await query.edit_message_text(
                f"✅ Lettino: {dettagli}\n\n"
                "Inserisci la LETTERA del lettino (A-Z):"
            )
        else:
            await query.edit_message_text(
                f"✅ Lettino: {dettagli}\n\n"
                "Inserisci il NUMERO del lettino (0-99):"
            )
        return LETTINO_NUMERO
    
    # Tempo
    elif data.startswith("tempo_"):
        tempo = data.replace("tempo_", "")
        context.user_data['tempo'] = tempo
        
        keyboard = [
            [InlineKeyboardButton("💳 CARTA", callback_data="pag_CARD")],
            [InlineKeyboardButton("🏦 BONIFICO", callback_data="pag_BONIFICO")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                f"✅ Tempo: {tempo}\n\n"
                "💰 Seleziona il tipo di PAGAMENTO:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Errore pagamento buttons: {e}")
            await query.message.reply_text(
                f"✅ Tempo: {tempo}\n\n"
                "💰 Seleziona il tipo di PAGAMENTO:",
                reply_markup=reply_markup
            )
        return PAGAMENTO
    
    # Pagamento
    elif data.startswith("pag_"):
        pagamento = data.replace("pag_", "")
        context.user_data['pagamento'] = pagamento
        
        keyboard = [
            [InlineKeyboardButton("📸 SÌ - Allego foto", callback_data="foto_SI")],
            [InlineKeyboardButton("❌ NO - Nessuna foto", callback_data="foto_NO")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                f"✅ Pagamento: {pagamento}\n\n"
                "📷 Vuoi allegare la foto della ricevuta?",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Errore foto buttons: {e}")
            await query.message.reply_text(
                f"✅ Pagamento: {pagamento}\n\n"
                "📷 Vuoi allegare la foto della ricevuta?",
                reply_markup=reply_markup
            )
        return FOTO_RICEVUTA
    
    # Foto ricevuta
    elif data.startswith("foto_"):
        if data == "foto_SI":
            await query.edit_message_text(
                "📸 Invia la foto della ricevuta:"
            )
            context.user_data['attende_foto'] = True
            return FOTO_RICEVUTA
        else:
            context.user_data['foto_ricevuta'] = None
            await query.edit_message_text("✅ Nessuna foto allegata.")
            return await salva_registrazione_callback(query, context)
    
    return ConversationHandler.END

async def show_tempo_buttons(query, context):
    """Mostra i pulsanti tempo - LAYOUT SEMPLICE CHE FUNZIONA (1-8h + mezz'ore)"""
    # Layout UNA COLONNA - funziona sempre su mobile e web
    keyboard = [
        [InlineKeyboardButton("⏱️ 1 ora", callback_data="tempo_1h")],
        [InlineKeyboardButton("⏱️ 1,5 ore", callback_data="tempo_1,5h")],
        [InlineKeyboardButton("⏱️ 2 ore", callback_data="tempo_2h")],
        [InlineKeyboardButton("⏱️ 2,5 ore", callback_data="tempo_2,5h")],
        [InlineKeyboardButton("⏱️ 3 ore", callback_data="tempo_3h")],
        [InlineKeyboardButton("⏱️ 3,5 ore", callback_data="tempo_3,5h")],
        [InlineKeyboardButton("⏱️ 4 ore", callback_data="tempo_4h")],
        [InlineKeyboardButton("⏱️ 4,5 ore", callback_data="tempo_4,5h")],
        [InlineKeyboardButton("⏱️ 5 ore", callback_data="tempo_5h")],
        [InlineKeyboardButton("⏱️ 5,5 ore", callback_data="tempo_5,5h")],
        [InlineKeyboardButton("⏱️ 6 ore", callback_data="tempo_6h")],
        [InlineKeyboardButton("⏱️ 6,5 ore", callback_data="tempo_6,5h")],
        [InlineKeyboardButton("⏱️ 7 ore", callback_data="tempo_7h")],
        [InlineKeyboardButton("⏱️ 7,5 ore", callback_data="tempo_7,5h")],
        [InlineKeyboardButton("⏱️ 8 ore", callback_data="tempo_8h")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    dettagli = context.user_data.get('dettagli', 'Standard')
    
    try:
        await query.edit_message_text(
            f"✅ {dettagli}\n\n"
            "🕐 Seleziona il tempo di noleggio:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Errore tempo buttons: {e}")
        # Se edit fallisce, manda nuovo messaggio
        await query.message.reply_text(
            f"✅ {dettagli}\n\n"
            "🕐 Seleziona il tempo di noleggio:",
            reply_markup=reply_markup
        )
    
    return TEMPO
    """Riceve il tipo di documento e chiede il numero"""
    documento = update.message.text
    if documento not in ['C.I.', 'PAT', 'PASS', 'ALTRO']:
        await update.message.reply_text(
            "❌ Seleziona un'opzione valida:",
            reply_markup=ReplyKeyboardMarkup([['C.I.', 'PAT'], ['PASS', 'ALTRO']], 
                                           one_time_keyboard=True, resize_keyboard=True)
        )
        return DOCUMENTO
    
    context.user_data['documento'] = documento
    await update.message.reply_text(
        f"Inserisci il NUMERO del documento {documento}:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NUMERO_DOCUMENTO

async def get_numero_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il numero di documento e chiede il telefono"""
    numero_doc = update.message.text.strip()
    if len(numero_doc) < 3:
        await update.message.reply_text(
            "❌ Il numero del documento deve essere di almeno 3 caratteri:"
        )
        return NUMERO_DOCUMENTO
    
    context.user_data['numero_documento'] = numero_doc
    await update.message.reply_text("Inserisci il numero di TELEFONO:")
    return TELEFONO

async def get_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il telefono e chiede se è associato"""
    context.user_data['telefono'] = update.message.text
    
    # Inline buttons per associato
    keyboard = [
        [InlineKeyboardButton("✅ SÌ", callback_data="assoc_SI")],
        [InlineKeyboardButton("❌ NO", callback_data="assoc_NO")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "La persona è un ASSOCIATO?",
        reply_markup=reply_markup
    )
    return ASSOCIATO

async def salva_registrazione_callback(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva la registrazione quando viene da callback"""
    try:
        # Prepara i dati per il salvataggio
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
            'foto_ricevuta': context.user_data.get('foto_ricevuta'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Salva nel database
        bot_instance.noleggi.append(registrazione)
        bot_instance.save_data()
        
        # Messaggio di conferma
        messaggio = f"""
✅ **REGISTRAZIONE COMPLETATA! (v.1.9)**

📅 Data: {registrazione['data']}
👤 Cliente: {registrazione['cognome']} {registrazione['nome']}
📄 Documento: {registrazione['documento']} - {registrazione['numero_documento']}
📞 Telefono: {registrazione['telefono']}
🏅 Associato: {registrazione['associato']}
🏄‍♂️ Noleggio: {registrazione['tipo_noleggio']}
📝 Dettagli: {registrazione['dettagli']}
🔢 Numero: {registrazione['numero']}
⏱️ Tempo: {registrazione['tempo']}
💳 Pagamento: {registrazione['pagamento']}
📸 Foto ricevuta: {'✅ Presente' if registrazione['foto_ricevuta'] else '❌ Non allegata'}

💡 **Comandi utili:**
• /start - Nuova registrazione
• /cerca {registrazione['cognome']} - Trova questo cliente
• /mostra_clienti - Vedi tutti i clienti
• /export - Esporta dati CSV
        """
        
        await query.message.reply_text(messaggio)
        
        # Pulisce i dati utente
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Errore nel salvataggio: {e}")
        await query.message.reply_text(
            "❌ Errore nel salvataggio dei dati. Riprova più tardi."
        )
        context.user_data.clear()
        return ConversationHandler.END
    """Riceve lo status associato e chiede il tipo di noleggio"""
    associato = update.message.text
    if associato not in ['SÌ', 'NO']:
        keyboard = [['SÌ', 'NO']]
        await update.message.reply_text(
            "❌ Seleziona SÌ o NO con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASSOCIATO
    
    context.user_data['associato'] = associato
    
    keyboard = [['SUP', 'KAYAK'], ['LETTINO'], ['PHONEBAG', 'DRYBAG']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Cosa viene noleggiato?",
        reply_markup=reply_markup
    )
    return TIPO_NOLEGGIO

async def get_tipo_noleggio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gestisce il tipo di noleggio"""
    tipo = update.message.text
    if tipo not in ['SUP', 'KAYAK', 'LETTINO', 'PHONEBAG', 'DRYBAG']:
        keyboard = [['SUP', 'KAYAK'], ['LETTINO'], ['PHONEBAG', 'DRYBAG']]
        await update.message.reply_text(
            "❌ Seleziona un'opzione valida con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return TIPO_NOLEGGIO
    
    context.user_data['tipo_noleggio'] = tipo
    
    if tipo == 'SUP':
        keyboard = [
            ['All-around', 'Touring'],
            ['Race', 'Surf'],
            ['Yoga', 'Whitewater'],
            ['Windsurf', 'Foil'],
            ['Multi', 'Fishing']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Seleziona il tipo di SUP:",
            reply_markup=reply_markup
        )
        return DETTAGLI_SUP
    
    elif tipo == 'LETTINO':
        keyboard = [['Pineta', 'Squero']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Seleziona il tipo di LETTINO:",
            reply_markup=reply_markup
        )
        return DETTAGLI_LETTINO
    
    elif tipo in ['PHONEBAG', 'DRYBAG']:
        await update.message.reply_text(
            f"Inserisci il numero del {tipo} (0-99):",
            reply_markup=ReplyKeyboardRemove()
        )
        return LETTINO_NUMERO
    
    else:  # KAYAK
        context.user_data['dettagli'] = 'Standard'
        return await get_tempo(update, context)

async def get_dettagli_sup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve i dettagli del SUP"""
    dettagli = update.message.text
    opzioni_sup = ['All-around', 'Touring', 'Race', 'Surf', 'Yoga', 'Whitewater', 
                   'Windsurf', 'Foil', 'Multi', 'Fishing']
    
    if dettagli not in opzioni_sup:
        keyboard = [
            ['All-around', 'Touring'],
            ['Race', 'Surf'],
            ['Yoga', 'Whitewater'],
            ['Windsurf', 'Foil'],
            ['Multi', 'Fishing']
        ]
        await update.message.reply_text(
            "❌ Seleziona un'opzione valida con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return DETTAGLI_SUP
    
    context.user_data['dettagli'] = dettagli
    return await get_tempo(update, context)

async def get_dettagli_lettino(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve i dettagli del lettino"""
    dettagli = update.message.text
    if dettagli not in ['Pineta', 'Squero']:
        keyboard = [['Pineta', 'Squero']]
        await update.message.reply_text(
            "❌ Seleziona Pineta o Squero con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return DETTAGLI_LETTINO
    
    context.user_data['dettagli'] = dettagli
    
    # Chiede il numero/lettera del lettino
    associato = context.user_data['associato']
    if associato == 'SÌ':
        await update.message.reply_text(
            "Inserisci la LETTERA del lettino (A-Z):",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Inserisci il NUMERO del lettino (0-99):",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return LETTINO_NUMERO

async def get_lettino_numero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il numero/lettera del lettino o numero di phonebag/drybag"""
    numero_text = update.message.text.upper()
    tipo = context.user_data['tipo_noleggio']
    
    if tipo == 'LETTINO':
        associato = context.user_data['associato']
        if associato == 'SÌ':
            # Verifica che sia una lettera A-Z
            if len(numero_text) != 1 or not numero_text.isalpha() or numero_text < 'A' or numero_text > 'Z':
                await update.message.reply_text(
                    "❌ Inserisci una lettera valida (A-Z):"
                )
                return LETTINO_NUMERO
        else:
            # Verifica che sia un numero 0-99
            try:
                numero = int(numero_text)
                if numero < 0 or numero > 99:
                    raise ValueError
            except ValueError:
                await update.message.reply_text(
                    "❌ Inserisci un numero valido (0-99):"
                )
                return LETTINO_NUMERO
    
    elif tipo in ['PHONEBAG', 'DRYBAG']:
        # Verifica che sia un numero 0-99
        try:
            numero = int(numero_text)
            if numero < 0 or numero > 99:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                f"❌ Inserisci un numero valido per {tipo} (0-99):"
            )
            return LETTINO_NUMERO
    
    context.user_data['numero'] = numero_text
    return await get_tempo(update, context)

async def get_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Chiede il tempo di noleggio"""
    # Crea tastiera con opzioni di tempo (più compatta)
    keyboard = [
        ['1h', '1,5h', '2h', '2,5h'],
        ['3h', '3,5h', '4h', '4,5h'],
        ['5h', '5,5h', '6h', '6,5h'],
        ['7h', '7,5h', '8h', '8,5h'],
        ['9h', '9,5h', '10h', '10,5h'],
        ['11h', '11,5h', '12h']
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Seleziona il tempo di noleggio:",
        reply_markup=reply_markup
    )
    return TEMPO

async def get_tempo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il tempo di noleggio"""
    tempo_text = update.message.text
    
    # Lista completa di tempi validi
    tempi_validi = []
    for h in range(1, 13):
        tempi_validi.append(f"{h}h")
        if h < 12:
            tempi_validi.append(f"{h},5h")
    
    if tempo_text not in tempi_validi:
        # Ricrea la tastiera se l'input non è valido
        keyboard = [
            ['1h', '1,5h', '2h', '2,5h'],
            ['3h', '3,5h', '4h', '4,5h'],
            ['5h', '5,5h', '6h', '6,5h'],
            ['7h', '7,5h', '8h', '8,5h'],
            ['9h', '9,5h', '10h', '10,5h'],
            ['11h', '11,5h', '12h']
        ]
        
        await update.message.reply_text(
            "❌ Seleziona un tempo valido con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return TEMPO
    
    context.user_data['tempo'] = tempo_text
    
    keyboard = [['CARD', 'BONIFICO']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Seleziona il tipo di PAGAMENTO:",
        reply_markup=reply_markup
    )
    return PAGAMENTO

async def get_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il tipo di pagamento"""
    pagamento = update.message.text
    if pagamento not in ['CARD', 'BONIFICO']:
        keyboard = [['CARD', 'BONIFICO']]
        await update.message.reply_text(
            "❌ Seleziona CARD o BONIFICO con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PAGAMENTO
    
    context.user_data['pagamento'] = pagamento
    
    keyboard = [['SÌ', 'NO']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Vuoi allegare la foto della ricevuta?",
        reply_markup=reply_markup
    )
    return FOTO_RICEVUTA

async def get_foto_ricevuta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gestisce la foto della ricevuta"""
    risposta = update.message.text
    
    if risposta not in ['SÌ', 'NO']:
        keyboard = [['SÌ', 'NO']]
        await update.message.reply_text(
            "❌ Seleziona SÌ o NO con i pulsanti:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return FOTO_RICEVUTA
    
    if risposta == 'SÌ':
        await update.message.reply_text(
            "📸 Invia la foto della ricevuta:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['attende_foto'] = True
        return FOTO_RICEVUTA
    else:
        context.user_data['foto_ricevuta'] = None
        return await salva_registrazione(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce tutti gli errori del bot"""
    logger.error(f"Errore causato da update {update}: {context.error}")
    
    # Se c'è un update, prova a rispondere all'utente
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Si è verificato un errore. Riprova tra qualche secondo.\n"
                "Se il problema persiste, usa /cancel e riprova con /start."
            )
        except Exception:
            # Se non riesce nemmeno a mandare il messaggio, logga e basta
            logger.error("Impossibile inviare messaggio di errore all'utente")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gestisce la ricezione della foto"""
    if not context.user_data.get('attende_foto', False):
        return FOTO_RICEVUTA
    
    try:
        # Salva la foto
        photo = update.message.photo[-1]  # Prende la foto con qualità più alta
        file = await context.bot.get_file(photo.file_id)
        
        # Crea nome file con timestamp e dati cliente
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome = context.user_data.get('nome', 'unknown')
        cognome = context.user_data.get('cognome', 'unknown')
        filename = f"{timestamp}_{nome}_{cognome}_ricevuta.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)
        
        await file.download_to_drive(filepath)
        context.user_data['foto_ricevuta'] = filename
        
        await update.message.reply_text("✅ Foto ricevuta salvata!")
        return await salva_registrazione(update, context)
        
    except Exception as e:
        logger.error(f"Errore salvataggio foto: {e}")
        await update.message.reply_text("⚠️ Errore nel salvataggio della foto, procedo senza foto.")
        context.user_data['foto_ricevuta'] = None
        return await salva_registrazione(update, context)

async def salva_registrazione(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva la registrazione completa"""
    try:
        # Prepara i dati per il salvataggio
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
            'foto_ricevuta': context.user_data.get('foto_ricevuta'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Salva nel database
        bot_instance.noleggi.append(registrazione)
        bot_instance.save_data()
        
        # Messaggio di conferma
        messaggio = f"""
✅ **REGISTRAZIONE COMPLETATA! (v.1.4)**

📅 Data: {registrazione['data']}
👤 Cliente: {registrazione['cognome']} {registrazione['nome']}
📄 Documento: {registrazione['documento']} - {registrazione['numero_documento']}
📞 Telefono: {registrazione['telefono']}
🏅 Associato: {registrazione['associato']}
🏄‍♂️ Noleggio: {registrazione['tipo_noleggio']}
📝 Dettagli: {registrazione['dettagli']}
🔢 Numero: {registrazione['numero']}
⏱️ Tempo: {registrazione['tempo']}
💳 Pagamento: {registrazione['pagamento']}
📸 Foto ricevuta: {'✅ Presente' if registrazione['foto_ricevuta'] else '❌ Non allegata'}

💡 **Comandi utili:**
• /start - Nuova registrazione
• /cerca {registrazione['cognome']} - Trova questo cliente
• /mostra_clienti - Vedi tutti i clienti
• /export - Esporta dati CSV
        """
        
        await update.message.reply_text(messaggio, reply_markup=ReplyKeyboardRemove())
        
        # Pulisce i dati utente
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Errore nel salvataggio: {e}")
        await update.message.reply_text(
            "❌ Errore nel salvataggio dei dati. Riprova più tardi.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esporta tutti i dati in un file CSV"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun dato da esportare.")
        return
    
    try:
        # Nome file CSV con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"noleggi_export_{timestamp}.csv"
        
        # Crea il CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Data', 'Cognome', 'Nome', 'Documento', 'Numero_Documento', 'Telefono', 'Associato',
                'Tipo_Noleggio', 'Dettagli', 'Numero', 'Tempo', 'Pagamento', 
                'Foto_Ricevuta', 'Timestamp'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for registro in bot_instance.noleggi:
                writer.writerow({
                    'Data': registro['data'],
                    'Cognome': registro.get('cognome', registro.get('nome', '')),  # Retrocompatibilità
                    'Nome': registro.get('nome', registro.get('cognome', '')),     # Retrocompatibilità
                    'Documento': registro['documento'],
                    'Numero_Documento': registro.get('numero_documento', ''),
                    'Telefono': registro['telefono'],
                    'Associato': registro['associato'],
                    'Tipo_Noleggio': registro['tipo_noleggio'],
                    'Dettagli': registro['dettagli'],
                    'Numero': registro['numero'],
                    'Tempo': registro['tempo'],
                    'Pagamento': registro['pagamento'],
                    'Foto_Ricevuta': registro['foto_ricevuta'] or 'Non presente',
                    'Timestamp': registro['timestamp']
                })
        
        # Invia il file
        with open(csv_filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=csv_filename,
                caption=f"📊 Export completato! {len(bot_instance.noleggi)} registrazioni esportate."
            )
        
        # Rimuove il file temporaneo
        os.remove(csv_filename)
        
    except Exception as e:
        logger.error(f"Errore export CSV: {e}")
        await update.message.reply_text("❌ Errore nella creazione del file CSV. Riprova più tardi.")

async def cerca_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cerca e mostra i dettagli di un cliente"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun dato presente.")
        return
    
    # Estrae il termine di ricerca dal comando
    query = " ".join(context.args).strip().lower()
    
    if not query:
        await update.message.reply_text(
            "🔍 **CERCA CLIENTE**\n\n"
            "Usa: `/cerca [termine]`\n\n"
            "**Puoi cercare per:**\n"
            "• Cognome: `/cerca Rossi`\n"
            "• Nome: `/cerca Mario`\n"
            "• Telefono: `/cerca 3331234567`\n"
            "• Numero documento: `/cerca AB123456`\n"
            "• Tipo noleggio: `/cerca SUP`, `/cerca KAYAK`\n"
            "• Numero specifico: `/cerca drybag 9`, `/cerca lettino A`\n\n"
            "💡 **Esempi avanzati:**\n"
            "• `/cerca sup yoga` - trova chi ha noleggiato SUP yoga\n"
            "• `/cerca phonebag 15` - trova chi ha il phonebag numero 15"
        )
        return
    
    # Cerca nelle registrazioni
    risultati = []
    for i, registro in enumerate(bot_instance.noleggi):
        # Ricerca base (cognome, nome, telefono, numero documento)
        trovato = (query in registro.get('cognome', '').lower() or 
                  query in registro.get('nome', '').lower() or 
                  query in registro['telefono'].lower() or
                  query in registro.get('numero_documento', '').lower())
        
        # Ricerca per tipo noleggio
        if not trovato:
            if query in registro['tipo_noleggio'].lower():
                trovato = True
        
        # Ricerca per dettagli (es: "yoga" per SUP yoga)
        if not trovato:
            if query in registro['dettagli'].lower():
                trovato = True
        
        # Ricerca per numero specifico
        if not trovato:
            query_parts = query.split()
            if len(query_parts) >= 2:
                tipo_cercato = query_parts[0]
                numero_cercato = query_parts[1]
                
                if (tipo_cercato in registro['tipo_noleggio'].lower() and 
                    numero_cercato == registro['numero'].lower()):
                    trovato = True
        
        # Ricerca semplice per numero
        if not trovato:
            if query == registro['numero'].lower():
                trovato = True
        
        if trovato:
            risultati.append((i, registro))
    
    if not risultati:
        await update.message.reply_text(f"❌ Nessun cliente trovato per: **{query}**")
        return
    
    if len(risultati) == 1:
        # Un solo risultato - mostra i dettagli completi
        _, registro = risultati[0]
        messaggio = f"""
🔍 **DETTAGLI CLIENTE TROVATO**

📅 **Data:** {registro['data']}
👤 **Nome:** {registro.get('cognome', '')} {registro.get('nome', '')}
📄 **Documento:** {registro['documento']} - {registro.get('numero_documento', 'N/A')}
📞 **Telefono:** {registro['telefono']}
🏅 **Associato:** {registro['associato']}

🏄‍♂️ **NOLEGGIO:**
• **Tipo:** {registro['tipo_noleggio']}
• **Dettagli:** {registro['dettagli']}
• **Numero:** {registro['numero']}
• **Tempo:** {registro['tempo']}

💳 **PAGAMENTO:**
• **Tipo:** {registro['pagamento']}
• **Ricevuta:** {'✅ Presente' if registro['foto_ricevuta'] else '❌ Non allegata'}

📝 **Registrato:** {registro['timestamp'][:19].replace('T', ' ')}
        """
        await update.message.reply_text(messaggio)
    
    else:
        # Più risultati - mostra lista
        messaggio = f"🔍 **TROVATI {len(risultati)} CLIENTI PER:** {query}\n\n"
        
        for i, (idx, registro) in enumerate(risultati[:10], 1):  # Mostra max 10
            data_noleggio = registro['data']
            tipo = registro['tipo_noleggio']
            tempo = registro['tempo']
            numero = registro['numero']
            
            messaggio += f"{i}. **{registro.get('cognome', '')} {registro.get('nome', '')}**\n"
            messaggio += f"   📅 {data_noleggio} | 🏄‍♂️ {tipo} {registro['dettagli']}\n"
            messaggio += f"   🔢 N. {numero} | ⏱️ {tempo} | 📞 {registro['telefono']}\n\n"
        
        if len(risultati) > 10:
            messaggio += f"... e altri {len(risultati) - 10} risultati\n\n"
        
        messaggio += "💡 **Suggerimento:** Affina la ricerca per vedere i dettagli completi"
        await update.message.reply_text(messaggio)

async def mostra_clienti(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra tutti i clienti registrati con contatore"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun cliente registrato.")
        return
    
    # Raggruppa per data per vedere i clienti giornalieri
    clienti_per_data = defaultdict(list)
    
    for registro in bot_instance.noleggi:
        clienti_per_data[registro['data']].append(registro)
    
    # Ordina le date
    date_ordinate = sorted(clienti_per_data.keys(), key=lambda x: tuple(map(int, x.split('/')[::-1])))
    
    messaggio = f"👥 **TUTTI I CLIENTI REGISTRATI**\n"
    messaggio += f"📊 **Totale:** {len(bot_instance.noleggi)} noleggi\n\n"
    
    for data in date_ordinate[-5:]:  # Mostra ultime 5 date
        registrazioni_giorno = clienti_per_data[data]
        messaggio += f"📅 **{data}** ({len(registrazioni_giorno)} noleggi)\n"
        
        for registro in registrazioni_giorno:
            nome_completo = f"{registro.get('cognome', '')} {registro.get('nome', '')}"
            tipo_breve = registro['tipo_noleggio']
            numero = registro['numero']
            tempo = registro['tempo']
            
            # Icone per i tipi
            icona = {"SUP": "🏄‍♂️", "KAYAK": "🚣‍♂️", "LETTINO": "🏖️", 
                    "PHONEBAG": "📱", "DRYBAG": "🎒"}.get(tipo_breve, "📦")
            
            messaggio += f"  • {nome_completo} - {icona}{tipo_breve}"
            if numero:
                messaggio += f" N.{numero}"
            messaggio += f" ({tempo})\n"
        
        messaggio += "\n"
    
    if len(date_ordinate) > 5:
        altre_date = len(date_ordinate) - 5
        messaggio += f"📋 ... e altri {altre_date} giorni di registrazioni\n\n"
    
    messaggio += "💡 Usa `/cerca [termine]` per trovare un cliente specifico"
    
    await update.message.reply_text(messaggio)

# Stati per la modifica
SELEZIONA_CLIENTE, SELEZIONA_CAMPO, NUOVO_VALORE = range(100, 103)

async def modifica_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Avvia la procedura di modifica di un cliente"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun cliente da modificare.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "✏️ **MODIFICA CLIENTE**\n\n"
        "Scrivi il nome, cognome o telefono del cliente da modificare:"
    )
    return SELEZIONA_CLIENTE

async def seleziona_cliente_modifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Seleziona il cliente da modificare"""
    query = update.message.text.strip().lower()
    
    # Cerca il cliente
    risultati = []
    for i, registro in enumerate(bot_instance.noleggi):
        if (query in registro.get('cognome', '').lower() or 
            query in registro.get('nome', '').lower() or 
            query in registro['telefono'].lower()):
            risultati.append((i, registro))
    
    if not risultati:
        await update.message.reply_text(f"❌ Nessun cliente trovato per: **{query}**\n\nRiprova con un altro termine:")
        return SELEZIONA_CLIENTE
    
    if len(risultati) == 1:
        # Un solo risultato - procedi alla selezione del campo
        context.user_data['cliente_modifica_idx'] = risultati[0][0]
        registro = risultati[0][1]
        
        # Mostra i campi modificabili
        keyboard = [
            ['Cognome', 'Nome', 'Telefono'],
            ['Documento', 'Numero Documento'],
            ['Tipo Noleggio', 'Tempo', 'Pagamento'],
            ['Annulla']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        messaggio = f"""
✏️ **CLIENTE SELEZIONATO:**
{registro.get('cognome', '')} {registro.get('nome', '')} - {registro['telefono']}
📅 {registro['data']} | 🏄‍♂️ {registro['tipo_noleggio']}

**Quale campo vuoi modificare?**
        """
        
        await update.message.reply_text(messaggio, reply_markup=reply_markup)
        return SELEZIONA_CAMPO
    
    else:
        # Più risultati - mostra lista numerata
        messaggio = f"🔍 **TROVATI {len(risultati)} CLIENTI:**\n\n"
        
        for i, (idx, registro) in enumerate(risultati[:5], 1):  # Max 5
            messaggio += f"{i}. {registro.get('cognome', '')} {registro.get('nome', '')}\n"
            messaggio += f"   📅 {registro['data']} | 📞 {registro['telefono']}\n\n"
        
        messaggio += "Scrivi il nome completo del cliente che vuoi modificare:"
        await update.message.reply_text(messaggio)
        return SELEZIONA_CLIENTE

async def seleziona_campo_modifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Seleziona il campo da modificare"""
    campo = update.message.text
    campi_validi = ['Cognome', 'Nome', 'Telefono', 'Documento', 'Numero Documento', 'Tipo Noleggio', 'Tempo', 'Pagamento']
    
    if campo == 'Annulla':
        await update.message.reply_text("❌ Modifica annullata.", reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END
    
    if campo not in campi_validi:
        keyboard = [
            ['Cognome', 'Nome', 'Telefono'],
            ['Documento', 'Numero Documento'],
            ['Tipo Noleggio', 'Tempo', 'Pagamento'],
            ['Annulla']
        ]
        await update.message.reply_text(
            "❌ Seleziona un campo valido:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELEZIONA_CAMPO
    
    context.user_data['campo_modifica'] = campo
    
    # Mostra valore attuale e chiedi nuovo valore
    idx = context.user_data['cliente_modifica_idx']
    registro = bot_instance.noleggi[idx]
    
    campo_map = {
        'Cognome': 'cognome',
        'Nome': 'nome', 
        'Telefono': 'telefono',
        'Documento': 'documento',
        'Numero Documento': 'numero_documento',
        'Tipo Noleggio': 'tipo_noleggio',
        'Tempo': 'tempo',
        'Pagamento': 'pagamento'
    }
    
    valore_attuale = registro.get(campo_map[campo], 'N/A')
    
    if campo == 'Documento':
        keyboard = [['C.I.', 'PAT'], ['PASS', 'ALTRO']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        messaggio = f"📄 **Valore attuale:** {valore_attuale}\n\nSeleziona il nuovo tipo di documento:"
    elif campo == 'Tipo Noleggio':
        keyboard = [['SUP', 'KAYAK', 'LETTINO'], ['PHONEBAG', 'DRYBAG']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        messaggio = f"🏄‍♂️ **Valore attuale:** {valore_attuale}\n\nSeleziona il nuovo tipo di noleggio:"
    elif campo == 'Pagamento':
        keyboard = [['CARD', 'BONIFICO']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        messaggio = f"💳 **Valore attuale:** {valore_attuale}\n\nSeleziona il nuovo tipo di pagamento:"
    else:
        reply_markup = ReplyKeyboardRemove()
        messaggio = f"✏️ **Valore attuale:** {valore_attuale}\n\nInserisci il nuovo valore:"
    
    await update.message.reply_text(messaggio, reply_markup=reply_markup)
    return NUOVO_VALORE

async def salva_modifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva la modifica effettuata"""
    nuovo_valore = update.message.text
    idx = context.user_data['cliente_modifica_idx']
    campo = context.user_data['campo_modifica']
    
    campo_map = {
        'Cognome': 'cognome',
        'Nome': 'nome', 
        'Telefono': 'telefono',
        'Documento': 'documento',
        'Numero Documento': 'numero_documento',
        'Tipo Noleggio': 'tipo_noleggio',
        'Tempo': 'tempo',
        'Pagamento': 'pagamento'
    }
    
    # Validazioni specifiche
    if campo == 'Documento' and nuovo_valore not in ['C.I.', 'PAT', 'PASS', 'ALTRO']:
        keyboard = [['C.I.', 'PAT'], ['PASS', 'ALTRO']]
        await update.message.reply_text(
            "❌ Seleziona un documento valido:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return NUOVO_VALORE
    
    if campo == 'Tipo Noleggio' and nuovo_valore not in ['SUP', 'KAYAK', 'LETTINO', 'PHONEBAG', 'DRYBAG']:
        keyboard = [['SUP', 'KAYAK', 'LETTINO'], ['PHONEBAG', 'DRYBAG']]
        await update.message.reply_text(
            "❌ Seleziona un tipo di noleggio valido:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return NUOVO_VALORE
    
    if campo == 'Pagamento' and nuovo_valore not in ['CARD', 'BONIFICO']:
        keyboard = [['CARD', 'BONIFICO']]
        await update.message.reply_text(
            "❌ Seleziona un tipo di pagamento valido:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return NUOVO_VALORE
    
    # Salva la modifica
    valore_precedente = bot_instance.noleggi[idx].get(campo_map[campo], 'N/A')
    
    # Assicura che il campo esista nel record (retrocompatibilità)
    if campo_map[campo] not in bot_instance.noleggi[idx]:
        bot_instance.noleggi[idx][campo_map[campo]] = ''
    
    bot_instance.noleggi[idx][campo_map[campo]] = nuovo_valore
    bot_instance.save_data()
    
    # Messaggio di conferma
    registro = bot_instance.noleggi[idx]
    messaggio = f"""
✅ **MODIFICA COMPLETATA!**

👤 **Cliente:** {registro.get('cognome', '')} {registro.get('nome', '')}
✏️ **Campo modificato:** {campo}
📝 **Da:** {valore_precedente}
📝 **A:** {nuovo_valore}

La modifica è stata salvata nel database.
    """
    
    await update.message.reply_text(messaggio, reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def vedi_ricevute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra le ricevute per cliente"""
    if not bot_instance.noleggi:
        await update.message.reply_text("📝 Nessun dato presente.")
        return
    
    # Raggruppa per cliente
    clienti_con_ricevute = {}
    clienti_senza_ricevute = {}
    
    for registro in bot_instance.noleggi:
        nome_completo = f"{registro.get('cognome', '')} {registro.get('nome', '')}"
        if registro['foto_ricevuta']:
            if nome_completo not in clienti_con_ricevute:
                clienti_con_ricevute[nome_completo] = []
            clienti_con_ricevute[nome_completo].append(registro)
        else:
            if nome_completo not in clienti_senza_ricevute:
                clienti_senza_ricevute[nome_completo] = []
            clienti_senza_ricevute[nome_completo].append(registro)
    
    messaggio = "📸 **STATO RICEVUTE CLIENTI**\n\n"
    
    if clienti_con_ricevute:
        messaggio += "✅ **CLIENTI CON RICEVUTE:**\n"
        for cliente, registrazioni in clienti_con_ricevute.items():
            messaggio += f"• {cliente} ({len(registrazioni)} noleggi)\n"
    
    if clienti_senza_ricevute:
        messaggio += "\n❌ **CLIENTI SENZA RICEVUTE:**\n"
        for cliente, registrazioni in clienti_senza_ricevute.items():
            messaggio += f"• {cliente} ({len(registrazioni)} noleggi)\n"
    
    await update.message.reply_text(messaggio)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancella la conversazione corrente"""
    await update.message.reply_text(
        "❌ Operazione annullata. Usa /start per iniziare una nuova registrazione.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la guida ai comandi"""
    help_text = """
🏄‍♂️ **BOT NOLEGGIO SUP - GUIDA COMANDI**

/start - Inizia una nuova registrazione noleggio
/cerca - Cerca cliente (nome/tipo noleggio/numero)
/mostra_clienti - Lista completa clienti con contatori
/modifica - Modifica dati di un cliente esistente
/export - Esporta tutti i dati in formato CSV
/vedi_ricevute - Visualizza stato ricevute per cliente
/help - Mostra questa guida
/cancel - Annulla l'operazione in corso

**Come funziona:**
1. Usa /start per registrare un noleggio
2. Segui la procedura guidata con i PULSANTI (non scrivere!)
3. Puoi allegare foto della ricevuta (opzionale)
4. Usa /cerca per trovare clienti specifici
5. Usa /mostra_clienti per vedere tutti i clienti
6. Usa /modifica per correggere errori
7. Usa /export per scaricare tutti i dati in CSV

**⚠️ IMPORTANTE: Usa sempre i PULSANTI, non scrivere le risposte!**

**Ricerca avanzata con /cerca:**
• Cognome/Nome: `/cerca Rossi`, `/cerca Mario`
• Telefono: `/cerca 3331234567`
• Numero documento: `/cerca AB123456`
• Tipo noleggio: `/cerca SUP`, `/cerca KAYAK`
• Numero specifico: `/cerca drybag 9`, `/cerca lettino A`
• Dettagli: `/cerca sup yoga`, `/cerca lettino pineta`

**Tipi di noleggio supportati:**
• SUP (con 10 varianti)
• KAYAK
• LETTINO (Pineta/Squero con numerazione A-Z per associati, 0-99 per non associati)
• PHONEBAG (numeri 0-99)
• DRYBAG (numeri 0-99)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **Autore:** Dino Bronzi
📅 **Creato:** 26 Luglio 2025
🔄 **Versione:** 1.9 - HOTFIX parametri run_polling
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    await update.message.reply_text(help_text)

def main():
    """Funzione principale per avviare il bot"""
    try:
        # Token del bot da variabile d'ambiente
        TOKEN = os.getenv('BOT_TOKEN')
        
        if not TOKEN:
            print("❌ ERRORE: Token non trovato!")
            print("🔧 Imposta la variabile d'ambiente BOT_TOKEN")
            return
        
        # Crea l'applicazione
        application = Application.builder().token(TOKEN).build()
        
        # Handler per la conversazione di registrazione
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
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
                FOTO_RICEVUTA: [
                    CallbackQueryHandler(handle_callback),
                    MessageHandler(filters.PHOTO, handle_photo)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        # Handler per la conversazione di modifica
        modifica_handler = ConversationHandler(
            entry_points=[CommandHandler("modifica", modifica_cliente)],
            states={
                SELEZIONA_CLIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleziona_cliente_modifica)],
                SELEZIONA_CAMPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleziona_campo_modifica)],
                NUOVO_VALORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, salva_modifica)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        # Aggiungi gli handler
        application.add_handler(conv_handler)
        application.add_handler(modifica_handler)
        application.add_handler(CommandHandler("nuovo", start))  # Cambiato per avviare registrazione
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cerca", cerca_cliente))
        application.add_handler(CommandHandler("mostra_clienti", mostra_clienti))
        application.add_handler(CommandHandler("export", export_csv))
        application.add_handler(CommandHandler("vedi_ricevute", vedi_ricevute))
        
        # IMPORTANTE: Aggiungi error handler
        application.add_error_handler(error_handler)
        
        # Avvia il bot con configurazioni corrette
        print("🏄‍♂️ Bot SUP Rental v.1.9 avviato!")
        print("📱 Usa /start per iniziare una registrazione")
        print("❌ Premi Ctrl+C per fermare il bot")
        
        # Configurazioni semplici e compatibili
        application.run_polling(
            drop_pending_updates=True,  # Ignora messaggi pendenti al riavvio
            allowed_updates=Update.ALL_TYPES  # Gestisce tutti i tipi di update
        )
        
    except Exception as e:
        logger.error(f"Errore critico nell'avvio del bot: {e}")
        print(f"❌ Errore nell'avvio del bot: {e}")
        print("🔧 Verifica il token e la connessione internet")

if __name__ == "__main__":
    main()
